"""Bounded empirical yaw-bias state comparator; no unverified full INS claim.

Choose a finite state/fusion grid on training-participant inner holdout, refit
empirical calibration on all observed training, then evaluate validation once.
Run: python physics_state_experiment.py
"""
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from pipeline import ROOT, digest, save_json, write_csv, metrics, summarize
from learning import training_group, load_predictor
from observed_training_experiment import observed_rows
from observed_reference_experiment import load_planar
from observed_ridge_experiment import imu_features
from planar_experiment import integrate_planar

WHEEL = np.array([3, 4, 5, 9, 10, 11])
BODY = np.array([15, 16, 17])
INNER = {'No.1', 'No.3', 'No.13', 'No.15'}
GRID = [(0., 0.)] + [(tau, blend) for tau in (.5, 2., 8.) for blend in (0., .25, .75)]


def fit(trials):
    """Every fitted conversion, threshold and cap uses these training rows only."""
    models = {}
    for setup in sorted({r['setup'] for r, d in trials}):
        xs, ys, gs, quiet_raw = [], [], [], []
        for row, data in trials:
            if row['setup'] != setup:
                continue
            valid = data['label_valid'] & data['imu_valid']
            ids = np.flatnonzero(valid)[::10]
            raw = data['raw'][ids]
            xs.append(raw)
            ys.append(np.c_[data['gt_v'][ids], data['gt_yaw'][ids]])
            gs.extend([training_group(row)] * len(ids))
            quiet = valid & (np.abs(data['gt_v']) < .02) & (np.abs(data['gt_yaw']) < .02)
            quiet_raw.append(data['raw'][quiet][::10])
        x, y = np.concatenate(xs), np.concatenate(ys)
        counts = Counter(gs)
        wt = np.array([1 / counts[g] for g in gs]); wt /= wt.sum()
        mu = np.average(x, axis=0, weights=wt)
        std = np.maximum(np.sqrt(np.average((x-mu)**2, axis=0, weights=wt)), 1.)
        fits = {}
        for name, cols, target in [('speed', WHEEL, 0), ('wheel_yaw', WHEEL, 1), ('body_yaw', BODY, 1)]:
            design = np.c_[(x[:, cols]-mu[cols])/std[cols], np.ones(len(x))]
            reg = np.eye(design.shape[1])*.001; reg[-1, -1] = 0.
            fits[name] = np.linalg.solve(design.T@(design*wt[:, None])+reg,
                                        design.T@(y[:, target]*wt))
        resting = np.concatenate(quiet_raw)
        if len(resting) < 20:
            raise RuntimeError(f'No observed training stationary support: {setup}')
        gyro_norm = np.c_[np.linalg.norm(resting[:, 3:6], axis=1),
                          np.linalg.norm(resting[:, 9:12], axis=1),
                          np.linalg.norm(resting[:, 15:18], axis=1)]
        gyro_gate = np.maximum(np.quantile(gyro_norm, .99, axis=0)*1.25, 1.)
        accel_rest = float(np.median(np.linalg.norm(resting[:, 12:15], axis=1)))
        ryaw = np.c_[(resting[:, BODY]-mu[BODY])/std[BODY], np.ones(len(resting))]@fits['body_yaw']
        disagreement = ((np.c_[(x[:, WHEEL]-mu[WHEEL])/std[WHEEL], np.ones(len(x))]@fits['wheel_yaw'])
                        -(np.c_[(x[:, BODY]-mu[BODY])/std[BODY], np.ones(len(x))]@fits['body_yaw']))
        models[setup] = dict(mean=mu.tolist(), std=std.tolist(),
            coefficients={k: v.tolist() for k, v in fits.items()},
            gyro_gate=gyro_gate.tolist(), accel_rest=accel_rest,
            bias_cap=float(min(.05, max(.003, np.quantile(np.abs(ryaw), .995)))),
            disagreement_scale=float(max(.02, np.quantile(np.abs(disagreement), .75))),
            training_groups=dict(counts), stationary_training_samples=len(resting))
    return models


