"""Validation-only, non-deployable oracle error-budget diagnosis; frozen inputs stay read-only."""
from pathlib import Path
import csv
import json
import hashlib

import numpy as np
import torch
from scipy import signal

from pipeline import ROOT, integrate, velocities, runs, read_markers, save_json, digest
from learning import load_predictor


def rmse(xy, truth, valid):
    good = valid & np.isfinite(xy).all(axis=1) & np.isfinite(truth).all(axis=1)
    return float(np.sqrt(np.mean(np.sum((xy[good] - truth[good]) ** 2, axis=1))))


def integrate_heading(t, forward, heading, xy0, lateral=None):
    lateral = np.zeros(len(t)) if lateral is None else lateral
    world = np.c_[forward * np.cos(heading) - lateral * np.sin(heading),
                  forward * np.sin(heading) + lateral * np.cos(heading)]
    increments = (world[1:] + world[:-1]) / 2 * np.diff(t)[:, None]
    return np.vstack([xy0, xy0 + np.cumsum(increments, axis=0)])


def group_average(rows, field):
    people = sorted({r['participant'] for r in rows})
    return float(np.mean([np.mean([r[field] for r in rows if r['participant'] == p]) for p in people]))


def check():
    t = np.arange(1001) / 100
    heading = np.ones(len(t)) * np.pi / 2
    xy = integrate_heading(t, np.ones(len(t)), heading, np.zeros(2), np.ones(len(t)) * .2)
    assert np.allclose(xy[-1], [-2, 10], atol=1e-10)
    # Perfect straight motion with 1 degree heading error drifts about 175 mm over 10 m.
    bad = integrate_heading(t, np.ones(len(t)), heading + np.deg2rad(1), np.zeros(2))
    good = integrate_heading(t, np.ones(len(t)), heading, np.zeros(2))
    assert np.isclose(np.linalg.norm(bad[-1] - good[-1]), 2 * 10 * np.sin(np.deg2rad(.5)))


