"""TRAIN-only exact linear displacement supervision for forward-speed residuals."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import json
import time
from collections import defaultdict
import numpy as np
import pipeline as p
from braking_hysteresis_folds_v56 import prepare_entry
from projected_yaw_folds_v52 import proxy
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from participant_folds_experiment_v24 import FOLDS
from trajectory_calibration_v10 import integrate
from research_metrics_v59 import trajectory_metrics, aggregate

OUT = p.ROOT / 'outputs_interval_speed_v60'
GAINS = (0., .25, .5)
POINT_WEIGHTS = (0., .3)
HORIZONS = (100, 300, 500)


def interval_system(entries, setup, model):
    mean, std = np.asarray(model['mean']), np.asarray(model['std'])
    size = len(mean) + 1
    point = defaultdict(lambda: [np.zeros((size, size)), np.zeros(size), 0])
    endpoint = defaultdict(lambda: [np.zeros((size, size)), np.zeros(size), 0])
    for e in entries:
        if e['setup'] != setup:
            continue
        d, m = e['data'], e['motion']
        z = np.c_[(e['features'] - mean) / std, np.ones(len(m))]
        idx = np.flatnonzero(e['label'])[::5]
        a, y = z[idx], e['target'][idx]
        q = point[e['group']]
        q[0] += a.T @ a; q[1] += a.T @ y; q[2] += len(idx)
        dt = np.diff(d['t'])
        h = np.r_[0., np.cumsum(dt * (m[1:, 2] + m[:-1, 2]) / 2)]
        mid = (h[1:] + h[:-1]) / 2
        zm = (z[1:] + z[:-1]) / 2
        velocity = (m[1:, 0] + m[:-1, 0]) / 2
        jx = np.vstack((np.zeros(size), np.cumsum(dt[:, None] * np.cos(mid)[:, None] * zm, axis=0)))
        jy = np.vstack((np.zeros(size), np.cumsum(dt[:, None] * np.sin(mid)[:, None] * zm, axis=0)))
        xy = np.vstack((np.zeros(2), np.cumsum(dt[:, None] * velocity[:, None] * np.c_[np.cos(mid), np.sin(mid)], axis=0)))
        invalid = np.r_[0, np.cumsum(~d['imu_valid'])]
        aa, yy = [], []
        for start in range(0, len(m), 100):
            if not d['gt_valid'][start]:
                continue
            for horizon in HORIZONS:
                end = start + horizon
                if end >= len(m) or not d['gt_valid'][end] or invalid[end + 1] != invalid[start]:
                    continue
                angle = h[start]
                rot = np.array([[np.cos(angle), np.sin(angle)], [-np.sin(angle), np.cos(angle)]])
                truth_angle = d['gt_heading'][start]
                truth_rot = np.array([[np.cos(truth_angle), np.sin(truth_angle)], [-np.sin(truth_angle), np.cos(truth_angle)]])
                target = truth_rot @ (d['gt_xy'][end] - d['gt_xy'][start])
                prediction = rot @ (xy[end] - xy[start])
                duration = d['t'][end] - d['t'][start]
                aa.append((rot @ np.vstack((jx[end] - jx[start], jy[end] - jy[start]))) / duration)
                yy.append((target - prediction) / duration)
        if aa:
            a, y = np.asarray(aa).reshape(-1, size), np.asarray(yy).reshape(-1)
            q = endpoint[e['group']]
            q[0] += a.T @ a; q[1] += a.T @ y; q[2] += len(aa)
    def average(groups):
        good = [q for q in groups.values() if q[2]]
        return sum(q[0] / q[2] for q in good) / len(good), sum(q[1] / q[2] for q in good) / len(good)
    return average(point), average(endpoint)


def predict(e, model, gain):
    m = e['motion'].copy()
    if gain:
        z = np.c_[(e['features'] - model['mean']) / model['std'], np.ones(len(m))]
        residual = np.clip(z @ model['coef'], -model['cap_mps'], model['cap_mps'])
        residual[~e['data']['imu_valid']] = 0.
        m[:, 0] += gain * residual
    return m


def main():
    started = time.perf_counter()
    OUT.mkdir(exist_ok=False)
    q = json.loads((p.ROOT / 'outputs_clock_arbitrated_v42/protocol.json').read_text())
    cfg = q['old_clock_settings']; fallback = set(q['fallback_old_clock_ids'])
    inv = {r['id']: r for r in json.loads((p.ROOT / 'outputs_amended_v2/inventory.json').read_text())}
    manifests = {s: json.loads((s / 'artifact_manifest.json').read_text()) for s in (OLD, NEW)}
    people = set.union(*FOLDS)
    trials = []
    for ident in q['training_ids']:
        r = inv[ident]
        if r['participant'] not in people:
            continue
        assert r['partition'] == 'train'
        d, _ = load_cache(OLD if ident in fallback else NEW, ident, manifests[OLD if ident in fallback else NEW])
        trials.append((r, d))
    assert len(trials) == 207
    v56 = json.loads((p.ROOT / 'outputs_braking_hysteresis_v56/fold_models.json').read_text())
    p.save_json(OUT / 'protocol.json', dict(hypothesis='Forward speed residuals supervised by 1/3/5s displacement may fix accumulated travel better than derivative targets',
        gains=GAINS, point_weights=POINT_WEIGHTS, alpha=1., horizons_frames=HORIZONS,
        feature_bank='v56 causal hysteresis; train-fold normalization/caps',
        baseline='v52 projected yaw with fold-refitted physics speed', scope='207 TRAIN, inherited frozen QC/clock/reference preparation',
        estimator_input='IMU features plus TRAIN-fitted constants; initial pose supplied once for evaluation',
        validation_accessed=False, test_accessed=False))
    records, frozen = [], []
    for fold, held in enumerate(FOLDS):
        original = v56[str(fold)]
        yaw = json.loads((p.ROOT / f'outputs_projected_yaw_v52/fold_{fold}_models.json').read_text())
        assert original['calibration'] == yaw['calibration']
        entries = []
        for r, d in trials:
            cal = original['calibration'][r['setup']]
            e = prepare_entry(r, d, cal)
            ym = yaw['yaw'][r['setup']]
            e['motion'][:, 2] = proxy(d, cal) * ym['scale'] + ym['intercept']
            entries.append(e)
        fitting = [e for e in entries if e['row']['participant'] not in held]
        evaluation = [e for e in entries if e['row']['participant'] in held]
        assert {e['row']['id'] for e in fitting} == set(original['fit_ids'])
        models = {weight: {} for weight in POINT_WEIGHTS}
        for setup, old in original['models'].items():
            (cp, rp), (ce, re) = interval_system(fitting, setup, old)
            reg = np.eye(len(rp)); reg[-1, -1] = 0.
            for weight in POINT_WEIGHTS:
                models[weight][setup] = dict(mean=old['mean'], std=old['std'],
                    coef=np.linalg.solve(ce + weight * cp + reg, re + weight * rp).tolist(), cap_mps=old['cap_mps'])
        for weight, fits in models.items():
            for gain in GAINS:
                if gain == 0 and weight != 0:
                    continue
                name = 'baseline' if not gain else f'point{weight:g}_gain{gain:g}'
                for e in evaluation:
                    m = predict(e, fits[e['setup']], gain)
                    xy, h = integrate(e['data'], m)
                    records.append(dict(method=name, fold=fold, id=e['row']['id'], participant=e['row']['participant'], condition=e['row']['condition'], **p.metrics(e['data'], xy, h, cfg)))
        p.save_json(OUT / f'fold_{fold}_models.json', dict(models=models, fit_ids=original['fit_ids'], held_ids=original['held_ids']))
        frozen.append((evaluation, models))
        print('Completed interval speed fold', fold, flush=True)
    p.write_csv(OUT / 'trials.csv', records)
    summaries = {}; participants = {}; maneuvers = {}
    for name in sorted({r['method'] for r in records}):
        summaries[name], participants[name], maneuvers[name] = p.summarize([r for r in records if r['method'] == name])
    expected = json.loads((p.ROOT / 'outputs_projected_yaw_v52/run.json').read_text())['selected']['score']
    assert abs(summaries['baseline']['equal_participant_mean_position_rmse_m'] - expected) < 1e-10
    bp = {r['participant']: r['mean_trial_position_rmse_m'] for r in participants['baseline']}
    bm = {r['condition']: r['equal_participant_mean_position_rmse_m'] for r in maneuvers['baseline']}
    candidates = []
    for name, s in summaries.items():
        pr = {r['participant']: r['mean_trial_position_rmse_m'] / bp[r['participant']] for r in participants[name]}
        mr = {r['condition']: r['equal_participant_mean_position_rmse_m'] / bm[r['condition']] for r in maneuvers[name]}
        candidates.append(dict(method=name, **s, participant_ratios=pr, maneuver_ratios=mr, worst_participant_ratio=max(pr.values()), worst_maneuver_ratio=max(mr.values())))
    selected = min((r for r in candidates if r['worst_participant_ratio'] <= 1.05 and r['worst_maneuver_ratio'] <= 1.05), key=lambda r:r['equal_participant_mean_position_rmse_m'])
    route_rows = []
    (OUT / 'trajectories').mkdir()
    for evaluation, models in frozen:
        for e in evaluation:
            for name in dict.fromkeys(('baseline', selected['method'])):
                weight, gain = (0., 0.) if name == 'baseline' else tuple(float(s) for s in name.replace('point', '').replace('_gain', ' ').split())
                m = predict(e, models[weight][e['setup']], gain)
                xy, h = integrate(e['data'], m)
                route_rows.append(dict(method=name, id=e['row']['id'], participant=e['row']['participant'], condition=e['row']['condition'], **trajectory_metrics(e['data'], xy, h)))
                np.savez_compressed(OUT / 'trajectories' / (e['row']['id'] + '__' + name + '.npz'), t=e['data']['t'], xy=xy, heading=h, motion=m, reference_xy=e['data']['gt_xy'], reference_heading=e['data']['gt_heading'], valid=e['data']['gt_valid'], imu_valid=e['data']['imu_valid'])
    p.write_csv(OUT / 'route_trials.csv', route_rows)
    p.save_json(OUT / 'run.json', dict(selected=selected, candidates=candidates, route_summary=aggregate(route_rows, ('method',)),
        runtime_s=time.perf_counter()-started, validation_accessed=False, test_accessed=False))
    p.save_json(OUT / 'artifact_manifest.json', dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps(selected), flush=True)


if __name__ == '__main__':
    main()
