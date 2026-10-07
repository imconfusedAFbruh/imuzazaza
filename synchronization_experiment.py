"""Development-only fine clock alignment over the frozen accepted recordings.

Run: python synchronization_experiment.py
No test signals, parameter sweep, or neural retraining. Outputs are immutable.
"""
import csv
import json
import time
from pathlib import Path

import numpy as np
import torch
from scipy import signal

import pipeline as p
from learning import load_predictor
from planar_experiment import cached_rows, verify_parent, planar_features
from planar_neural_experiment import PlanarResNet, predict_windows, evaluate_planar

COARSE_SYNCHRONIZE = p.synchronize


def refine_synchronize(t, raw, imu_valid, gt, cfg, setup=None):
    """Refine an already accepted basin using correlation, never position RMSE."""
    result = COARSE_SYNCHRONIZE(t, raw, imu_valid, gt, cfg, setup)
    step = float(cfg['sync_refinement_step_s'])
    radius = float(cfg['sync_refinement_radius_s'])
    if not 0 < step <= .001 or not 0 < radius <= .025:
        raise ValueError('Refinement requires step (0, .001] and radius (0, .025]')
    mode = result['source']
    terms = cfg.get('sync_terms', {}).get(setup)
    if mode == 'signed_yaw':
        c = terms[2]
        imu = raw[:, c['column']] * c['scale'] + c['intercept']
        ref = gt['yaw']
    elif mode == 'calibrated_speed':
        wheel = [raw[:, c['column']] * c['scale'] + c['intercept'] for c in terms[:2]]
        imu, ref = np.abs((wheel[0] + wheel[1]) / 2), np.abs(gt['speed'])
    elif mode == 'yaw':
        imu, ref = np.linalg.norm(raw[:, 15:18], axis=1), np.abs(gt['yaw'])
    elif mode == 'speed':
        imu = np.linalg.norm(raw[:, 3:6], axis=1) + np.linalg.norm(raw[:, 9:12], axis=1)
        ref = np.abs(gt['speed'])
    else:
        raise ValueError(f'Unknown alignment source: {mode}')
    ref_mask = gt['derivative_valid'] & np.isfinite(ref)
    a = p.smooth_standard(imu, cfg['hz'])
    b = p.smooth_standard(np.interp(gt['t'], gt['t'][ref_mask], ref[ref_mask]), gt['hz'])
    lag = result['offset_s']
    lo, hi = max(-cfg['max_lag_s'], lag - radius), min(cfg['max_lag_s'], lag + radius)
    # All lag candidates use identical native-rate samples and valid interpolation
    # brackets. Changing overlap or bridging packet gaps cannot increase a score.
    lower = np.clip(np.searchsorted(t, gt['t'] + lo) - 1, 0, len(t) - 1)
    upper = np.clip(np.searchsorted(t, gt['t'] + hi), 0, len(t) - 1)
    bad = np.r_[0, np.cumsum(~imu_valid)]
    valid = (ref_mask & (gt['t'] + lo >= t[0]) & (gt['t'] + hi <= t[-1])
             & (bad[upper + 1] == bad[lower]))
    result.update(coarse_offset_s=lag, refinement_step_s=step,
                  refinement_radius_s=radius, refinement_frames=int(valid.sum()))
    if valid.sum() < 3 * gt['hz']:
        return dict(result, refinement_status='kept_coarse_insufficient_common_support')
    rt, rb = gt['t'][valid], b[valid]
    ap, bp = (np.abs(a), np.abs(b)) if mode == 'signed_yaw' else (a, b)
    pi = signal.find_peaks(ap, prominence=cfg['peak_prominence'], distance=cfg['hz'] * cfg['peak_distance_s'])[0]
    pg = signal.find_peaks(bp, prominence=cfg['peak_prominence'], distance=gt['hz'] * cfg['peak_distance_s'])[0]
    pi, pg = pi[imu_valid[pi]], pg[ref_mask[pg]]
    pi, pg = pi[np.argsort(ap[pi])[-100:]], pg[np.argsort(bp[pg])[-100:]]

    def score(offset):
        residuals = p.match_peaks(t[pi], gt['t'][pg] + offset, cfg['peak_tolerance_s'])
        values = np.interp(rt + offset, t, a)
        corr = float(np.corrcoef(values, rb)[0, 1])
        if len(residuals) < cfg['min_peak_matches'] or not np.isfinite(corr):
            return -np.inf, []
        return corr, residuals

    initial, _ = score(lag)
    best_lag, best_corr = lag, initial
    evaluations = 1
    # ponytail: two fixed local grids; add a clock-drift model only with independent
    # timing evidence, rather than optimizing a trajectory against its reference.
    for grid_step, center, width in ((.001, lag, radius), (step, None, .001)):
        center = best_lag if center is None else center
        candidates = np.arange(np.ceil(max(lo, center - width) / grid_step),
                               np.floor(min(hi, center + width) / grid_step) + 1) * grid_step
        for candidate in candidates:
            corr, _ = score(float(candidate)); evaluations += 1
            if corr > best_corr:
                best_lag, best_corr = float(candidate), corr
    if best_corr < cfg['min_sync_corr'] or not np.isfinite(best_corr):
        return dict(result, refinement_status='kept_coarse_full_rate_gate', refinement_evaluations=evaluations)
    _, residuals = score(best_lag)
    return dict(result, offset_s=best_lag, correlation=best_corr, matched_peaks=len(residuals),
                peak_timing_median_abs_s=float(np.median(np.abs(residuals))),
                coarse_full_rate_correlation=initial, refinement_delta_s=best_lag - lag,
                refinement_evaluations=evaluations, refinement_status='refined',
                ambiguity_scope='inherited accepted coarse basin; local radius <=25 ms')


