"""Training-only residual models, selected by held-out participant trajectory RMSE."""
from pathlib import Path
import json
from collections import Counter

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from scipy import signal

from pipeline import collect, velocities, evaluate, save_json, digest, selected_artifacts


def features(data, base, calibration):
    """Twenty causal physical features; all scales/biases are training-fitted."""
    c = calibration[str(data['setup'])]
    raw, terms = data['raw'], c['terms']
    wheel = [raw[:, f['column']] * f['scale'] + f['intercept'] for f in terms[:2]]
    wheel_yaw = (wheel[1] - wheel[0]) / c['track_width_m']
    def derivative(x):
        # Recorded streams are resampled at 100 Hz; this is a trailing filter.
        return signal.lfilter(np.ones(5) / 5, [1], np.diff(x, prepend=x[0]) * 100)
    accel, offaxis, axial = [], [], []
    for i, f in enumerate(terms):
        a = raw[:, i * 6:i * 6 + 3] / c['accel_counts_per_g'][i]
        gyro = raw[:, i * 6 + 3:i * 6 + 6] - np.array(c['gyro_bias_counts'][i])
        axis = f['column'] % 6 - 3
        gyro[:, axis] = 0
        factor = abs(f['scale']) / c['wheel_radius_m'] if i < 2 else abs(f['scale'])
        accel.append(np.linalg.norm(a, axis=1) - 1)
        offaxis.append(np.linalg.norm(gyro, axis=1) * factor)
        axial.append(a[:, axis])
    a = raw[:, 12:15] / c['accel_counts_per_g'][2]
    gravity = np.array(c['center_gravity_direction'])
    parallel = a @ gravity
    horizontal = np.linalg.norm(a - parallel[:, None] * gravity, axis=1)
    return np.column_stack([wheel[0], wheel[1], base[:, 0], base[:, 1], wheel_yaw,
          wheel_yaw - base[:, 1], derivative(base[:, 0]), derivative(base[:, 1]),
          derivative(wheel[0]), derivative(wheel[1]), *accel, *offaxis,
          parallel - 1, horizontal, axial[0], axial[1]]).astype(np.float32)


def training_group(row):
    person = row['participant']
    return row['date'] + ':unmapped' if person == 'earlier-unmapped' else person


class CausalBlock(nn.Module):
    def __init__(self, width, dilation):
        super().__init__()
        self.padding = 4 * dilation
        self.conv = nn.Conv1d(width, width, 5, dilation=dilation)

    def forward(self, x):
        return x + F.silu(self.conv(F.pad(x, (self.padding, 0))))


class ResidualTCN(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.input = nn.Conv1d(20, width, 1)
        self.blocks = nn.Sequential(*(CausalBlock(width, d) for d in (1, 2, 4, 8, 16)))
        self.output = nn.Conv1d(width, 2, 1)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, x):
        return self.output(self.blocks(F.silu(self.input(x))))


class Windows(Dataset):
    def __init__(self, sequences, groups=None, length=512, stride=256, warmup=124):
        self.sequences = sequences
        self.length, self.warmup = length, warmup
        self.index = []
        self.group_ids = []
        for i, (x, y, mask, iv) in enumerate(sequences):
            for start in range(0, len(x) - length + 1, stride):
                if iv[start:start + length].all() and mask[start + warmup:start + length].mean() >= .7:
                    self.index.append((i, start))
                    self.group_ids.append(groups[i] if groups else str(i))
        if not self.index:
            raise ValueError('No valid causal training windows')

    def __len__(self):
        return len(self.index)

    def __getitem__(self, index):
        i, start = self.index[index]
        x, y, mask, _ = self.sequences[i]
        sl = slice(start, start + self.length)
        m = mask[sl].copy()
        m[:self.warmup] = False
        return torch.from_numpy(x[sl].T.copy()), torch.from_numpy(y[sl].T.copy()), torch.from_numpy(m.copy())


def load_predictor(out, name, gain_override=None):
    norm = json.loads((out / 'normalization.json').read_text())
    if norm.get('feature_schema') != 'physics_v2':
        raise ValueError('This code requires physics_v2 model artifacts; original models remain in the archived experiment')
    calibration = json.loads((out / 'calibration.json').read_text())
    mean, std, scale, cap = [np.array(norm[k], np.float32) for k in ('mean', 'std', 'target_scale', 'residual_cap')]
    if name == 'ridge':
        weights = np.load(out / 'ridge.npy')
        gain = norm.get('ridge_gain', 1.) if gain_override is None else gain_override
        def predict(data, base):
            x = (features(data, base, calibration) - mean) / std
            residual = np.c_[x, np.ones(len(x))] @ weights * scale
            return base + gain * np.clip(residual, -cap, cap)
        return predict
    checkpoint = torch.load(out / (name + '.pt'), map_location='cpu', weights_only=True)
    model = ResidualTCN(checkpoint['width'])
    model.load_state_dict(checkpoint['state'])
    model.eval()
    gain = checkpoint.get('gain', 1.) if gain_override is None else gain_override
    def predict(data, base):
        x = (features(data, base, calibration) - mean) / std
        chunks = []
        # Exact 124-frame left context preserves causal output across inference chunks.
        with torch.no_grad():
            for start in range(0, len(x), 4096):
                left = max(0, start - 124)
                values = model(torch.from_numpy(x[left:start + 4096].T.copy())[None])[0].T.numpy()
                chunks.append(values[start - left:])
        residual = np.concatenate(chunks) * scale
        return base + gain * np.clip(residual, -cap, cap)
    return predict


