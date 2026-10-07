"""Training-only balanced ridge motion correction on observed-reference v7."""
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from pipeline import ROOT, digest, save_json, write_csv, velocities, metrics, summarize
from learning import load_predictor, training_group
from planar_experiment import verify_parent, planar_features, lateral_labels, integrate_planar
from observed_reference_experiment import load_planar
from observed_training_experiment import observed_rows


def imu_features(data, cal, tcn_predict, champion):
    """Prediction features receive only IMU signals, setup and time validity."""
    imu = {key: data[key] for key in ('setup', 't', 'raw', 'imu_valid')}
    base = velocities(imu, cal[str(imu['setup'])])
    tcn = tcn_predict(imu, base)
    motion = champion(imu, cal, tcn_predict)
    x = np.c_[planar_features(imu, base, tcn, cal), motion]
    if x.shape[1] != 31 or not np.isfinite(x).all():
        raise RuntimeError('Invalid feature schema')
    return x, motion


def main():
    started = time.perf_counter()
    source, parent = ROOT/'outputs_observed_reference_v7', ROOT/'outputs_amended_v2'
    out = ROOT/'outputs_observed_ridge_v8'
    if out.exists():
        raise RuntimeError('Preserve existing experiment')
    provenance = verify_parent(parent)
    manifest = json.loads((source/'artifact_manifest.json').read_text())
    for name, sha in manifest['sha256'].items():
        if digest(source/name) != sha:
            raise RuntimeError(f'Observed artifact changed: {name}')
    run = json.loads((source/'run.json').read_text())
    for name, sha in run['provenance'].items():
        if digest(ROOT/name) != sha:
            raise RuntimeError(f'Observed dependency changed: {name}')
    old = json.loads((ROOT/'outputs_planar_neural_v4/selection.json').read_text())
    for name, sha in old['artifacts'].items():
        if digest(name) != sha:
            raise RuntimeError(f'Frozen planar artifact changed: {name}')
    torch.set_num_threads(4)
    cfg = run['settings']
    cal = json.loads((parent/'calibration.json').read_text())
    tcn_predict, champion = load_predictor(parent, 'tcn32'), load_planar()
    xs, ys, group_ids, train_ids, train_people = [], [], [], [], set()
    for row, data, _ in observed_rows(source, cfg, 'train', manifest):
        x, motion = imu_features(data, cal, tcn_predict, champion)
        side, valid = lateral_labels(data, hz=cfg['hz'], cutoff=cfg['derivative_hz'])
        target = np.c_[data['gt_v'], side, data['gt_yaw']] - motion
        valid &= data['label_valid'] & data['imu_valid'] & np.isfinite(target).all(axis=1)
        xx, yy = x[valid][::10], target[valid][::10]
        xs.append(xx); ys.append(yy)
        group_ids.extend([training_group(row)]*len(xx))
        train_ids.append(row['id']); train_people.add(row['participant'])
        if len(train_ids)%50 == 0:
            print(f'{len(train_ids)} observed training sequences', flush=True)
    if len(train_ids) != 473:
        raise RuntimeError('Training coverage differs from sealed v7')
    x, y = np.concatenate(xs), np.concatenate(ys)
    counts = Counter(group_ids)
    weights = np.array([1/counts[g] for g in group_ids]); weights /= weights.sum()
    mean = np.sum(x*weights[:,None],axis=0)
    std = np.maximum(np.sqrt(np.sum((x-mean)**2*weights[:,None],axis=0)),1e-5)
    design = np.c_[(x-mean)/std, np.ones(len(x))]
    covariance = design.T@(design*weights[:,None])
    rhs = design.T@(y*weights[:,None])
    cap = np.quantile(np.abs(y), .995, axis=0)
    fits = {}
    for alpha in (.001, .1, 10.):
        penalty = np.eye(design.shape[1])*alpha; penalty[-1,-1] = 0.
        fits[alpha] = np.linalg.solve(covariance+penalty, rhs)
    validation = []
    for row, data, _ in observed_rows(source, cfg, 'validation', manifest):
        if row['participant'] in train_people:
            raise RuntimeError('Participant leakage')
        x, motion = imu_features(data, cal, tcn_predict, champion)
        validation.append((row, data, motion, np.c_[(x-mean)/std,np.ones(len(x))]))
    if len(validation) != 71:
        raise RuntimeError('Validation coverage differs from sealed v7')
    candidates, all_records, details = [], [], {}
    for alpha, gain in [(0.,0.)]+[(a,g) for a in fits for g in (.25,.5,1.)]:
        records = []
        for row, data, base, design_val in validation:
            motion = base.copy()
            if gain:
                motion += gain*np.clip(design_val@fits[alpha],-cap,cap)
            xy, heading = integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
            record = dict(id=row['id'],participant=row['participant'],condition=row['condition'],
                          alpha=alpha,gain=gain,**metrics(data,xy,heading,cfg))
            if not np.isfinite(record['position_rmse_m']):
                raise RuntimeError('Nonfinite reconstruction')
            records.append(record)
        summary, people, conditions = summarize(records)
        if summary['trials'] != 71 or summary['participants'] != 4:
            raise RuntimeError('Candidate coverage changed')
        candidates.append(dict(alpha=alpha,gain=gain,**summary))
        details[(alpha,gain)] = (records,people,conditions)
        all_records.extend(records)
        print(f'alpha={alpha:g} gain={gain:g}: {summary["equal_participant_mean_position_rmse_m"]*1000:.3f} mm',flush=True)
    expected = json.loads((source/'comparison.json').read_text())['candidates']['corrected_initialization_same_observed_frames']['equal_participant_mean_position_rmse_m']
    if abs(candidates[0]['equal_participant_mean_position_rmse_m']-expected)>1e-8:
        raise RuntimeError('Frozen champion reproduction differs')
    best = min(candidates,key=lambda c:c['equal_participant_mean_position_rmse_m'])
    out.mkdir()
    np.savez(out/'linear_artifacts.npz',mean=mean,std=std,cap=cap,**{f'weights_{a}':w for a,w in fits.items()})
    save_json(out/'normalization.json',dict(mean=mean.tolist(),std=std.tolist(),residual_cap=cap.tolist(),
         training_ids=train_ids,training_groups=dict(counts),training_samples=len(x),
         feature_schema='28 frozen planar IMU features plus frozen champion forward/lateral/yaw motion',
         target='observed-reference forward/lateral/yaw minus frozen champion motion',
         fit='equal group total weight; within group equal subsampled valid frames; pooled training .995 absolute residual cap'))
    for prefix, key in [('selected',(best['alpha'],best['gain'])),('champion',(0.,0.))]:
        for suffix, records in zip(('trials','participants','maneuvers'),details[key]):
            write_csv(out/f'{prefix}_{suffix}.csv',records)
    write_csv(out/'all_candidates_trials.csv',all_records)
    paths = [Path(__file__),ROOT/'observed_training_experiment.py',ROOT/'observed_reference_experiment.py',
             ROOT/'planar_experiment.py',ROOT/'planar_neural_experiment.py',source/'artifact_manifest.json',
             source/'run.json',ROOT/'outputs_planar_neural_v4/all_three.pt',ROOT/'outputs_planar_neural_v4/normalization.json']
    provenance.update({str(f.relative_to(ROOT)):digest(f) for f in paths})
    save_json(out/'selection.json',dict(best=best,candidates=candidates,training_trials=len(train_ids),
         validation_trials=len(validation),provenance=provenance,runtime_seconds=time.perf_counter()-started,
         test_evaluated=False,scope='Exploratory reused-validation selection; corrected observation reference and initial pose; no trajectory alignment.'))
    baseline = candidates[0]['equal_participant_mean_position_rmse_m']
    score = best['equal_participant_mean_position_rmse_m']
    report = ['# Observed-reference balanced ridge correction v8','',
        'Training-only affine/ridge residual over the frozen planar champion. Same 473 training and 71 validation recordings as sealed v7; four held-out validation participants. Physical calibration and champion remain frozen. No test signals opened.','',
        f'Champion: **{baseline*1000:.3f} mm**. Selected: **{score*1000:.3f} mm** (alpha {best["alpha"]}, gain {best["gain"]}). Improvement: {(baseline-score)*1000:.3f} mm / {(1-score/baseline)*100:.3f}%.','',
        '| Alpha | Gain | Validation RMSE (mm) |','|---:|---:|---:|']
    report += [f'| {c["alpha"]:g} | {c["gain"]:g} | {c["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for c in candidates]
    report += ['', 'Features are restricted to raw IMU, setup, timestamps and IMU validity before prediction; no reference feature access. Normalization, weights and clipping caps use training only. Positive-residual camera-supported optical frames supply gap-masked training targets and evaluation. Known initial pose only. Group weighting treats known participants equally and unmapped earlier sessions by date. The fixed candidate grid includes the unchanged champion. Reused validation remains exploratory.']
    (out/'report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    save_json(out/'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()}))


if __name__ == '__main__':
    main()