def neural_score(trials, source, cal, cfg, out, name):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tcn = load_predictor(source, 'tcn32')
    parent = p.ROOT / 'outputs_planar_neural_v4'
    norm = json.loads((parent / 'normalization.json').read_text())
    mean, std, scale, cap = [np.array(norm[k], np.float32) for k in ('mean','std','target_scale','residual_cap')]
    checkpoint = torch.load(parent / 'all_three.pt', map_location='cpu', weights_only=True)
    model = PlanarResNet().to(device).eval(); model.load_state_dict(checkpoint['state'])
    validation, predictions = [], {}
    for row, data, _ in trials:
        base = p.velocities(data, cal[row['setup']]); motion = tcn(data, base)
        x = (planar_features(data, base, motion, cal).astype(np.float32) - mean) / std
        predictions[id(data)] = np.clip(predict_windows(model, x, device) * scale, -cap, cap)
        validation.append((row, data, motion, x))
    summary, records, people, conditions = evaluate_planar(validation, predictions, cfg, 'all_three', checkpoint['gain'])
    folder = out / name; folder.mkdir()
    for label, rows in [('metrics',records),('participants',people),('maneuvers',conditions)]:
        p.write_csv(folder / ('validation_' + label + '.csv'), rows)
    p.save_json(folder / 'validation_summary.json', summary)
    return summary