def train_and_select(rows, root, out, cfg, calibration, epochs):
    torch.manual_seed(42)
    np.random.seed(42)
    torch.set_num_threads(4)
    train = collect(rows, 'train', root, out, cfg)
    validation = collect(rows, 'validation', root, out, cfg)
    if not validation:
        raise ValueError('No accepted validation trials; model selection is impossible')
    train_ids = {r['participant'] for r, _, _ in train if r['date'] in ('2026-09-24', '2026-09-25')}
    val_ids = {r['participant'] for r, _, _ in validation}
    assert train_ids.isdisjoint(val_ids), 'Participant leakage'
    sequences, groups = [], []
    sampled_x, sampled_y, sample_groups = [], [], []
    for row, d, _ in train:
        if row['setup'] not in calibration:
            continue
        base = velocities(d, calibration[row['setup']])
        x = features(d, base, calibration)
        y = np.c_[d['gt_v'], d['gt_yaw']] - base
        mask = d['label_valid'] & np.isfinite(y).all(axis=1)
        sampled_x.append(x[mask][::10])
        sampled_y.append(y[mask][::10])
        sample_groups.extend([training_group(row)] * len(sampled_x[-1]))
        sequences.append((x, np.nan_to_num(y).astype(np.float32), mask, d['imu_valid']))
        groups.append(training_group(row))
    del train
    sample_x, sample_y = np.concatenate(sampled_x), np.concatenate(sampled_y)
    counts = Counter(sample_groups)
    sample_weights = np.array([1 / counts[g] for g in sample_groups])
    mean = np.average(sample_x, axis=0, weights=sample_weights).astype(np.float32)
    std = np.maximum(np.sqrt(np.average((sample_x - mean) ** 2, axis=0, weights=sample_weights)), 1e-4).astype(np.float32)
    target_mean = np.average(sample_y, axis=0, weights=sample_weights)
    scale = np.maximum(np.sqrt(np.average((sample_y - target_mean) ** 2, axis=0, weights=sample_weights)), .01).astype(np.float32)
    cap = np.maximum(np.quantile(np.abs(sample_y), .995, axis=0), .03)
    norm = dict(mean=mean.tolist(), std=std.tolist(), target_scale=scale.tolist(),
                residual_cap=cap.tolist(), source='group-balanced accepted training labels only',
                target='speed/yaw residual', feature_schema='physics_v2',
                grouping='participant when known; acquisition date group for older unidentified trials')
    save_json(out / 'normalization.json', norm)
    sequences = [((x - mean) / std, y / scale, mask, iv) for x, y, mask, iv in sequences]
    baseline = evaluate(validation, calibration, cfg, out, name='baseline', export=False)
    if baseline['participants'] != 4:
        raise ValueError('Validation requires at least one accepted trial from each of the four reserved participants')
    candidates = {'baseline': baseline}
    # A regularized linear residual is the inexpensive comparator for the TCN.
    xx = np.c_[(sample_x - mean) / std, np.ones(len(sample_x))]
    yy = sample_y / scale
    penalty = np.eye(xx.shape[1]) * sample_weights.sum() * .01
    penalty[-1, -1] = 0
    weights = np.linalg.solve(xx.T @ (xx * sample_weights[:, None]) + penalty,
                              xx.T @ (yy * sample_weights[:, None]))
    np.save(out / 'ridge.npy', weights)
    gains = (.25, .5, 1.)
    ridge_scores = [(gain, evaluate(validation, calibration, cfg, out, name='ridge',
                    predictor=load_predictor(out, 'ridge', gain), export=False)) for gain in gains]
    best_gain, _ = min(ridge_scores, key=lambda pair: pair[1]['equal_participant_mean_position_rmse_m'])
    norm['ridge_gain'] = best_gain
    save_json(out / 'normalization.json', norm)
    candidates['ridge'] = evaluate(validation, calibration, cfg, out, name='ridge', predictor=load_predictor(out, 'ridge'), export=False)
    dataset = Windows(sequences, groups)
    window_counts = Counter(dataset.group_ids)
    window_weights = [1 / window_counts[g] for g in dataset.group_ids]
    mean_tensor = torch.tensor(mean, dtype=torch.float32)[None, :, None]
    std_tensor = torch.tensor(std, dtype=torch.float32)[None, :, None]
    scale_tensor = torch.tensor(scale, dtype=torch.float32)[None, :, None]
    history = []
    for width in (16, 32):
        name = f'tcn{width}'
        torch.manual_seed(42)
        model = ResidualTCN(width)
        optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
        generator = torch.Generator().manual_seed(42)
        sampler = WeightedRandomSampler(window_weights, len(dataset), replacement=True, generator=generator)
        loader = DataLoader(dataset, batch_size=32, sampler=sampler, num_workers=0)
        best_score = float('inf')
        for epoch in range(1, epochs + 1):
            model.train()
            losses = []
            for x, y, mask in loader:
                optimizer.zero_grad()
                pred = model(x)
                loss = F.smooth_l1_loss(pred.transpose(1, 2)[mask], y.transpose(1, 2)[mask])
                # Short integrated-motion loss uses only complete training-label spans.
                tail = slice(dataset.warmup, None)
                complete = mask[:, tail].all(dim=1)
                if complete.any():
                    physical = x * std_tensor + mean_tensor
                    base_motion = physical[:, (2, 3), tail]
                    predicted = base_motion + pred[:, :, tail] * scale_tensor
                    target = base_motion + y[:, :, tail] * scale_tensor
                    def local_pose(motion):
                        angle = torch.cumsum(motion[:, 1] * .01, dim=1)
                        delta = torch.stack([motion[:, 0] * torch.cos(angle), motion[:, 0] * torch.sin(angle)], dim=1) * .01
                        return torch.cumsum(delta, dim=2), angle
                    position, angle = local_pose(predicted[complete])
                    reference_position, reference_angle = local_pose(target[complete])
                    duration = predicted.shape[-1] * .01
                    loss = loss + .2 * F.smooth_l1_loss(position / max(float(scale[0] * duration), .05),
                                   reference_position / max(float(scale[0] * duration), .05))
                    loss = loss + .1 * F.smooth_l1_loss(angle / max(float(scale[1] * duration), .03),
                                   reference_angle / max(float(scale[1] * duration), .03))
                if not torch.isfinite(loss):
                    raise ValueError('Non-finite model loss')
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.)
                optimizer.step()
                losses.append(float(loss.detach()))
            torch.save(dict(width=width, state=model.state_dict()), out / (name + '_epoch.pt'))
            model.eval()
            epoch_scores = [(gain, evaluate(validation, calibration, cfg, out, name=name + '_epoch',
                       predictor=load_predictor(out, name + '_epoch', gain), export=False)) for gain in gains]
            gain, score = min(epoch_scores, key=lambda pair: pair[1]['equal_participant_mean_position_rmse_m'])
            current = score['equal_participant_mean_position_rmse_m']
            print(f'{name} epoch {epoch}/{epochs}: loss={np.mean(losses):.4f}, gain={gain}, validation RMSE={current:.3f} m', flush=True)
            history.append(dict(candidate=name, epoch=epoch, loss=float(np.mean(losses)), gain=gain, validation_position_rmse_m=current))
            if score['trials'] == baseline['trials'] and not score['failed_reconstructions'] and current < best_score:
                best_score = current
                torch.save(dict(width=width, gain=gain, state=model.state_dict()), out / (name + '.pt'))
        if (out / (name + '.pt')).exists():
            candidates[name] = evaluate(validation, calibration, cfg, out, name=name,
                                        predictor=load_predictor(out, name), export=False)
    eligible = {name: score for name, score in candidates.items()
                if score['trials'] == baseline['trials'] and not score['failed_reconstructions']}
    winner = min(eligible, key=lambda name: eligible[name]['equal_participant_mean_position_rmse_m'])
    selection = dict(selected=winner, criterion='equal-participant mean trial position RMSE on validation only',
                     candidates=candidates, epochs=epochs, training_windows=len(dataset), history=history,
                     claim='best of these tested candidates; not a claim of globally optimal architecture',
                     final_test_opened=False, calibration_sha256=digest(out / 'calibration.json'),
                     normalization_sha256=digest(out / 'normalization.json'), code_sha256=digest(Path(__file__)))
    selection['protocol_version'] = 2
    selection['gain_candidates'] = list(gains)
    selection['loss'] = 'point residual plus integrated local position and heading on complete training spans'
    selection['artifact_sha256'] = selected_artifacts(out, winner)
    save_json(out / 'selection.json', selection)
    if winner != 'baseline':
        evaluate(validation, calibration, cfg, out, name=winner, predictor=load_predictor(out, winner), export=True)
    print(f'Selected {winner} using validation only; final test remains unopened.', flush=True)