def main():
    check()
    torch.set_num_threads(4)
    frozen = ROOT / 'outputs_amended_v2'
    out = ROOT / 'outputs_accuracy_audit'
    out.mkdir(exist_ok=True)
    calibration = json.loads((frozen / 'calibration.json').read_text())
    cfg = json.loads((frozen / 'run.json').read_text())['settings']
    predictor = load_predictor(frozen, 'tcn32')
    with (frozen / 'inventory.csv').open(newline='') as f:
        # Partition filter precedes any signal loading. No test cache/trajectory is read.
        rows = [r for r in csv.DictReader(f) if r['partition'] == 'validation']
    with (frozen / 'qc_validation.csv').open(newline='') as f:
        accepted = {r['id'] for r in csv.DictReader(f) if r['status'] == 'accepted'}
    rows = [r for r in rows if r['id'] in accepted]
    fingerprint = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    whole, spans, qc, marker_stats = [], [], [], []
    for row in rows:
        path = frozen / 'cache' / (row['id'] + '.npz')
        if not path.exists():
            continue
        with np.load(path) as z:
            d = {k: z[k] for k in z.files}
        meta = json.loads(path.with_suffix('.json').read_text())
        assert meta['signature']['settings_sha256'] == fingerprint, 'Stale cached settings'
        base = velocities(d, calibration[row['setup']])
        motion = predictor(d, base)
        xy, heading = integrate(d['t'], motion, d['gt_xy'][0], d['gt_heading'][0], d['imu_valid'])
        bxy, _ = integrate(d['t'], base, d['gt_xy'][0], d['gt_heading'][0], d['imu_valid'])
        rec = {k: row[k] for k in ('id', 'participant', 'condition', 'date')}
        rec.update(baseline_rmse_m=rmse(bxy, d['gt_xy'], d['gt_valid']),
                   tcn_rmse_m=rmse(xy, d['gt_xy'], d['gt_valid']))
        for angle in (-1., 1.):
            shifted, _ = integrate(d['t'], motion, d['gt_xy'][0], d['gt_heading'][0] + np.deg2rad(angle), d['imu_valid'])
            rec[f'initial_heading_{angle:+g}deg_rmse_m'] = rmse(shifted, d['gt_xy'], d['gt_valid'])
        whole.append(rec)
        qc.append(dict(id=row['id'], sync=meta['synchronization'], streams=meta['streams']))
        points, valid, hz = read_markers(ROOT / row['c3d'])
        midpoint = points[valid].mean(axis=1)
        marker_stats.append(dict(id=row['id'], coordinate_range_m=np.ptp(midpoint, axis=0).tolist(),
                                 separation_std_m=float(np.std(np.linalg.norm(points[valid, 0] - points[valid, 1], axis=1)))))
        good = (d['label_valid'] & d['gt_valid'] & d['imu_valid'] & np.isfinite(d['gt_v']) & np.isfinite(d['gt_yaw']))
        candidates = [(a, b) for a, b in runs(good) if b - a >= 300]
        if not candidates:
            continue
        a, b = max(candidates, key=lambda pair: pair[1] - pair[0])
        t, truth = d['t'][a:b], d['gt_xy'][a:b]
        gt_heading = np.unwrap(d['gt_heading'][a:b])
        v, yaw = d['gt_v'][a:b], d['gt_yaw'][a:b]
        pred = motion[a:b]
        iv = np.ones(len(t), bool)
        pred_xy, pred_heading = integrate(t, pred, truth[0], gt_heading[0], iv)
        speed_oracle, _ = integrate(t, np.c_[v, pred[:, 1]], truth[0], gt_heading[0], iv)
        rates_oracle, _ = integrate(t, np.c_[v, yaw], truth[0], gt_heading[0], iv)
        yaw_oracle, _ = integrate(t, np.c_[pred[:, 0], yaw], truth[0], gt_heading[0], iv)
        heading_oracle = integrate_heading(t, pred[:, 0], gt_heading, truth[0])
        nonholonomic_oracle = integrate_heading(t, v, gt_heading, truth[0])
        # Differentiate a local, uninterrupted reference span, preserving its boundary guard.
        smooth = signal.sosfiltfilt(signal.butter(2, cfg['derivative_hz'], fs=cfg['hz'], output='sos'), truth, axis=0)
        world_v = np.gradient(smooth, t, axis=0)
        lateral = -world_v[:, 0] * np.sin(gt_heading) + world_v[:, 1] * np.cos(gt_heading)
        forward = world_v[:, 0] * np.cos(gt_heading) + world_v[:, 1] * np.sin(gt_heading)
        moving = np.abs(forward) > .2
        side_angle = np.rad2deg(np.arctan2(lateral[moving], np.abs(forward[moving])))
        quiet = (np.abs(v) < .02) & (np.abs(yaw) < .02)
        quiet_pair = quiet[1:] & quiet[:-1]
        increments = np.rad2deg(np.diff(gt_heading))
        full_oracle = integrate_heading(t, forward, gt_heading, truth[0], lateral)
        # Diagnostic only: fit one constant marker/body-heading offset using this GT span.
        beta = .5 * np.arctan2(2 * np.sum(forward[moving] * lateral[moving]),
                               np.sum(forward[moving] ** 2 - lateral[moving] ** 2)) if moving.any() else 0.
        rotated_forward = forward * np.cos(beta) + lateral * np.sin(beta)
        constant_offset_oracle = integrate_heading(t, rotated_forward, gt_heading + beta, truth[0])
        edge = 20
        score = np.ones(len(t), bool)
        score[:edge] = score[-edge:] = False
        sr = {k: row[k] for k in ('id', 'participant', 'condition', 'date')}
        sr.update(duration_s=float(t[-1] - t[0]), full_trial_duration_s=float(d['t'][-1]),
                  reference_path_m=float(np.sum(np.linalg.norm(np.diff(truth, axis=0), axis=1))),
                  forward_speed_rmse_m_s=float(np.sqrt(np.mean((pred[:, 0] - v) ** 2))),
                  yaw_rate_rmse_deg_s=float(np.rad2deg(np.sqrt(np.mean((pred[:, 1] - yaw) ** 2)))),
                  lateral_speed_rms_m_s=float(np.sqrt(np.mean(lateral[score] ** 2))),
                  moving_lateral_heading_difference_rms_deg=float(np.sqrt(np.mean(side_angle ** 2))) if moving.any() else None,
                  quiet_heading_increment_rms_deg=float(np.sqrt(np.mean(increments[quiet_pair] ** 2))) if quiet_pair.sum() >= 100 else None,
                  quiet_heading_samples=int(quiet_pair.sum()),
                  fitted_constant_heading_offset_deg=float(np.rad2deg(beta)),
                  signed_lateral_speed_mean_m_s=float(np.mean(lateral[score])),
                  max_speed_m_s=float(np.quantile(np.linalg.norm(world_v[score], axis=1), .95)))
        cases = dict(tcn_local=pred_xy, gt_speed_predicted_yaw=speed_oracle,
                     predicted_speed_gt_yaw=yaw_oracle, gt_speed_gt_yaw=rates_oracle,
                     predicted_speed_gt_heading=heading_oracle,
                     gt_speed_gt_heading_no_lateral=nonholonomic_oracle,
                     gt_fitted_constant_heading_offset_no_lateral=constant_offset_oracle,
                     gt_2d_velocity_with_lateral=full_oracle)
        sr.update({name + '_rmse_m': rmse(value, truth, score) for name, value in cases.items()})
        spans.append(sr)
        if len(whole) % 12 == 0:
            print(f'{len(whole)} validation trials audited', flush=True)
    assert len(whole) == 72 and len({r['participant'] for r in whole}) == 4
    fields = [k for k in spans[0] if k.endswith('_rmse_m')]
    summary = dict(whole_trial={k: group_average(whole, k) for k in whole[0] if k.endswith('_rmse_m')},
                   continuous_span={k: group_average(spans, k) for k in fields},
                   trials=len(whole), span_trials=len(spans), participants=4,
                   median_span_duration_s=float(np.median([r['duration_s'] for r in spans])),
                   median_span_fraction=float(np.median([r['duration_s'] / r['full_trial_duration_s'] for r in spans])),
                   median_lateral_speed_rms_m_s=float(np.median([r['lateral_speed_rms_m_s'] for r in spans])),
                   median_lateral_diagnostic_floor_m=float(np.median([r['gt_speed_gt_heading_no_lateral_rmse_m'] for r in spans])),
                   median_optical_2d_integration_check_m=float(np.median([r['gt_2d_velocity_with_lateral_rmse_m'] for r in spans])),
                   median_clock_fit_residual_ms=float(np.median([s['clock_residual_ms'] for q in qc for s in q['streams']])),
                   median_peak_timing_residual_ms=float(1000 * np.median([q['sync']['peak_timing_median_abs_s'] for q in qc])),
                   median_speed_p95_m_s=float(np.median([r['max_speed_m_s'] for r in spans])))
    summary['median_moving_lateral_heading_difference_rms_deg'] = float(np.median([r['moving_lateral_heading_difference_rms_deg'] for r in spans if r['moving_lateral_heading_difference_rms_deg'] is not None]))
    quiet_values = [r['quiet_heading_increment_rms_deg'] for r in spans if r['quiet_heading_increment_rms_deg'] is not None]
    summary['trials_with_at_least_100_quiet_heading_pairs'] = len(quiet_values)
    summary['median_quiet_heading_increment_rms_deg'] = float(np.median(quiet_values)) if quiet_values else None
    conditions = {}
    for condition in sorted({r['condition'] for r in spans}):
        selected = [r for r in spans if r['condition'] == condition]
        conditions[condition] = dict(trials=len(selected), **{k: group_average(selected, k) for k in fields},
                                    lateral_speed_rms_m_s=group_average(selected, 'lateral_speed_rms_m_s'))
    inputs = {name: digest(frozen / name) for name in ('calibration.json', 'run.json', 'normalization.json', 'tcn32.pt', 'inventory.csv')}
    save_json(out / 'diagnostics.json', dict(protocol='Validation-only non-deployable oracle diagnosis; no test signal loading',
               input_sha256=inputs, summary=summary, by_condition=conditions, whole_trials=whole,
               continuous_spans=spans, timing_metadata=qc, marker_coordinate_checks=marker_stats))
    table = '\n'.join(f'| {k.removesuffix("_rmse_m")} | {v:.4f} |' for k, v in summary['continuous_span'].items())
    condition_table = '\n'.join(f"| {c} | {s['trials']} | {s['tcn_local_rmse_m']:.4f} | {s['gt_speed_gt_heading_no_lateral_rmse_m']:.4f} | {s['gt_2d_velocity_with_lateral_rmse_m']:.4f} | {s['lateral_speed_rms_m_s']:.4f} |" for c, s in conditions.items())
    report = f'''# Validation error-budget audit

Validation only: {len(whole)} accepted recordings, four held-out participants. Frozen source and outputs are read-only. Numeric checks pass. These are **non-deployable oracle diagnostics**, not competing model results or final-test tuning.

## Official whole-trial reproduction

Physics baseline: {summary['whole_trial']['baseline_rmse_m']:.6f} m. TCN32: {summary['whole_trial']['tcn_rmse_m']:.6f} m. Equal-participant mean trial RMSE.

## Matched continuous-span ablations

Use the longest uninterrupted derivative-valid span per recording, initial reference pose at span start, and no reference gap interpolation. {len(spans)} recordings; median span duration {summary['median_span_duration_s']:.1f} s, median duration fraction {summary['median_span_fraction']:.1%}. Each case scores the same span excluding 0.20 s at each boundary. **These local-span errors cannot be directly compared to full-trial published errors.** GT means continuous ground-truth information unavailable to the deployed estimator.

| Diagnostic | Equal-participant mean trial position RMSE (m) |
|---|---:|
{table}

GT speed with predicted yaw isolates accumulated heading error. Predicted speed with GT heading removes all accumulated yaw error. GT speed and GT heading still impose zero lateral speed. GT 2D velocity includes the measured lateral component and is a differentiation/integration sanity check, not an IMU predictor.

Median lateral-speed RMS: {summary['median_lateral_speed_rms_m_s']:.4f} m/s. Median no-lateral oracle RMSE: {summary['median_lateral_diagnostic_floor_m']:.4f} m; median full-2D integration sanity RMSE: {summary['median_optical_2d_integration_check_m']:.4f} m. Lateral components combine genuine slip, marker/heading misalignment, tilt/projection, optical noise, and derivative effects; they do not prove skidding alone.

| Condition | Trials | TCN local RMSE (m) | Perfect forward + heading, no lateral RMSE (m) | Full GT 2D integration check (m) | Lateral speed RMS (m/s) |
|---|---:|---:|---:|---:|---:|
{condition_table}

Median per-trial RMS angle between body-forward marker heading and path tangent while forward magnitude exceeds 0.2 m/s: {summary['median_moving_lateral_heading_difference_rms_deg']:.2f} degrees. Reverse travel is compared to the reverse body direction. There are {summary['trials_with_at_least_100_quiet_heading_pairs']} trials with at least one second of quiet derivative label pairs. Their median adjacent-frame marker-heading increment RMS is {summary['median_quiet_heading_increment_rms_deg']:.4f} degrees. This is a wobble diagnostic combining noise and genuine small movement; it is not a calibrated angular uncertainty, and adjacent increments can be correlated. The numerical full-GT integration check cannot establish MoCap absolute measurement accuracy.

## Millimeter error budget and timing

The synchronizer searches a 25 ms lag grid. Quantization alone allows up to 12.5 ms residual offset; at 1 m/s that is 12.5 mm of temporal positional disagreement. Hardware timing truth is unavailable. Median PC/device affine fit residual is {summary['median_clock_fit_residual_ms']:.2f} ms and median matched-peak timing residual {summary['median_peak_timing_residual_ms']:.2f} ms; these are diagnostics, not measured ground-truth synchronization error. Median within-trial 95th-percentile reference speed is {summary['median_speed_p95_m_s']:.2f} m/s.

For a 10 m straight path, 1 degree heading error gives 174.5 mm endpoint error; 1 mm would require about 0.0057 degrees if all other errors vanished. A constant 0.1% wheel-speed scale error gives 10 mm over 10 m. A 1 mm budget allows only 0.01% scale error over 10 m. These are illustrative exact geometry bounds, not promised attainable accuracy.

Whole-trial TCN RMSE with initial heading -1 degree: {summary['whole_trial']['initial_heading_-1deg_rmse_m']:.4f} m; +1 degree: {summary['whole_trial']['initial_heading_+1deg_rmse_m']:.4f} m. This sensitivity experiment does not fit initialization to GT.

## Structural limits and direction

1. The deployed state assumes forward speed plus planar yaw and zero lateral velocity. Train a body-forward/body-lateral/yaw or planar-displacement estimator if the oracle ablations show material lateral error. Validate unknown heading-marker offsets with acquisition records before attributing the entire component to slip.
2. Current features normalize accelerometer magnitudes by static gravity but do not recover attitude or world-frame horizontal acceleration. Center yaw chooses one gyro axis. Unknown mounting, slope tilt, gyro cross-axis terms, and changing bias remain physical errors that extra network capacity cannot guarantee removing.
3. Confirm that markers lie symmetrically on the hub axis and that C3D XY is horizontal. Two markers give lateral axis and projected yaw but cannot uniquely determine full 3D attitude. Coordinate ranges and rigidity are logged; they cannot establish the acquisition's ground-truth geometry.
4. Packet arrival times are fit against device clocks; this is not hardware MoCap synchronization. Refine offset continuously on train/validation and estimate clock drift from genuine shared events. Independent hardware triggers are preferable for a millimeter accuracy claim.
5. Keep participant-disjoint evaluation. The historical test is already inspected; neither this audit nor architecture experiments make it blind again. New acquisitions/participants are required for a fresh confirmatory test.

The CPU/GPU changes training speed, not observability. IMU-only absolute position has unobservable modes and integrating bias/slip produces drift. Millimeter full-recording accuracy across people is not supportable as a guaranteed target from the existing evidence. External absolute/relative position sensing or frequent known landmarks should be considered if millimeter accuracy is mandatory. Reinforcement learning is not a source of missing motion information; supervised lateral/slip residual learning has a direct training signal here and should precede an RL controller without an environment or defined control action.

The fitted constant heading-offset oracle is **another non-deployable GT diagnostic**: it projects the optical velocity onto one per-trial rotated body axis. The principal-axis angle minimizes squared lateral velocity on moving frames, not trajectory RMSE, so individual trajectory errors need not decrease. Its remaining error helps separate a constant marker/body heading offset from a changing lateral component. It cannot establish wheel skidding without mounting/marker geometry evidence. Camber, frame roll/pitch, and asymmetric marker offsets can change the relationship between the projected marker axis and true body heading. With only two hub-axis markers, full 3D attitude is not identifiable. The no-lateral result diagnoses a conflict between truthful body-forward/body-heading labels and a zero-lateral kinematic assumption. It is not a universal error lower bound: a predictor could deliberately bias heading toward the path tangent and trade heading/speed accuracy for position accuracy. It is also not a proven physical skid floor or a calibrated acquisition noise floor.

See diagnostics.json for per-condition ablations, all trial records, input hashes, and timing/coordinate metadata. No fitted oracle parameter is saved for inference.
'''
    (out / 'report.md').write_text(report, encoding='utf-8')
    print(json.dumps(summary, indent=2))