def main():
    started = time.perf_counter(); torch.set_num_threads(4)
    source, out = p.ROOT / 'outputs_amended_v2', p.ROOT / 'outputs_synchronization_v5'
    if out.exists(): raise RuntimeError('Preserve existing run; choose a new version before rerunning')
    parent_hashes = verify_parent(source)
    neural_parent = json.loads((p.ROOT / 'outputs_planar_neural_v4/selection.json').read_text())
    for path, sha in neural_parent['artifacts'].items():
        if p.digest(path) != sha: raise RuntimeError(f'Neural parent artifact changed: {path}')
    cfg = json.loads((source / 'run.json').read_text())['settings']
    cal = json.loads((source / 'calibration.json').read_text())
    out.mkdir()
    inventory = {r['id']: r for r in json.loads((source / 'inventory.json').read_text())}
    refined_cfg = dict(cfg, sync_refinement_step_s=.0001, sync_refinement_radius_s=.025,
                       synchronization_protocol='v5: accepted coarse basin, fixed-support native-rate local correlation')
    results, alignment = {}, []
    refined_train, refined_validation, original_validation = [], [], []
    try:
        p.synchronize = refine_synchronize
        train_people = set()
        for partition in ('train', 'validation'):
            count = 0
            for cached_row, old_data in cached_rows(source, cfg, partition):
                row = inventory[cached_row['id']]
                if partition == 'train': train_people.add(row['participant'])
                elif row['participant'] in train_people: raise RuntimeError('Participant overlap')
                data, meta = p.prepare(row, p.ROOT, out, refined_cfg)
                alignment.append(dict(id=row['id'], partition=partition, participant=row['participant'],
                                      **meta['synchronization']))
                if partition == 'train': refined_train.append((row, data, meta))
                else:
                    refined_validation.append((row, data, meta))
                    original_validation.append((row, old_data, {}))
                count += 1
                if count % 25 == 0: print(f'{partition}: {count} refined', flush=True)
        if len(refined_train) != 477 or len(refined_validation) != 72:
            raise RuntimeError('Matched accepted coverage changed')
        new_cal = p.calibrate(refined_train, refined_cfg)
        del refined_train
        p.save_json(out / 'calibration.json', new_cal)
        for name, trials, calibration in [
            ('coarse_physics', original_validation, cal),
            ('refined_physics_frozen', refined_validation, cal),
            ('refined_physics_refit', refined_validation, new_cal)]:
            results[name] = p.evaluate(trials, calibration, refined_cfg, out, name=name, export=False)
        predict = load_predictor(source, 'tcn32')
        for prefix, trials in [('coarse',original_validation),('refined',refined_validation)]:
            results[prefix + '_tcn_frozen'] = p.evaluate(trials, cal, refined_cfg, out,
                  name=prefix + '_tcn_frozen', predictor=predict, export=False)
            results[prefix + '_planar_neural_frozen'] = neural_score(trials, source, cal, refined_cfg, out,
                  prefix + '_planar_neural_frozen')
    finally:
        p.synchronize = COARSE_SYNCHRONIZE
    if any(s['trials'] != 72 or s.get('failed_reconstructions') for s in results.values()):
        raise RuntimeError('Candidate reconstruction coverage differs')
    paths = [Path(__file__), source / 'run.json', source / 'inventory.json',
             p.ROOT / 'outputs_planar_neural_v4/selection.json', p.ROOT / 'config/default.yaml']
    provenance = dict(parent_hashes, **{str(path.relative_to(p.ROOT)):p.digest(path) for path in paths})
    p.save_json(out / 'alignment.json', alignment)
    p.save_json(out / 'run.json', dict(settings=refined_cfg, acquisition_range_g=2,
                  acquisition_evidence='researcher confirms actual +/-2g; encoding unverified',
                  train_trials=477,validation_trials=72,test_evaluated=False,
                  scope='Matched parent-accepted recordings; rejected recordings not revisited',
                  provenance=provenance))
    deltas = [a.get('refinement_delta_s', 0) for a in alignment if a['partition']=='validation']
    selection = dict(candidates=results, test_evaluated=False, neural_retrained=False,
                     validation_delta_median_abs_ms=float(np.median(np.abs(deltas))*1000),
                     runtime_seconds=time.perf_counter()-started,
                     interpretation='Offline alignment sensitivity; not independent timing accuracy. Neural weights frozen under original alignment.')
    p.save_json(out / 'comparison.json', selection)
    lines = ['# Synchronization refinement v5','','Matched 477 training and 72 validation recordings from the frozen accepted set. '
             'Original correlation/unique-peak gates remain. Native-rate local correlation uses identical valid support across candidates; '
             '1 ms then 0.1 ms grids search within 25 ms of the accepted coarse lag. No position metric selects a lag. '
             'The physics refit uses training only. Neural weights, normalization and calibration stay frozen. No test signals opened.','',
             '| Candidate | Equal-participant validation RMSE (mm) |','|---|---:|']
    for name, score in results.items():
        lines.append(f"| {name} | {1000*score['equal_participant_mean_position_rmse_m']:.3f} |")
    lines += ['',f"Median absolute validation lag adjustment: {selection['validation_delta_median_abs_ms']:.3f} ms.",
              '', 'Grid resolution is not a timing-accuracy measurement. Coarse correlation, native-rate correlation and peak residuals '
              'are alignment diagnostics. A single lag does not correct residual clock drift or frequency-dependent filtering delays. '
              'Repeated validation use remains exploratory. CSV units are still unverified; actual acceleration range is researcher-confirmed +/-2 g.','']
    (out / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(selection), flush=True)


if __name__ == '__main__': main()
