"""Compare a GRU and learned-uncertainty rate filter with frozen v2 TCN.

python alternatives.py train --epochs 12
python alternatives.py retrospective-test
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler

from pipeline import ROOT, digest, evaluate, save_json, velocities
from learning import features, training_group, Windows, load_predictor


class ResidualGRU(nn.Module):
    def __init__(self, width=32):
        super().__init__()
        self.gru = nn.GRU(20, width, batch_first=True)
        self.output = nn.Linear(width, 2)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, x):
        values, _ = self.gru(x.transpose(1, 2))
        return self.output(values).transpose(1, 2)


def cached_trials(source, partition, cfg):
    """Read accepted, fingerprinted prepared signals without changing the parent."""
    rows = json.loads((source / 'inventory.json').read_text())
    accepted = {r['id'] for r in csv.DictReader((source / f'qc_{partition}.csv').open())
                if r['status'] == 'accepted'}
    import hashlib
    fingerprint = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    trials = []
    for row in rows:
        if row['partition'] != partition or row['id'] not in accepted:
            continue
        path = source / 'cache' / (row['id'] + '.npz')
        meta = json.loads(path.with_suffix('.json').read_text())
        signature = dict(preparation_version=2, settings_sha256=fingerprint,
                         imu_sha256=digest(ROOT / row['imu']), c3d_sha256=digest(ROOT / row['c3d']))
        if meta['signature'] != signature:
            raise RuntimeError(f'Prepared input changed: {row["id"]}')
        with np.load(path) as z:
            data = {k: z[k] for k in z.files}
        trials.append((row, data, meta))
    if not trials:
        raise ValueError(f'No accepted {partition} recordings')
    return trials


def gru_predictor(out, calibration, norm, gain_override=None):
    state = torch.load(out / 'gru32.pt', map_location='cpu', weights_only=True)
    model = ResidualGRU().eval()
    model.load_state_dict(state['state'])
    mean, std, scale, cap = [np.array(norm[k], np.float32)
                            for k in ('mean', 'std', 'target_scale', 'residual_cap')]
    gain = state['gain'] if gain_override is None else gain_override
    def predict(data, base):
        x = (features(data, base, calibration) - mean) / std
        pieces = []
        # ponytail: bounded recurrent history; train longer windows before increasing it.
        with torch.no_grad():
            starts = list(range(0, len(x), 256))
            for offset in range(0, len(starts), 64):
                batch_starts = starts[offset:offset + 64]
                windows = []
                for start in batch_starts:
                    window = x[max(0, start - 256):start + 256]
                    windows.append(np.pad(window, ((0, 512 - len(window)), (0, 0))))
                result = model(torch.from_numpy(np.stack(windows).transpose(0, 2, 1).copy())).numpy()
                for i, start in enumerate(batch_starts):
                    left = min(start, 256); length = min(256, len(x) - start)
                    pieces.append(result[i, :, left:left + length].T)
        return base + gain * np.clip(np.concatenate(pieces) * scale, -cap, cap)
    return predict


def integrated_loss(pred, target, physical, mask, scale):
    loss = F.smooth_l1_loss(pred.transpose(1, 2)[mask], target.transpose(1, 2)[mask])
    valid = mask[:, 124:].all(dim=1)
    if valid.any():
        def pose(residual):
            motion = physical[valid, 2:4, 124:] + residual[valid, :, 124:] * scale
            angle = torch.cumsum(motion[:, 1] * .01, dim=1)
            delta = torch.stack([motion[:, 0] * torch.cos(angle), motion[:, 0] * torch.sin(angle)], dim=1) * .01
            return torch.cumsum(delta, dim=2), angle
        position, angle = pose(pred)
        reference_position, reference_angle = pose(target)
        duration = pred.shape[-1] * .01 - 1.24
        loss = loss + .2 * F.smooth_l1_loss(position / max(float(scale[0, 0, 0]) * duration, .05),
                    reference_position / max(float(scale[0, 0, 0]) * duration, .05))
        loss = loss + .1 * F.smooth_l1_loss(angle / max(float(scale[0, 1, 0]) * duration, .03),
                    reference_angle / max(float(scale[0, 1, 0]) * duration, .03))
    return loss


def fit_uncertainty(trials, predictor, calibration, norm):
    """Log squared error regression, group-balanced and fitted on training only."""
    xs, errors, groups, increments = [], [], [], []
    mean, std = np.array(norm['mean']), np.array(norm['std'])
    for row, data, _ in trials:
        base = velocities(data, calibration[row['setup']])
        motion = predictor(data, base)
        truth = np.c_[data['gt_v'], data['gt_yaw']]
        mask = data['label_valid'] & data['imu_valid'] & np.isfinite(truth).all(axis=1)
        x = (features(data, base, calibration) - mean) / std
        xs.append(x[mask][::10]); errors.append((motion[mask] - truth[mask])[::10] ** 2)
        groups.extend([training_group(row)] * len(xs[-1]))
        contiguous = mask[1:] & mask[:-1]
        increments.append(np.diff(truth, axis=0)[contiguous] ** 2)
    x, e = np.concatenate(xs), np.concatenate(errors)
    counts = Counter(groups); w = np.array([1 / counts[g] for g in groups])
    floor = np.maximum(np.average(e, axis=0, weights=w) * .05, [1e-5, 1e-6])
    xx = np.c_[x, np.ones(len(x))]
    penalty = np.eye(xx.shape[1]) * w.sum() * .1; penalty[-1, -1] = 0
    beta = np.linalg.solve(xx.T @ (xx * w[:, None]) + penalty,
                          xx.T @ (np.log(e + floor) * w[:, None]))
    fitted = np.exp(np.clip(xx @ beta, -20, 5))
    factor = np.average(e / fitted, axis=0, weights=w)
    q = np.maximum(np.median(np.concatenate(increments), axis=0), floor * .001)
    return dict(weights=beta.tolist(), factor=factor.tolist(), floor=floor.tolist(),
                ceiling=np.maximum(np.quantile(e, .995, axis=0), floor * 20).tolist(),
                process_variance=q.tolist(), source='accepted training labels only; in-sample uncertainty fit',
                limitation='diagonal rate random walk; no absolute pose update or independently observable bias state')


def rate_filter(motion, variance, process_variance):
    """Two diagonal random-walk Kalman states: forward speed and yaw rate."""
    if motion.shape != variance.shape or motion.ndim != 2 or motion.shape[1] != 2 or not len(motion):
        raise ValueError('Motion and variance must be N by 2')
    q = np.asarray(process_variance)
    if q.shape != (2,) or not np.isfinite(q).all() or not np.isfinite(motion).all() or not np.isfinite(variance).all() or (variance <= 0).any() or (q <= 0).any():
        raise ValueError('Filter inputs must be finite with positive variances')
    result = np.empty_like(motion); state = motion[0].copy(); covariance = variance[0].copy()
    result[0] = state
    for i in range(1, len(motion)):
        covariance += q
        gain = covariance / (covariance + variance[i])
        state += gain * (motion[i] - state)
        covariance *= 1 - gain
        result[i] = state
    return result


def filtered_predictor(predictor, uncertainty, calibration, norm, multiplier):
    mean, std = np.array(norm['mean']), np.array(norm['std'])
    def predict(data, base):
        motion = predictor(data, base)
        x = (features(data, base, calibration) - mean) / std
        variance = np.exp(np.clip(np.c_[x, np.ones(len(x))] @ np.array(uncertainty['weights']), -20, 5))
        variance *= uncertainty['factor']
        variance = np.clip(variance, uncertainty['floor'], uncertainty['ceiling'])
        return rate_filter(motion, variance, np.array(uncertainty['process_variance']) * multiplier)
    return predict


def artifact_hashes(source, out):
    files = [source / name for name in ('final_test_lock.json', 'split.json', 'calibration.json',
             'normalization.json', 'geometry_policy.json', 'run.json', 'inventory.json', 'tcn32.pt')]
    files += [Path(__file__), ROOT / 'pipeline.py', ROOT / 'learning.py', out / 'gru32.pt', out / 'uncertainty.json']
    return {str(p.resolve()): digest(p) for p in files}


def write_report(out, selection, test=None):
    lines = ['# GRU and learned-uncertainty comparison', '',
             'The same participants were inspected previously. These are retrospective experiments, not a new blind test.', '',
             'Calibration, features, normalization, preparation and inclusion rules are inherited from frozen v2. '
             'The GRU uses the same 12-epoch budget, training groups, residual gains and integrated-motion loss. '
             'The filter estimates speed/yaw rates with training-fitted diagonal uncertainty; it does not estimate absolute pose or a separately observable sensor bias.', '',
             '| Candidate | Validation position RMSE (m) |', '|---|---:|']
    for name, score in selection['candidates'].items():
        lines.append(f"| {name} | {score['equal_participant_mean_position_rmse_m']:.4f} |")
    lines += ['', f"Validation-selected estimator: **{selection['selected']}**.", '',
              'Uncertainty is fitted using in-sample training errors, so its calibration may be optimistic. '
              'Validation selects only the process-variance multiplier (0.25/1/4). No test trajectory tunes a parameter. '
              'The inherited unit, initial-pose, external-clock, marker geometry and coverage limitations still apply.']
    if test:
        lines += ['', '## Frozen retrospective test', '', '| Candidate | Position RMSE (m) | Trials | Participants |', '|---|---:|---:|---:|']
        for name, score in test.items():
            lines.append(f"| {name} | {score['equal_participant_mean_position_rmse_m']:.4f} | {score['trials']} | {score['participants']} |")
        lines += ['', 'All candidates use the same accepted recordings. Publish participant tables and exclusion counts with the averages.']
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('train', 'retrospective-test'))
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--source', type=Path, default=ROOT / 'outputs_amended_v2')
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs_alternatives_v3')
    args = parser.parse_args(); source, out = args.source.resolve(), args.out.resolve()
    if args.epochs < 1 or out == source:
        parser.error('Positive epochs and a separate output directory are required')
    out.mkdir(parents=True, exist_ok=True)
    lock = out / 'retrospective_test_lock.json'
    if args.command == 'train' and (lock.exists() or (out / 'selection.json').exists()):
        raise RuntimeError('This comparison is already selected/frozen; use a new directory')
    parent = json.loads((source / 'final_test_lock.json').read_text())['freeze']
    if digest(ROOT / 'pipeline.py') != parent['code_sha256'] or digest(ROOT / 'learning.py') != parent['learning_code_sha256']:
        raise RuntimeError('Frozen parent source changed')
    for name, sha in parent['artifacts'].items():
        if digest(source / name) != sha: raise RuntimeError('Frozen parent artifact changed')
    cfg = json.loads((source / 'run.json').read_text())['settings']
    calibration = json.loads((source / 'calibration.json').read_text())
    norm = json.loads((source / 'normalization.json').read_text())
    torch.set_num_threads(4); torch.manual_seed(42); np.random.seed(42)
    tcn = load_predictor(source, 'tcn32')
    if args.command == 'train':
        train, validation = cached_trials(source, 'train', cfg), cached_trials(source, 'validation', cfg)
        assert {r['participant'] for r, _, _ in train}.isdisjoint({r['participant'] for r, _, _ in validation})
        mean, std, scale = [np.array(norm[k], np.float32) for k in ('mean', 'std', 'target_scale')]
        sequences, groups = [], []
        for row, d, _ in train:
            base = velocities(d, calibration[row['setup']]); y = np.c_[d['gt_v'], d['gt_yaw']] - base
            mask = d['label_valid'] & np.isfinite(y).all(axis=1)
            sequences.append(((features(d, base, calibration) - mean) / std,
                              np.nan_to_num(y).astype(np.float32) / scale, mask, d['imu_valid']))
            groups.append(training_group(row))
        dataset = Windows(sequences, groups); counts = Counter(dataset.group_ids)
        sampler = WeightedRandomSampler([1 / counts[g] for g in dataset.group_ids], len(dataset),
                                        generator=torch.Generator().manual_seed(42))
        loader = DataLoader(dataset, batch_size=32, sampler=sampler)
        model = ResidualGRU(); optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
        mean_t, std_t = torch.tensor(mean)[None, :, None], torch.tensor(std)[None, :, None]
        scale_t = torch.tensor(scale)[None, :, None]
        candidates = {'baseline': evaluate(validation, calibration, cfg, out, export=False),
                      'tcn32': evaluate(validation, calibration, cfg, out, name='tcn32', predictor=tcn, export=False)}
        best, history, best_state = float('inf'), [], None
        for epoch in range(1, args.epochs + 1):
            model.train(); losses = []
            for x, y, mask in loader:
                optimizer.zero_grad(); pred = model(x)
                loss = integrated_loss(pred, y, x * std_t + mean_t, mask, scale_t)
                if not torch.isfinite(loss): raise ValueError('Non-finite GRU loss')
                loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
                losses.append(float(loss.detach()))
            torch.save(dict(state=model.state_dict(), gain=1.), out / 'gru32.pt')
            predictor = gru_predictor(out, calibration, norm, 1.)
            predicted = {id(d): predictor(d, velocities(d, calibration[r['setup']])) for r,d,_ in validation}
            scores = [(g, evaluate(validation, calibration, cfg, out, name='gru32', export=False,
                       predictor=lambda d,b,g=g: b + g * (predicted[id(d)] - b))) for g in (.25, .5, 1.)]
            gain, score = min(scores, key=lambda p:p[1]['equal_participant_mean_position_rmse_m'])
            value = score['equal_participant_mean_position_rmse_m']
            print(f'GRU epoch {epoch}/{args.epochs}: loss={np.mean(losses):.4f}, gain={gain}, validation RMSE={value:.4f} m', flush=True)
            history.append(dict(epoch=epoch, gain=gain, validation_rmse_m=value))
            if not score['failed_reconstructions'] and score['trials'] == candidates['baseline']['trials'] and value < best:
                best = value; best_state = dict(state={k:v.detach().clone() for k,v in model.state_dict().items()}, gain=gain)
        if best_state is None: raise RuntimeError('No eligible GRU checkpoint')
        torch.save(best_state, out / 'gru32.pt')
        gru = gru_predictor(out, calibration, norm)
        candidates['gru32'] = evaluate(validation, calibration, cfg, out, name='gru32', predictor=gru, export=False)
        uncertainties, multipliers = {}, {}
        for name, predictor in [('tcn32', tcn), ('gru32', gru)]:
            print(f'Fitting {name} uncertainty using training only', flush=True)
            uncertainty = fit_uncertainty(train, predictor, calibration, norm); uncertainties[name] = uncertainty
            scores = [(m, evaluate(validation, calibration, cfg, out, name=name+'_filter', export=False,
                      predictor=filtered_predictor(predictor, uncertainty, calibration, norm, m))) for m in (.25, 1., 4.)]
            multiplier, score = min(scores, key=lambda p:p[1]['equal_participant_mean_position_rmse_m'])
            multipliers[name] = multiplier; candidates[name+'_filter'] = score
            print(f'{name} filter: multiplier={multiplier}, validation RMSE={score["equal_participant_mean_position_rmse_m"]:.4f} m', flush=True)
        save_json(out / 'uncertainty.json', uncertainties)
        eligible = {n:s for n,s in candidates.items() if s['trials']==candidates['baseline']['trials'] and not s['failed_reconstructions']}
        winner = min(eligible, key=lambda n:eligible[n]['equal_participant_mean_position_rmse_m'])
        selection = dict(selected=winner, candidates=candidates, epochs=args.epochs, history=history,
                         multipliers=multipliers, training_windows=len(dataset),
                         criterion='equal-participant mean validation trajectory RMSE', test_previously_inspected=True,
                         artifacts=artifact_hashes(source, out))
        save_json(out / 'selection.json', selection); write_report(out, selection)
        print(f'Selected {winner} on validation only', flush=True)
    else:
        selection = json.loads((out / 'selection.json').read_text())
        if selection['artifacts'] != artifact_hashes(source, out): raise RuntimeError('Selected inputs changed')
        freeze = dict(selection_sha256=digest(out / 'selection.json'), artifacts=selection['artifacts'])
        if lock.exists() and json.loads(lock.read_text()) != freeze: raise RuntimeError('Frozen experiment changed')
        save_json(lock, freeze)
        trials = cached_trials(source, 'test', cfg)
        gru = gru_predictor(out, calibration, norm); uncertainties = json.loads((out / 'uncertainty.json').read_text())
        predictors = {'baseline':None, 'tcn32':tcn, 'gru32':gru}
        for name in ('tcn32', 'gru32'):
            predictors[name+'_filter'] = filtered_predictor(predictors[name], uncertainties[name], calibration, norm, selection['multipliers'][name])
        results = {}
        for name, predictor in predictors.items():
            results[name] = evaluate(trials, calibration, cfg, out, name=name, predictor=predictor,
                                     export=name==selection['selected'])
            print(name, json.dumps(results[name]), flush=True)
        save_json(out / 'retrospective_test_summary.json', results); write_report(out, selection, results)


if __name__ == '__main__':
    main()
