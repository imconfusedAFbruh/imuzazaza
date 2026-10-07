"""Training-only residual models, selected by held-out participant trajectory RMSE."""
from pathlib import Path
import json

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset, DataLoader

from pipeline import collect, velocities, evaluate, save_json, digest, selected_artifacts


def features(data, base):
    # At inference these features use only IMUs and the physics baseline.
    return np.c_[data['raw'], base].astype(np.float32)


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
    def __init__(self, sequences, length=384, stride=256, warmup=124):
        self.sequences = sequences
        self.length, self.warmup = length, warmup
        self.index = []
        for i, (x, y, mask, iv) in enumerate(sequences):
            for start in range(0, len(x) - length + 1, stride):
                if iv[start:start + length].all() and mask[start + warmup:start + length].mean() >= .7:
                    self.index.append((i, start))
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


def load_predictor(out, name):
    norm = json.loads((out / 'normalization.json').read_text())
    mean, std, scale, cap = [np.array(norm[k], np.float32) for k in ('mean', 'std', 'target_scale', 'residual_cap')]
    if name == 'ridge':
        weights = np.load(out / 'ridge.npy')
        def predict(data, base):
            x = (features(data, base) - mean) / std
            residual = np.c_[x, np.ones(len(x))] @ weights * scale
            return base + np.clip(residual, -cap, cap)
        return predict
    checkpoint = torch.load(out / (name + '.pt'), map_location='cpu', weights_only=True)
    model = ResidualTCN(checkpoint['width'])
    model.load_state_dict(checkpoint['state'])
    model.eval()
    def predict(data, base):
        x = (features(data, base) - mean) / std
        chunks = []
        # Exact 124-frame left context preserves causal output across inference chunks.
        with torch.no_grad():
            for start in range(0, len(x), 4096):
                left = max(0, start - 124)
                values = model(torch.from_numpy(x[left:start + 4096].T.copy())[None])[0].T.numpy()
                chunks.append(values[start - left:])
        residual = np.concatenate(chunks) * scale
        return base + np.clip(residual, -cap, cap)
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
    sequences = []
    sampled_x, sampled_y = [], []
    for row, d, _ in train:
        if row['setup'] not in calibration:
            continue
        base = velocities(d, calibration[row['setup']])
        x = features(d, base)
        y = np.c_[d['gt_v'], d['gt_yaw']] - base
        mask = d['label_valid'] & np.isfinite(y).all(axis=1)
        sampled_x.append(x[mask][::10])
        sampled_y.append(y[mask][::10])
        sequences.append((x, np.nan_to_num(y).astype(np.float32), mask, d['imu_valid']))
    del train
    sample_x, sample_y = np.concatenate(sampled_x), np.concatenate(sampled_y)
    mean = sample_x.mean(axis=0)
    std = np.maximum(sample_x.std(axis=0), 1e-4)
    scale = np.maximum(sample_y.std(axis=0), .01)
    cap = np.maximum(np.quantile(np.abs(sample_y), .995, axis=0), .03)
    save_json(out / 'normalization.json', dict(mean=mean.tolist(), std=std.tolist(), target_scale=scale.tolist(),
              residual_cap=cap.tolist(), source='accepted training labels only', target='speed/yaw residual'))
    sequences = [((x - mean) / std, y / scale, mask, iv) for x, y, mask, iv in sequences]
    baseline = evaluate(validation, calibration, cfg, out, name='baseline', export=False)
    if baseline['participants'] != 4:
        raise ValueError('Validation requires at least one accepted trial from each of the four reserved participants')
    candidates = {'baseline': baseline}
    # A regularized linear residual is the inexpensive comparator for the TCN.
    xx = np.c_[(sample_x - mean) / std, np.ones(len(sample_x))]
    yy = sample_y / scale
    penalty = np.eye(xx.shape[1]) * len(xx) * .01
    penalty[-1, -1] = 0
    weights = np.linalg.solve(xx.T @ xx + penalty, xx.T @ yy)
    np.save(out / 'ridge.npy', weights)
    candidates['ridge'] = evaluate(validation, calibration, cfg, out, name='ridge',
                                   predictor=load_predictor(out, 'ridge'), export=False)
    dataset = Windows(sequences)
    history = []
    for width in (16, 32):
        name = f'tcn{width}'
        torch.manual_seed(42)
        model = ResidualTCN(width)
        optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
        generator = torch.Generator().manual_seed(42)
        loader = DataLoader(dataset, batch_size=32, shuffle=True, generator=generator, num_workers=0)
        best_score = float('inf')
        for epoch in range(1, epochs + 1):
            model.train()
            losses = []
            for x, y, mask in loader:
                optimizer.zero_grad()
                pred = model(x)
                loss = F.smooth_l1_loss(pred.transpose(1, 2)[mask], y.transpose(1, 2)[mask])
                if not torch.isfinite(loss):
                    raise ValueError('Non-finite model loss')
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.)
                optimizer.step()
                losses.append(float(loss.detach()))
            torch.save(dict(width=width, state=model.state_dict()), out / (name + '_epoch.pt'))
            model.eval()
            score = evaluate(validation, calibration, cfg, out, name=name + '_epoch',
                             predictor=load_predictor(out, name + '_epoch'), export=False)
            current = score['equal_participant_mean_position_rmse_m']
            print(f'{name} epoch {epoch}/{epochs}: loss={np.mean(losses):.4f}, validation RMSE={current:.3f} m', flush=True)
            history.append(dict(candidate=name, epoch=epoch, loss=float(np.mean(losses)), validation_position_rmse_m=current))
            if score['trials'] == baseline['trials'] and not score['failed_reconstructions'] and current < best_score:
                best_score = current
                torch.save(dict(width=width, state=model.state_dict()), out / (name + '.pt'))
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
    selection['artifact_sha256'] = selected_artifacts(out, winner)
    save_json(out / 'selection.json', selection)
    if winner != 'baseline':
        evaluate(validation, calibration, cfg, out, name=winner, predictor=load_predictor(out, winner), export=True)
    print(f'Selected {winner} using validation only; final test remains unopened.', flush=True)