def geometry_followup():
    """Bounded train/validation geometry and static yaw-transfer diagnosis."""
    from planar_experiment import cached_rows, verify_parent
    from learning import training_group
    torch.set_num_threads(4)
    frozen, out = ROOT / 'outputs_amended_v2', ROOT / 'outputs_accuracy_audit'
    verify_parent(frozen)
    cfg = json.loads((frozen / 'run.json').read_text())['settings']
    cal = json.loads((frozen / 'calibration.json').read_text())
    audit = json.loads((out / 'diagnostics.json').read_text())
    span_records = {r['id']: r for r in audit['continuous_spans']}
    train = {}
    for row, d in cached_rows(frozen, cfg, 'train'):
        valid = d['label_valid'] & np.isfinite(d['gt_yaw'])
        x, y = d['raw'][valid][::10, 15:18], d['gt_yaw'][valid][::10]
        train.setdefault(row['setup'], []).append((x, y, training_group(row)))
    fits = {}
    for setup, samples in train.items():
        x = np.concatenate([r[0] for r in samples])
        y = np.concatenate([r[1] for r in samples])
        groups = np.concatenate([np.full(len(r[0]), r[2]) for r in samples])
        names, counts = np.unique(groups, return_counts=True)
        sizes = dict(zip(names, counts))
        w = np.array([1 / sizes[g] for g in groups]); w /= w.sum()
        mean = np.sum(x * w[:, None], axis=0)
        std = np.maximum(np.sqrt(np.sum((x - mean) ** 2 * w[:, None], axis=0)), 1.)
        design = np.c_[(x - mean) / std, np.ones(len(x))]
        penalty = np.eye(4) * 1e-5; penalty[-1, -1] = 0
        weights = np.linalg.solve(design.T @ (design * w[:, None]) + penalty, design.T @ (y * w))
        fits[setup] = dict(mean=mean, std=std, weights=weights, training_samples=len(y))
    records = []
    for row, d in cached_rows(frozen, cfg, 'validation'):
        sr = span_records[row['id']]
        points, valid, hz = read_markers(ROOT / row['c3d'])
        midpoint = points.mean(axis=1)
        axis = points[:, 0] - points[:, 1]
        axle_tilt = np.rad2deg(np.arcsin(np.clip(axis[:, 2] / np.maximum(np.linalg.norm(axis, axis=1), 1e-9), -1, 1)))
        base = velocities(d, cal[row['setup']])
        fit = fits[row['setup']]
        linear_yaw = np.c_[(d['raw'][:, 15:18] - fit['mean']) / fit['std'], np.ones(len(d['t']))] @ fit['weights']
        good = d['label_valid'] & d['gt_valid'] & d['imu_valid'] & np.isfinite(d['gt_v']) & np.isfinite(d['gt_yaw'])
        a, b = max([(a, b) for a, b in runs(good) if b - a >= 300], key=lambda pair: pair[1] - pair[0])
        score = np.ones(b - a, bool); score[:20] = score[-20:] = False
        oracle_xy, _ = integrate(d['t'][a:b], np.c_[d['gt_v'][a:b], linear_yaw[a:b]],
                                 d['gt_xy'][a], d['gt_heading'][a], np.ones(b - a, bool))
        base_error = base[a:b, 1] - d['gt_yaw'][a:b]
        linear_error = linear_yaw[a:b] - d['gt_yaw'][a:b]
        vertical_grades_deg = []
        for start, stop in runs(valid):
            if stop - start < 40:
                continue
            smooth = signal.sosfiltfilt(signal.butter(2, 6., fs=hz, output='sos'), midpoint[start:stop], axis=0)
            velocity = np.gradient(smooth, 1 / hz, axis=0)
            horizontal = np.linalg.norm(velocity[:, :2], axis=1)
            moving = horizontal > .2
            vertical_grades_deg.extend(np.rad2deg(np.arctan2(np.abs(velocity[moving, 2]), horizontal[moving])).tolist())
        record = {k: row[k] for k in ('id', 'participant', 'condition', 'date')}
        record.update(midpoint_z_range_m=float(np.ptp(midpoint[valid, 2])),
                      span_duration_s=sr['duration_s'], reference_path_m=sr['reference_path_m'],
                      midpoint_z_p95_p5_m=float(np.quantile(midpoint[valid, 2], .95) - np.quantile(midpoint[valid, 2], .05)),
                      axle_tilt_median_abs_deg=float(np.median(np.abs(axle_tilt[valid]))),
                      axle_tilt_p95_abs_deg=float(np.quantile(np.abs(axle_tilt[valid]), .95)),
                      axle_tilt_p95_p5_deg=float(np.quantile(axle_tilt[valid], .95) - np.quantile(axle_tilt[valid], .05)),
                      moving_path_grade_p95_abs_deg=float(np.quantile(vertical_grades_deg, .95)) if vertical_grades_deg else 0.,
                      baseline_yaw_rate_rmse_deg_s=float(np.rad2deg(np.sqrt(np.mean(base_error[score] ** 2)))),
                      baseline_yaw_bias_deg_s=float(np.rad2deg(np.mean(base_error[score]))),
                      baseline_speed_rmse_m_s=float(np.sqrt(np.mean((base[a:b, 0][score] - d['gt_v'][a:b][score]) ** 2))),
                      baseline_speed_bias_m_s=float(np.mean(base[a:b, 0][score] - d['gt_v'][a:b][score])),
                      linear_three_axis_yaw_rate_rmse_deg_s=float(np.rad2deg(np.sqrt(np.mean(linear_error[score] ** 2)))),
                      linear_three_axis_yaw_bias_deg_s=float(np.rad2deg(np.mean(linear_error[score]))),
                      gt_speed_linear_three_axis_yaw_rmse_m=rmse(oracle_xy, d['gt_xy'][a:b], score),
                      tcn_yaw_rate_rmse_deg_s=sr['yaw_rate_rmse_deg_s'],
                      tcn_speed_rmse_m_s=sr['forward_speed_rmse_m_s'],
                      tcn_local_rmse_m=sr['tcn_local_rmse_m'],
                      gt_speed_tcn_yaw_rmse_m=sr['gt_speed_predicted_yaw_rmse_m'],
                      tcn_speed_gt_yaw_rmse_m=sr['predicted_speed_gt_yaw_rmse_m'],
                      gt_speed_gt_heading_no_lateral_rmse_m=sr['gt_speed_gt_heading_no_lateral_rmse_m'])
        records.append(record)
    fields = [k for k in records[0] if k not in ('id', 'participant', 'condition', 'date')]
    conditions = {}
    for condition in sorted({r['condition'] for r in records}):
        selected = [r for r in records if r['condition'] == condition]
        conditions[condition] = dict(trials=len(selected), participants=len({r['participant'] for r in selected}),
                                    **{k: group_average(selected, k) for k in fields})
    save_json(out / 'geometry_yaw_followup.json', dict(scope='Training-fitted static yaw diagnostic; validation-only signal inspection',
                trials=records, conditions=conditions,
                fits={s: {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in f.items()} for s, f in fits.items()},
                note='Three-axis coefficients are training-only; GT speed trajectory is non-deployable oracle diagnosis. No parameter selected on validation.'))
    header = '\n## Elevation, axle tilt, and static yaw-transfer follow-up\n\nAll geometry columns summarize accepted validation recordings only. Condition labels are retained without inferred maneuver meanings. Mean trial statistics are averaged equally by participants represented in each condition. OS has only two participants/three recordings; condition effects are partly confounded with participant/setup and exclusion coverage. Axle elevation angle is derived from the optical left-right marker line, not full chair pitch/roll. Vertical movement assumes the configured C3D Z-up convention, which still requires acquisition confirmation.\n\n'
    table = '| Condition | Trials / people | Z range (m) | Axle tilt p95 (deg) | Path grade p95 (deg) | TCN speed RMSE (m/s) | TCN yaw RMSE (deg/s) | Baseline yaw RMSE (deg/s) | 3-axis yaw RMSE (deg/s) |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for c, r in conditions.items():
        table += f"| {c} | {r['trials']} / {r['participants']} | {r['midpoint_z_range_m']:.3f} | {r['axle_tilt_p95_abs_deg']:.2f} | {r['moving_path_grade_p95_abs_deg']:.2f} | {r['tcn_speed_rmse_m_s']:.3f} | {r['tcn_yaw_rate_rmse_deg_s']:.2f} | {r['baseline_yaw_rate_rmse_deg_s']:.2f} | {r['linear_three_axis_yaw_rate_rmse_deg_s']:.2f} |\n"
    table += '\n| Condition | Span duration (s) | Path length (m) | Baseline speed RMSE (m/s) | Baseline speed bias (m/s) | Baseline yaw bias (deg/s) |\n|---|---:|---:|---:|---:|---:|\n'
    for c, r in conditions.items():
        table += f"| {c} | {r['span_duration_s']:.2f} | {r['reference_path_m']:.2f} | {r['baseline_speed_rmse_m_s']:.3f} | {r['baseline_speed_bias_m_s']:+.3f} | {r['baseline_yaw_bias_deg_s']:+.3f} |\n"
    narrative = '\nThe three-axis comparator fits a single static affine mapping from center gyro gx/gy/gz to projected reference yaw rate per acquisition date, using participant-balanced training data only and a fixed numerical ridge of 1e-5. It checks whether adding fixed cross-axis coefficients resolves yaw transfer; it is not a gravity/attitude estimator. The associated GT-speed trajectory is a non-deployable yaw-isolation diagnosis. Per-trial bias, axle tilt variability, full oracle comparisons, and coefficients are in geometry_yaw_followup.json. No validation trajectory or geometry calibrates its coefficients.\n\nOS/PS do not have the largest observed elevation or axle tilt: ST has substantially greater Z motion and inferred path grade but lower position error. Thus these data do not establish tilt or gravity compensation as the dominant explanation for OS/PS. Both forward-speed and yaw transfer errors materially contribute to the difficult conditions; the three-axis static yaw mapping does not resolve them. Attitude/mounting calibration remains physically relevant, especially for changing orientation, but should be investigated alongside scale/bias stability, longer-duration drift, and reference/mounting correctness rather than promised as the main cure. This study does not infer full frame attitude from the two axle markers.\n\nReproduce the bounded follow-up with `python -c "from accuracy_audit import geometry_followup; geometry_followup()"`; it never loads test signals.\n'
    narrative += '\nOS/PS are not the longest recordings: their equal-participant mean spans are 14.55 s and 7.22 s, versus 47.52 s for 10x5. The largest errors therefore are not explained by duration alone. Mean speed biases and substantial rate RMSE indicate condition-dependent transfer errors, while cancellation can make small yaw mean bias coexist with large changing yaw error. Importantly, axle-marker tilt and hub elevation cannot rule out frame pitch about the rear axle: that rotation is unobservable from these two axle markers. The geometry check does not establish full-frame tilt as the cause, and also cannot exclude it.\n'
    report = (out / 'report.md').read_text(encoding='utf-8')
    marker = '\n## Elevation, axle tilt, and static yaw-transfer follow-up'
    report = report.split(marker)[0]
    (out / 'report.md').write_text(report + header + table + narrative, encoding='utf-8')
    print(json.dumps(conditions, indent=2))


if __name__ == '__main__':
    main()