def predict(imu, model, tau, blend):
    """Only raw IMU, time and IMU validity enter this causal comparator."""
    raw, t, valid = imu['raw'], imu['t'], imu['imu_valid']
    mu, std = np.array(model['mean']), np.array(model['std'])
    coef = model['coefficients']
    wheel = np.c_[(raw[:, WHEEL]-mu[WHEEL])/std[WHEEL], np.ones(len(raw))]
    body = np.c_[(raw[:, BODY]-mu[BODY])/std[BODY], np.ones(len(raw))]
    speed = wheel@np.array(coef['speed'])
    wheel_yaw = wheel@np.array(coef['wheel_yaw'])
    body_yaw = body@np.array(coef['body_yaw'])
    gyro_norm = np.c_[np.linalg.norm(raw[:, 3:6], axis=1), np.linalg.norm(raw[:, 9:12], axis=1),
                      np.linalg.norm(raw[:, 15:18], axis=1)]
    norm = np.linalg.norm(raw[:, 12:15], axis=1)
    candidate = ((gyro_norm < np.array(model['gyro_gate'])).all(axis=1)
                 & (np.abs(norm/model['accel_rest']-1) < .10) & valid)
    motion = np.zeros((len(raw), 3)); bias_history = np.zeros(len(raw)); quiet = np.zeros(len(raw), bool)
    bias, duration = 0., 0.
    for i in range(len(raw)):
        dt = max(0., min(.1, float(t[i]-t[i-1]))) if i else 0.
        duration = duration+dt if candidate[i] and (i == 0 or valid[i-1]) else 0.
        quiet[i] = duration >= .5
        if tau and quiet[i]:
            observation = float(np.clip(body_yaw[i], -model['bias_cap'], model['bias_cap']))
            bias += (1-np.exp(-dt/tau))*(observation-bias)
        adjusted = body_yaw[i]-bias
        # Disagreement reduces trust in wheel-derived yaw; it is not a slip label.
        weight = blend/(1+((wheel_yaw[i]-adjusted)/model['disagreement_scale'])**2)
        yaw = adjusted+weight*(wheel_yaw[i]-adjusted)
        motion[i] = (speed[i], 0., yaw)
        if tau and quiet[i]:
            motion[i] = 0.
        bias_history[i] = bias
    return motion, bias_history, quiet


def evaluate(trials, models, cfg, tau, blend):
    records = []
    for row, data in trials:
        imu = {k: data[k] for k in ('raw', 't', 'imu_valid')}
        motion, bias, quiet = predict(imu, models[row['setup']], tau, blend)
        xy, heading = integrate_planar(data['t'], motion, data['gt_xy'][0], data['gt_heading'][0], data['imu_valid'])
        records.append(dict(id=row['id'], participant=row['participant'], condition=row['condition'],
            stationary_detected_s=float(quiet.sum()/cfg['hz']), final_yaw_bias_rad_s=float(bias[-1]),
            **metrics(data, xy, heading, cfg)))
    summary, people, conditions = summarize(records)
    return summary, records, people, conditions


