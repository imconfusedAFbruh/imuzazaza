"""Training-only supervised wheel disagreement corrections; python skid_experiment.py."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from pipeline import ROOT, velocities, evaluate, digest, save_json
from learning import features, training_group, load_predictor
from alternatives import cached_trials


def balanced_weights(groups):
    counts = Counter(groups)
    return np.array([1 / counts[g] for g in groups])


def fit_ridge(x, y, w, strength):
    xx = np.c_[x, np.ones(len(x))]
    penalty = np.eye(xx.shape[1]) * w.sum() * strength
    penalty[-1, -1] = 0
    return np.linalg.solve(xx.T @ (xx * w[:, None]) + penalty,
                           xx.T @ (y * w[:, None]))


def skid_features(physical, wheel_yaw, tcn_motion, disagreement_scale):
    """Causal proxies, not measured slip labels; disagreement is not proof of slip."""
    disagreement = wheel_yaw - physical[:, 3]
    gate = np.abs(disagreement) / (np.abs(disagreement) + disagreement_scale)
    extra = np.column_stack([wheel_yaw, disagreement, gate, gate * physical[:, 2],
                             gate * physical[:, 3], gate * disagreement,
                             physical[:, 17] * physical[:, 2],
                             tcn_motion[:, 0] - physical[:, 2],
                             tcn_motion[:, 1] - physical[:, 3]])
    return np.column_stack([physical, extra])


def main():
    source = ROOT / 'outputs_amended_v2'
    out = ROOT / 'outputs_skid_v4'
    out.mkdir(exist_ok=True)
    if (out / 'selection.json').exists():
        raise RuntimeError('Already selected; preserve experiment and use a new directory')
    cfg = json.loads((source / 'run.json').read_text())['settings']
    cal = json.loads((source / 'calibration.json').read_text())
    parent = json.loads((source / 'final_test_lock.json').read_text())['freeze']
    if digest(ROOT / 'pipeline.py') != parent['code_sha256'] or digest(ROOT / 'learning.py') != parent['learning_code_sha256']:
        raise RuntimeError('Frozen parent source changed')
    for name, sha in parent['artifacts'].items():
        if digest(source / name) != sha:
            raise RuntimeError('Frozen parent artifact changed')
    torch.set_num_threads(2)
    train = cached_trials(source, 'train', cfg)
    validation = cached_trials(source, 'validation', cfg)
    assert {r['participant'] for r, _, _ in train}.isdisjoint({r['participant'] for r, _, _ in validation})
    tcn = load_predictor(source, 'tcn32')
    records = []
    for row, data, _ in train + validation:
        base = velocities(data, cal[row['setup']])
        p = features(data, base, cal)
        motion = tcn(data, base)
        records.append((row, data, base, p, motion))
    wheel_coefficients = {}
    for setup in sorted(cal):
        xs, ys, groups = [], [], []
        for row, data, _, p, _ in records:
            if row['partition'] != 'train' or row['setup'] != setup:
                continue
            mask = data['label_valid'] & data['imu_valid'] & np.isfinite(data['gt_yaw'])
            x = (p[:, 1] - p[:, 0])[mask][::10, None]
            xs.append(x); ys.append(data['gt_yaw'][mask][::10, None])
            groups.extend([training_group(row)] * len(x))
        if not xs:
            raise ValueError('No training setup')
        wheel_coefficients[setup] = fit_ridge(np.concatenate(xs), np.concatenate(ys), balanced_weights(groups), .0001)[:, 0]
    prepared = {}
    train_x, train_y, groups, disagreement = [], [], [], []
    for row, data, base, p, motion in records:
        coef = wheel_coefficients[row['setup']]
        wheel_yaw = (p[:, 1] - p[:, 0]) * coef[0] + coef[1]
        prepared[id(data)] = (p, motion, wheel_yaw)
        if row['partition'] == 'train':
            mask = data['label_valid'] & data['imu_valid']
            disagreement.extend(np.abs(wheel_yaw[mask][::10] - p[mask][::10, 3]))
    gate_scale = max(float(np.quantile(disagreement, .75)), .01)
    for row, data, base, p, motion in records:
        if row['partition'] != 'train':
            continue
        x = skid_features(p, prepared[id(data)][2], motion, gate_scale)
        y = np.c_[data['gt_v'], data['gt_yaw']] - motion
        mask = data['label_valid'] & data['imu_valid'] & np.isfinite(y).all(axis=1)
        train_x.append(x[mask][::10]); train_y.append(y[mask][::10])
        groups.extend([training_group(row)] * len(train_x[-1]))
    x, y, w = np.concatenate(train_x), np.concatenate(train_y), balanced_weights(groups)
    mean = np.average(x, axis=0, weights=w)
    std = np.maximum(np.sqrt(np.average((x - mean) ** 2, axis=0, weights=w)), .0001)
    cap = np.maximum(np.quantile(np.abs(y), .995, axis=0), .03)
    x = (x - mean) / std
    candidates = {}
    candidates['tcn32'] = evaluate(validation, cal, cfg, out, name='tcn32', predictor=lambda d,b: prepared[id(d)][1], export=False)
    for gain in (.1, .25, .5):
        def fusion(d, b, gain=gain):
            p, motion, wheel_yaw = prepared[id(d)]
            result = motion.copy()
            gate = 1 / (1 + (np.abs(wheel_yaw - p[:, 3]) / gate_scale) ** 2)
            result[:, 1] += gain * gate * (wheel_yaw - result[:, 1])
            return result
        name = f'wheel_fusion_{gain:g}'
        candidates[name] = evaluate(validation, cal, cfg, out, name=name, predictor=fusion, export=False)
        print(name, candidates[name]['equal_participant_mean_position_rmse_m'], flush=True)
    for strength in (.1, 1., 10.):
        beta = fit_ridge(x, y, w, strength)
        np.save(out / f'skid_ridge_{strength:g}.npy', beta)
        for gain in (.1, .25, .5):
            def correction(d, b, beta=beta, gain=gain):
                p, motion, wheel_yaw = prepared[id(d)]
                z = (skid_features(p, wheel_yaw, motion, gate_scale) - mean) / std
                return motion + gain * np.clip(np.c_[z, np.ones(len(z))] @ beta, -cap, cap)
            name = f'skid_ridge_{strength:g}_gain_{gain:g}'
            candidates[name] = evaluate(validation, cal, cfg, out, name=name, predictor=correction, export=False)
            print(name, candidates[name]['equal_participant_mean_position_rmse_m'], flush=True)
    eligible = {n:s for n,s in candidates.items() if s['trials'] == candidates['tcn32']['trials'] and not s['failed_reconstructions']}
    winner = min(eligible, key=lambda n: eligible[n]['equal_participant_mean_position_rmse_m'])
    save_json(out / 'calibration.json', dict(wheel_yaw={k:v.tolist() for k,v in wheel_coefficients.items()},
              gate_scale=gate_scale, mean=mean.tolist(), std=std.tolist(), cap=cap.tolist(), source='training only, participant/date group balanced'))
    hashes = {str(p.resolve()):digest(p) for p in [Path(__file__), ROOT/'pipeline.py', ROOT/'learning.py', ROOT/'alternatives.py',
              source/'final_test_lock.json', source/'inventory.json', source/'split.json', source/'calibration.json',
              source/'normalization.json', source/'tcn32.pt', source/'run.json', source/'geometry_policy.json', out/'calibration.json']}
    hashes.update({str(p.resolve()):digest(p) for p in out.glob('*.npy')})
    selection = dict(selected=winner, candidates=candidates, test_accessed=False, test_previously_inspected_in_parent=True,
                     criterion='equal-participant mean validation trial position RMSE', train_trials=len(train), validation_trials=len(validation),
                     source='frozen v2 inputs and estimator', artifacts=hashes)
    save_json(out/'selection.json', selection)
    lines = ['# Supervised wheel disagreement experiment', '',
             'Training only fits wheel yaw, group-balanced residual regression and scales. Validation selects the finite candidate grid. No test recording is opened.', '',
             'Wheel-center disagreement and acceleration are skid proxies, not ground-truth slip labels. This model cannot prove physical skidding or correct unobservable common-mode constant slip.', '',
             '| Candidate | Validation RMSE (m) |', '|---|---:|']
    lines += [f"| {n} | {s['equal_participant_mean_position_rmse_m']:.6f} |" for n,s in candidates.items()]
    lines += ['', f'Validation-selected: **{winner}**. All eligible candidates use the same {len(validation)} recordings and four participants.', '',
              'Do not retune using the previously inspected test. A new independent participant cohort is needed for a confirmatory accuracy claim.']
    (out/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('Selected', winner, flush=True)


if __name__ == '__main__':
    main()
