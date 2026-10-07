"""Train-only linear body-planar residual comparator; validation-only selection."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from scipy import signal

from pipeline import ROOT, runs, velocities, metrics, summarize, write_csv, save_json, digest
from learning import features, load_predictor, training_group


def verify_parent(frozen):
    freeze = json.loads((frozen / 'final_test_lock.json').read_text())['freeze']
    paths = {ROOT / 'pipeline.py': freeze['code_sha256'], ROOT / 'learning.py': freeze['learning_code_sha256']}
    for name, key in (('selection.json', 'selection_sha256'), ('split.json', 'split_sha256'),
                      ('inventory.json', 'inventory_sha256'), ('input_identity_audit.json', 'input_audit_sha256')):
        paths[frozen / name] = freeze[key]
    paths.update({frozen / n: h for n, h in freeze['artifacts'].items()})
    for path, expected in paths.items():
        assert digest(path) == expected, f'Frozen parent changed: {path}'
    return {str(path.relative_to(ROOT)): sha for path, sha in paths.items()}


def integrate_planar(t, motion, initial_xy, initial_heading, imu_valid):
    """Columns forward m/s, lateral m/s, yaw rad/s; stop at first IMU gap."""
    xy = np.full((len(t), 2), np.nan)
    heading = np.full(len(t), np.nan)
    xy[0], heading[0] = initial_xy, initial_heading
    for i in range(1, len(t)):
        if not imu_valid[i - 1:i + 1].all() or not np.isfinite(xy[i - 1]).all():
            break
        dt = t[i] - t[i - 1]
        forward, lateral, yaw = (motion[i - 1] + motion[i]) / 2
        heading[i] = heading[i - 1] + yaw * dt
        middle = (heading[i] + heading[i - 1]) / 2
        xy[i] = xy[i - 1] + dt * np.array([forward * np.cos(middle) - lateral * np.sin(middle),
                                         forward * np.sin(middle) + lateral * np.cos(middle)])
    return xy, heading


def lateral_labels(data, hz=100., cutoff=6.):
    """Optical body-lateral motion, not claimed to be physical tire slip."""
    side = np.full(len(data['t']), np.nan)
    mask = np.zeros(len(side), bool)
    sos = signal.butter(2, cutoff, fs=hz, output='sos')
    for a, b in runs(data['gt_valid']):
        if b - a < 40:
            continue
        xy = signal.sosfiltfilt(sos, data['gt_xy'][a:b], axis=0)
        heading = signal.sosfiltfilt(sos, np.unwrap(data['gt_heading'][a:b]))
        world = np.gradient(xy, data['t'][a:b], axis=0)
        side[a:b] = -world[:, 0] * np.sin(heading) + world[:, 1] * np.cos(heading)
        mask[a + 20:b - 20] = True
    return side, mask & data['label_valid'] & np.isfinite(side)


def planar_features(data, base, tcn, cal):
    c = cal[str(data['setup'])]
    center_acc = data['raw'][:, 12:15] / c['accel_counts_per_g'][2] - np.array(c['center_gravity_direction'])
    center_gyro = (data['raw'][:, 15:18] - np.array(c['gyro_bias_counts'][2])) * abs(c['terms'][2]['scale'])
    # Empirical isotropic scale; raw mounting axes are stable within acquisition setup.
    return np.c_[features(data, base, cal), center_acc, center_gyro, tcn].astype(np.float64)


def cached_rows(frozen, cfg, partition):
    assert partition in ('train', 'validation'), 'Test signals are forbidden in development'
    with (frozen / f'qc_{partition}.csv').open(newline='') as f:
        accepted = {r['id'] for r in csv.DictReader(f) if r['status'] == 'accepted'}
    with (frozen / 'inventory.csv').open(newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['partition'] == partition and r['id'] in accepted]
    fingerprint = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    originals = {r['id']: r for r in json.loads((frozen / 'input_identity_audit.json').read_text())['records']}
    for row in rows:
        path = frozen / 'cache' / (row['id'] + '.npz')
        meta = json.loads(path.with_suffix('.json').read_text())
        assert meta['signature']['settings_sha256'] == fingerprint, 'Stale cached settings'
        assert meta['signature']['preparation_version'] == 2
        for kind in ('imu', 'c3d'):
            assert digest(ROOT / row[kind]) == meta['signature'][kind + '_sha256'], f'Stale cached input: {row["id"]}'
            assert originals[row['id']][kind + '_sha256'] == meta['signature'][kind + '_sha256'], 'Input differs from parent freeze'
        assert originals[row['id']]['partition'] == partition
        with np.load(path) as z:
            data = {k: z[k] for k in z.files}
        yield row, data


def main():
    torch.set_num_threads(4)
    frozen, out = ROOT / 'outputs_amended_v2', ROOT / 'outputs_planar_v4'
    if (out / 'selection.json').exists():
        raise RuntimeError('Preserved selected output exists; use a fresh output directory for a new experiment')
    verify_parent(frozen)
    out.mkdir(exist_ok=True)
    cfg = json.loads((frozen / 'run.json').read_text())['settings']
    cal = json.loads((frozen / 'calibration.json').read_text())
    predict_tcn = load_predictor(frozen, 'tcn32')
    xs, ys, group_ids = [], [], []
    train_people = set()
    training_trials = 0
    for row, d in cached_rows(frozen, cfg, 'train'):
        base = velocities(d, cal[row['setup']])
        tcn = predict_tcn(d, base)
        side, valid = lateral_labels(d)
        target = np.c_[d['gt_v'] - tcn[:, 0], side, d['gt_yaw'] - tcn[:, 1]]
        valid &= np.isfinite(target).all(axis=1)
        x = planar_features(d, base, tcn, cal)
        xs.append(x[valid][::10])
        ys.append(target[valid][::10])
        group_ids.extend([training_group(row)] * len(xs[-1]))
        train_people.add(row['participant'])
        training_trials += 1
        if training_trials % 50 == 0:
            print(f'{training_trials} training trials', flush=True)
    x, y, groups = np.concatenate(xs), np.concatenate(ys), np.array(group_ids)
    unique, count = np.unique(groups, return_counts=True)
    sizes = dict(zip(unique, count))
    weight = np.array([1 / sizes[g] for g in groups])
    weight /= weight.sum()
    mean = np.sum(x * weight[:, None], axis=0)
    std = np.sqrt(np.sum((x - mean) ** 2 * weight[:, None], axis=0))
    std = np.maximum(std, 1e-5)
    design = np.c_[(x - mean) / std, np.ones(len(x))]
    covariance = design.T @ (design * weight[:, None])
    rhs = design.T @ (y * weight[:, None])
    cap = np.quantile(np.abs(y), .995, axis=0)
    fits = {}
    for alpha in (.001, .1, 10.):
        penalty = np.eye(design.shape[1]) * alpha
        penalty[-1, -1] = 0
        fits[alpha] = np.linalg.solve(covariance + penalty, rhs)
    validation = []
    for row, d in cached_rows(frozen, cfg, 'validation'):
        assert row['participant'] not in train_people
        base = velocities(d, cal[row['setup']])
        tcn = predict_tcn(d, base)
        f = planar_features(d, base, tcn, cal)
        validation.append((row, d, tcn, np.c_[(f - mean) / std, np.ones(len(f))]))
    assert len(validation) == 72
    results, candidates = [], []
    for mode in ('tcn_reference', 'lateral_only', 'all_three'):
        alphas = (0.,) if mode == 'tcn_reference' else tuple(fits)
        gains = (0.,) if mode == 'tcn_reference' else (.25, .5, 1.)
        for alpha in alphas:
            for gain in gains:
                records = []
                for row, d, tcn, design_val in validation:
                    motion = np.c_[tcn[:, 0], np.zeros(len(tcn)), tcn[:, 1]]
                    if mode != 'tcn_reference':
                        correction = gain * np.clip(design_val @ fits[alpha], -cap, cap)
                        if mode == 'lateral_only':
                            motion[:, 1] += correction[:, 1]
                        else:
                            motion += correction
                    xy, heading = integrate_planar(d['t'], motion, d['gt_xy'][0], d['gt_heading'][0], d['imu_valid'])
                    record = dict(id=row['id'], participant=row['participant'], condition=row['condition'],
                                  mode=mode, alpha=alpha, gain=gain, **metrics(d, xy, heading, cfg))
                    records.append(record)
                summary = summarize(records)[0]
                candidates.append(dict(mode=mode, alpha=alpha, gain=gain, **summary))
                results.extend(records)
                print(f"{mode} alpha={alpha} gain={gain}: {summary['equal_participant_mean_position_rmse_m']:.6f} m", flush=True)
    best = min(candidates, key=lambda c: c['equal_participant_mean_position_rmse_m'])
    np.savez(out / 'linear_artifacts.npz', mean=mean, std=std, cap=cap,
             **{f'weights_{alpha}': w for alpha, w in fits.items()})
    provenance = {n: digest(frozen / n) for n in ('run.json', 'calibration.json', 'tcn32.pt', 'normalization.json', 'inventory.csv', 'qc_train.csv', 'qc_validation.csv')}
    save_json(out / 'selection.json', dict(scope='validation-only; no test signals read', training_trials=training_trials,
              training_samples=len(x), training_groups=len(unique), best=best, candidates=candidates,
              input_sha256=provenance, source_sha256=digest(Path(__file__)),
              dependency_sha256={n: digest(ROOT / n) for n in ('pipeline.py', 'learning.py')},
              artifact_sha256=digest(out / 'linear_artifacts.npz'),
              feature_schema='20 physical + signed center accel3 + signed center gyro3 + frozen TCN motion2'))
    write_csv(out / 'validation_trials.csv', results)
    table = '\n'.join(f"| {c['mode']} | {c['alpha']} | {c['gain']} | {c['equal_participant_mean_position_rmse_m']:.6f} |" for c in candidates)
    (out / 'report.md').write_text(f'''# Explicit planar-motion comparator

Training-only linear residuals over frozen TCN32 output. State: forward velocity, lateral velocity, yaw rate. Initial MoCap position/heading only at inference. An IMU gap stops propagation. Ground-truth gaps are excluded when creating lateral targets; no gap interpolation. Signed center accelerometer and gyro channels retain lateral direction information missing from magnitude-only features. Unknown isotropic scaling and mounting/marker geometry remain assumptions; lateral labels are optical body-lateral motion, not established tire slip.

Training recordings: {training_trials}; subsampled valid training labels: {len(x)}; balanced training groups: {len(unique)}. Normalization, ridge weights, clipping caps fitted on training only. Earlier unmapped participants are grouped by acquisition date. Validation: 72 original accepted trials/four held-out participants, same official whole-trial metric as frozen TCN. Nine finite regularization/gain settings per candidate family, selected on validation. The reference TCN is included and can win. This reused validation is exploratory; no new blind accuracy claim is made.

| Model | Ridge penalty | Residual gain | Equal-participant position RMSE (m) |
|---|---:|---:|---:|
{table}

Best validation setting: **{best['mode']}**, alpha {best['alpha']}, gain {best['gain']}, RMSE **{best['equal_participant_mean_position_rmse_m']:.6f} m**. No final-test recordings or signals read. Frozen source/artifacts remain unchanged. The small linear comparator runs on CPU; GPU changes its speed, not the motion information available. A negative outcome does not invalidate the oracle representation finding; signed features and an affine mapping may not recover lateral velocity from these sensors.

`selection.json` records the complete finite comparison and input hashes. `linear_artifacts.npz` stores training-fitted parameters. `validation_trials.csv` contains all matched trial metrics.
''', encoding='utf-8')


if __name__ == '__main__':
    main()
