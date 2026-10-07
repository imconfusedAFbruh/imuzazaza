"""RoNIN-inspired offline ResNet comparator; training/validation only.

python ronin_experiment.py --epochs 12
Adapted architecture, features and wheelchair speed/yaw targets; not original RoNIN.
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler

from alternatives import cached_trials
from learning import features, training_group, Windows, load_predictor
from pipeline import ROOT, digest, evaluate, velocities, save_json


class Block(nn.Module):
    def __init__(self, incoming, width, stride=1):
        super().__init__()
        self.layers = nn.Sequential(nn.Conv1d(incoming, width, 3, stride, 1, bias=False),
            nn.BatchNorm1d(width), nn.ReLU(), nn.Conv1d(width, width, 3, padding=1, bias=False),
            nn.BatchNorm1d(width))
        self.skip = nn.Identity() if incoming == width and stride == 1 else nn.Conv1d(incoming, width, 1, stride)

    def forward(self, x):
        return F.relu(self.layers(x) + self.skip(x))


class OfflineResNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(nn.Conv1d(20, 32, 7, stride=2, padding=3), nn.ReLU(),
            Block(32, 32), Block(32, 32), Block(32, 64, 2), Block(64, 64),
            Block(64, 96, 2), Block(96, 96))
        self.output = nn.Conv1d(96, 2, 1)
        nn.init.zeros_(self.output.weight); nn.init.zeros_(self.output.bias)

    def forward(self, x):
        return F.interpolate(self.output(self.encoder(x)), size=x.shape[-1], mode='linear', align_corners=False)


def window_predictions(model, x, device, batch_size=64):
    """256-sample output cores with exactly 128 samples of left/right context.

    Offline: uses future IMU measurements, never future ground truth.
    Zero padding is in standardized feature space; includes recording boundaries.
    """
    if x.ndim != 2 or x.shape[1] != 20 or not len(x) or not np.isfinite(x).all():
        raise ValueError('Expected finite nonempty N by 20 feature matrix')
    padded = np.pad(x, ((128, 512), (0, 0)))
    starts = list(range(0, len(x), 256)); pieces = []
    with torch.no_grad():
        for offset in range(0, len(starts), batch_size):
            indices = starts[offset:offset + batch_size]
            batch = np.stack([padded[s:s + 512].T for s in indices])
            values = model(torch.from_numpy(batch).to(device)).cpu().numpy()
            for i, start in enumerate(indices):
                pieces.append(values[i, :, 128:128 + min(256, len(x) - start)].T)
    return np.concatenate(pieces)


def predictor(model, calibration, norm, device, gain):
    mean, std, scale, cap = [np.array(norm[k], np.float32) for k in ('mean', 'std', 'target_scale', 'residual_cap')]
    def predict(data, base):
        x = (features(data, base, calibration) - mean) / std
        return base + gain * np.clip(window_predictions(model, x, device) * scale, -cap, cap)
    return predict


def loss_for_core(pred, target, physical, mask, scale):
    pred, target, physical, mask = pred[:, :, 128:384], target[:, :, 128:384], physical[:, :, 128:384], mask[:, 128:384]
    if not mask.any(): raise ValueError('No valid output labels')
    loss = F.smooth_l1_loss(pred.transpose(1, 2)[mask], target.transpose(1, 2)[mask])
    valid = mask.all(dim=1)
    if valid.any():
        def pose(residual):
            motion = physical[valid, 2:4] + residual[valid] * scale
            angle = torch.cumsum(motion[:, 1] * .01, dim=1)
            delta = torch.stack([motion[:, 0] * torch.cos(angle), motion[:, 0] * torch.sin(angle)], dim=1) * .01
            return torch.cumsum(delta, dim=2), angle
        position, angle = pose(pred); truth_position, truth_angle = pose(target)
        loss = loss + .2 * F.smooth_l1_loss(position / max(float(scale[0, 0, 0]) * 2.56, .05), truth_position / max(float(scale[0, 0, 0]) * 2.56, .05))
        loss = loss + .1 * F.smooth_l1_loss(angle / max(float(scale[0, 1, 0]) * 2.56, .03), truth_angle / max(float(scale[0, 1, 0]) * 2.56, .03))
    return loss


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs_ronin_v4')
    args = parser.parse_args()
    if not 1 <= args.epochs <= 12: parser.error('Epoch budget must be 1 through 12')
    out = args.out.resolve(); source = ROOT / 'outputs_amended_v2'
    if out.exists(): raise RuntimeError('Use a fresh output directory; preserve selected experiments')
    if not torch.cuda.is_available(): raise RuntimeError('This experiment requires the enabled CUDA GPU')
    parent = json.loads((source / 'final_test_lock.json').read_text())['freeze']
    if digest(ROOT / 'pipeline.py') != parent['code_sha256'] or digest(ROOT / 'learning.py') != parent['learning_code_sha256']: raise RuntimeError('Frozen parent code changed')
    for name, sha in parent['artifacts'].items():
        if digest(source / name) != sha: raise RuntimeError('Frozen parent artifact changed')
    out.mkdir(); start_time = time.perf_counter()
    torch.manual_seed(42); np.random.seed(42); torch.set_num_threads(4)
    device = torch.device('cuda')
    cfg = json.loads((source / 'run.json').read_text())['settings']
    calibration = json.loads((source / 'calibration.json').read_text()); norm = json.loads((source / 'normalization.json').read_text())
    train, validation = cached_trials(source, 'train', cfg), cached_trials(source, 'validation', cfg)
    assert {r['participant'] for r, _, _ in train}.isdisjoint({r['participant'] for r, _, _ in validation})
    mean, std, scale = [np.array(norm[k], np.float32) for k in ('mean', 'std', 'target_scale')]
    sequences, groups = [], []
    for row, data, _ in train:
        base = velocities(data, calibration[row['setup']]); y = np.c_[data['gt_v'], data['gt_yaw']] - base
        mask = data['label_valid'] & np.isfinite(y).all(axis=1)
        sequences.append(((features(data, base, calibration) - mean) / std, np.nan_to_num(y).astype(np.float32) / scale, mask, data['imu_valid']))
        groups.append(training_group(row))
    dataset = Windows(sequences, groups, warmup=128); counts = Counter(dataset.group_ids)
    sampler = WeightedRandomSampler([1 / counts[g] for g in dataset.group_ids], len(dataset), generator=torch.Generator().manual_seed(42))
    loader = DataLoader(dataset, batch_size=64, sampler=sampler)
    model = OfflineResNet().to(device); optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
    mean_t, std_t, scale_t = [torch.tensor(a, device=device)[None, :, None] for a in (mean, std, scale)]
    candidates = {'baseline': evaluate(validation, calibration, cfg, out, export=False),
        'tcn32': evaluate(validation, calibration, cfg, out, name='tcn32', predictor=load_predictor(source, 'tcn32'), export=False)}
    best, best_state, history = float('inf'), None, []
    training_seconds, inference_seconds = 0., 0.
    for epoch in range(1, args.epochs + 1):
        model.train(); losses = []; epoch_start = time.perf_counter()
        for x, y, mask in loader:
            x, y, mask = x.to(device), y.to(device), mask.to(device)
            optimizer.zero_grad(); pred = model(x)
            loss = loss_for_core(pred, y, x * std_t + mean_t, mask, scale_t)
            if not torch.isfinite(loss): raise ValueError('Non-finite loss')
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step(); losses.append(float(loss.detach()))
        torch.cuda.synchronize(); training_seconds += time.perf_counter() - epoch_start
        inference_start = time.perf_counter()
        model.eval(); predict = predictor(model, calibration, norm, device, 1.)
        predictions = {id(data): predict(data, velocities(data, calibration[row['setup']])) for row, data, _ in validation}
        scores = [(gain, evaluate(validation, calibration, cfg, out, name='ronin_resnet', export=False,
            predictor=lambda d,b,g=gain: b + g * (predictions[id(d)] - b))) for gain in (.25, .5, 1.)]
        gain, score = min(scores, key=lambda p:p[1]['equal_participant_mean_position_rmse_m'])
        inference_seconds += time.perf_counter() - inference_start
        value = score['equal_participant_mean_position_rmse_m']
        history.append(dict(epoch=epoch, loss=float(np.mean(losses)), gain=gain, validation_rmse_m=value))
        print(f'ResNet epoch {epoch}/{args.epochs}: loss={np.mean(losses):.4f}, gain={gain}, validation RMSE={value:.4f} m', flush=True)
        if score['trials'] == candidates['baseline']['trials'] and not score['failed_reconstructions'] and value < best:
            best = value; best_state = dict(state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}, gain=gain, epoch=epoch)
    if best_state is None: raise RuntimeError('No eligible checkpoint')
    torch.save(best_state, out / 'ronin_resnet.pt'); model.load_state_dict(best_state['state']); model.eval()
    candidates['ronin_resnet'] = evaluate(validation, calibration, cfg, out, name='ronin_resnet', predictor=predictor(model, calibration, norm, device, best_state['gain']), export=False)
    files = [source / n for n in ('final_test_lock.json', 'split.json', 'calibration.json', 'normalization.json', 'geometry_policy.json', 'run.json', 'inventory.json', 'tcn32.pt')]
    files += [ROOT / n for n in ('pipeline.py', 'learning.py', 'alternatives.py', 'ronin_experiment.py', 'test_ronin_experiment.py')]
    files += [out / 'ronin_resnet.pt']
    selection = dict(selected=min(candidates, key=lambda n:candidates[n]['equal_participant_mean_position_rmse_m']), candidates=candidates,
        epochs=args.epochs, history=history, best_epoch=best_state['epoch'], gain=best_state['gain'], training_trials=len(train), training_windows=len(dataset),
        training_groups=dict(counts), runtime_seconds=time.perf_counter() - start_time, parameters=sum(p.numel() for p in model.parameters()),
        dependencies=dict(torch=torch.__version__, numpy=np.__version__, cuda=torch.version.cuda, gpu=torch.cuda.get_device_name()),
        training_seconds=training_seconds, validation_inference_and_metrics_seconds=inference_seconds,
        peak_allocated_vram_bytes=torch.cuda.max_memory_allocated(),
        semantics='Offline 512-frame windows, central 256-frame outputs, 128-frame future IMU context; no future reference input',
        adaptation='RoNIN-inspired small dense ResNet; 20 physics features and speed/yaw residual targets; not a faithful original RoNIN reproduction',
        test_evaluated=False, test_previously_inspected=True, artifacts={str(p.resolve()):digest(p) for p in files})
    save_json(out / 'selection.json', selection)
    lines = ['# RoNIN-inspired ResNet validation experiment', '', selection['adaptation'], '', selection['semantics'], '',
        'Calibration, normalization, grouping and input QC are inherited unchanged from frozen v2. Training uses group-balanced sampling; 12 epochs maximum; checkpoint and residual gain (0.25/0.5/1) selected by validation only. No test recordings were opened by this experiment.', '',
        '| Candidate | Validation position RMSE (m) | Trials | Participants |', '|---|---:|---:|---:|']
    for name, score in candidates.items(): lines.append(f"| {name} | {score['equal_participant_mean_position_rmse_m']:.6f} | {score['trials']} | {score['participants']} |")
    lines += ['', f"Selected: **{selection['selected']}**; ResNet checkpoint epoch {best_state['epoch']}, gain {best_state['gain']}; runtime {selection['runtime_seconds']:.1f} seconds.", '',
        'Existing test participants have been inspected in previous experiments. Any later evaluation on them is retrospective. Offline future IMU context differs from the causal TCN and must be disclosed. Symmetric window padding and temporal interpolation are deliberately simple; this experiment does not estimate lateral skid velocity or absolute pose corrections.', '',
        '[RoNIN paper](https://arxiv.org/abs/1905.12853) and [authors’ ResNet implementation](https://github.com/Sachini/ronin/blob/master/source/model_resnet1d.py).']
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(selection['candidates']), flush=True)


if __name__ == '__main__': main()