def main():
    started = time.perf_counter(); torch.set_num_threads(4)
    source = ROOT/'outputs_observed_reference_v7'; out = ROOT/'outputs_physics_state_v9'
    if out.exists():
        raise RuntimeError('Preserve existing experiment')
    manifest = json.loads((source/'artifact_manifest.json').read_text())
    run = json.loads((source/'run.json').read_text()); cfg = run['settings']
    for name, sha in manifest['sha256'].items():
        if digest(source/name) != sha: raise RuntimeError(f'Observed dependency changed: {name}')
    ridge_path = ROOT/'outputs_observed_ridge_v8'; ridge_selection = json.loads((ridge_path/'selection.json').read_text())
    for name, sha in ridge_selection['provenance'].items():
        if digest(ROOT/name) != sha: raise RuntimeError(f'Ridge dependency changed: {name}')
    rmanifest = json.loads((ridge_path/'artifact_manifest.json').read_text())
    for name, sha in rmanifest['sha256'].items():
        if digest(ridge_path/name) != sha: raise RuntimeError(f'Ridge artifact changed: {name}')
    train = [(row, data) for row, data, _ in observed_rows(source, cfg, 'train', manifest)]
    if len(train) != 473: raise RuntimeError('Training coverage changed')
    inner_fit = [(r,d) for r,d in train if r['participant'] not in INNER]
    inner_score = [(r,d) for r,d in train if r['participant'] in INNER]
    if set(r['participant'] for r,d in inner_score) != INNER: raise RuntimeError('Missing inner participant')
    fit_people = {r['participant'] for r,d in inner_fit}
    if fit_people & INNER: raise RuntimeError('Inner participant leakage')
    inner_models = fit(inner_fit); inner_scores = []
    for tau, blend in GRID:
        summary, *_ = evaluate(inner_score, inner_models, cfg, tau, blend)
        inner_scores.append(dict(tau_s=tau, wheel_blend=blend, **summary))
        print(f'Inner tau={tau:g} blend={blend:g}: {summary["equal_participant_mean_position_rmse_m"]*1000:.3f} mm', flush=True)
    chosen = min(inner_scores, key=lambda x: x['equal_participant_mean_position_rmse_m'])
    models = fit(train)
    # Lock choice before any validation recordings are loaded or predictions computed.
    out.mkdir()
    save_json(out/'training_selection.json', dict(chosen=chosen, grid=inner_scores,
        inner_participants=sorted(INNER), inner_fit_trials=len(inner_fit), inner_score_trials=len(inner_score),
        training_ids=[r['id'] for r,d in train], validation_used_for_selection=False))
    save_json(out/'empirical_calibration.json', models)
    validation = [(r,d) for r,d,_ in observed_rows(source, cfg, 'validation', manifest)]
    if len(validation) != 71 or {r['participant'] for r,d in validation} & {r['participant'] for r,d in train}:
        raise RuntimeError('Validation coverage or separation changed')
    selected, selected_rows, people, conditions = evaluate(validation, models, cfg, chosen['tau_s'], chosen['wheel_blend'])
    plain, plain_rows, _, _ = evaluate(validation, models, cfg, 0., 0.)
    cal = json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    tcn, champion = load_predictor(ROOT/'outputs_amended_v2', 'tcn32'), load_planar()
    with np.load(ridge_path/'linear_artifacts.npz') as z:
        mean, std, cap = z['mean'], z['std'], z['cap']
        coefficients = z[f'weights_{ridge_selection["best"]["alpha"]}']
    ridge_rows = []
    for row, data in validation:
        x, motion = imu_features(data, cal, tcn, champion)
        motion = motion+ridge_selection['best']['gain']*np.clip(np.c_[(x-mean)/std, np.ones(len(x))]@coefficients, -cap, cap)
        xy, heading = integrate_planar(data['t'], motion, data['gt_xy'][0], data['gt_heading'][0], data['imu_valid'])
        ridge_rows.append(dict(id=row['id'], participant=row['participant'], condition=row['condition'], **metrics(data, xy, heading, cfg)))
    ridge, _, _ = summarize(ridge_rows)
    if abs(ridge['equal_participant_mean_position_rmse_m']-ridge_selection['best']['equal_participant_mean_position_rmse_m']) > 1e-8:
        raise RuntimeError('Frozen ridge reproduction differs')
    for prefix, rows in [('selected_trials', selected_rows), ('selected_participants', people),
                         ('selected_maneuvers', conditions), ('static_trials', plain_rows), ('ridge_trials', ridge_rows)]:
        write_csv(out/f'{prefix}.csv', rows)
    provenance = dict(ridge_selection['provenance'])
    for file in [Path(__file__), source/'artifact_manifest.json', source/'run.json', ridge_path/'artifact_manifest.json',
                 ridge_path/'selection.json', ridge_path/'linear_artifacts.npz']:
        provenance[str(file.relative_to(ROOT))] = digest(file)
    save_json(out/'selection.json', dict(selected_physics=selected, static_empirical=plain, frozen_ridge=ridge,
        chosen_before_validation=chosen, training_trials=len(train), validation_trials=len(validation),
        provenance=provenance, test_evaluated=False, runtime_s=time.perf_counter()-started,
        inference='causal raw IMU/time/validity; initial reference XY/heading once; no later pose reset',
        scope='empirical bounded yaw-bias state comparator; no full attitude, verified SI conversion or Wheel-INS equivalence'))
    score = selected['equal_participant_mean_position_rmse_m']*1000
    reference = ridge['equal_participant_mean_position_rmse_m']*1000
    lines = ['# Empirical physics state comparator v9', '',
        f'Selected physics comparator: **{score:.3f} mm**. Static empirical comparator: **{plain["equal_participant_mean_position_rmse_m"]*1000:.3f} mm**. Frozen ridge: **{reference:.3f} mm**.', '',
        '473 observed training recordings; 71 validation recordings/four participants. Hyperparameters locked using a four-person inner holdout from training participants before validation loading. No test signals opened. All scored on identical v7 camera-supported frames.', '',
        '| Inner selection tau (s) | Wheel blend | Inner RMSE (mm) |', '|---:|---:|---:|']
    lines += [f'| {s["tau_s"]:g} | {s["wheel_blend"]:g} | {s["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for s in inner_scores]
    lines += ['', '## What was implemented', '',
        'Balanced empirical six-wheel-gyro linear forward/yaw conversion and three-chassis-gyro yaw conversion, fitted per setup. A causal IMU-only stationary detector uses training-learned gyro-norm gates and gravity-norm bounds, requiring 0.5 s continuous support. During detected rest, bounded chassis-yaw bias moves toward its measured yaw and motion is zeroed. Robust wheel/chassis disagreement downweights wheel-yaw blending; disagreement is not called a physical slip label. There is no continuous optical feedback or trajectory alignment.', '',
        '## Limits and honest interpretation', '',
        'CSV serialization, complete mounting rotations and rotating lever-arm vectors remain unverified. Consequently this is not a full attitude/bias INS, Wheel-INS2 reproduction, or calibrated physical slip estimator. The comparator assumes zero lateral velocity; the frozen ridge retains its learned lateral component. The gyro-norm detector can confuse extremely slow motion with rest. Thresholds, scale and cap are trained, not physical truth. Earlier participant identities are partly unmapped; known target participants are separated in the inner fold. Frozen reference preparation and clock mapping were inherited from the full development training protocol, so this is parameter selection conditional on that fixed preparation, not a completely independent end-to-end nested validation.', '',
        f'Keep the existing ridge model if it remains lower on validation; this comparator differs from it by {(score-reference):.3f} mm. No further validation tuning was performed.']
    (out/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    save_json(out/'artifact_manifest.json', dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()}))
    print(f'Validation selected physics {score:.3f} mm; ridge {reference:.3f} mm', flush=True)


if __name__ == '__main__':
    main()
