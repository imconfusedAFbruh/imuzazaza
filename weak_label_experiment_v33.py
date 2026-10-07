"""Confidence-weighted stored-processed endpoint supervision.

Adds weak endpoint equations to unchanged v21 observed equations; derivative
labels, normalization, clipping, calibration and inherited base stay fixed.
Selection uses the original training participant fold. Test data are forbidden.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import json
import time
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT, digest, save_json, write_csv, metrics, summarize
from nonlinear_endpoint_experiment_v21 import load_train, bounds, adapted, nonlinear_features, FOLD
from motion_endpoint_experiment_v16 import normal_system, fit, score, HORIZONS
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix, correction
from trajectory_calibration_v10 import integrate

OUT = ROOT / 'outputs_weak_labels_v33'
WEIGHTS = (0., .1, .25, .5)


def added_endpoint_systems(e, mean, std):
    """Separate one/two processed endpoint equations, never altering old pairs."""
    old = e['data']; d = e['restored']; m = e['motion']
    z = np.c_[(e['x'] - mean) / std, np.ones(len(m))]
    p = z.shape[1]; t = old['t']; dt = np.diff(t)
    v = (m[1:] + m[:-1]) / 2; zm = (z[1:] + z[:-1]) / 2
    h = np.r_[0., np.cumsum(dt * v[:, 2])]
    middle = (h[1:] + h[:-1]) / 2; c, s = np.cos(middle), np.sin(middle)
    qh = np.vstack((np.zeros(p), np.cumsum(dt[:, None] * zm, axis=0)))
    qm = (qh[1:] + qh[:-1]) / 2
    xy = np.vstack((np.zeros(2), np.cumsum(dt[:, None] * np.c_[v[:, 0]*c-v[:, 1]*s, v[:, 0]*s+v[:, 1]*c], axis=0)))
    px = np.vstack((np.zeros(2*p), np.cumsum(dt[:, None]*np.c_[c[:, None]*zm, (-s*v[:, 0]-c*v[:, 1])[:, None]*qm], axis=0)))
    py = np.vstack((np.zeros(2*p), np.cumsum(dt[:, None]*np.c_[s[:, None]*zm, (c*v[:, 0]-s*v[:, 1])[:, None]*qm], axis=0)))
    invalid = np.r_[0, np.cumsum(~old['imu_valid'])]
    aa = {1: [], 2: []}; yy = {1: [], 2: []}; old_pairs = 0
    for a in range(0, len(m), 100):
        if not d['gt_valid'][a]:
            continue
        for horizon in HORIZONS:
            b = a + horizon
            if b >= len(m) or not d['gt_valid'][b] or invalid[b+1] != invalid[a]:
                continue
            weak_count = int(not old['gt_valid'][a]) + int(not old['gt_valid'][b])
            if not weak_count:
                old_pairs += 1
                continue
            delta = xy[b] - xy[a]; ca, sa = np.cos(h[a]), np.sin(h[a])
            rot = np.array([[ca, sa], [-sa, ca]])
            pred = np.r_[rot @ delta, h[b]-h[a]]
            js = np.zeros((3, 2*p))
            js[:2] = rot @ np.vstack((px[b]-px[a], py[b]-py[a]))
            dh = np.r_[np.zeros(p), qh[a]]
            js[:2] += np.array([pred[1], -pred[0]])[:, None]*dh[None, :]
            js[2, p:] = qh[b]-qh[a]
            h0 = d['gt_heading'][a]; delta_gt = d['gt_xy'][b]-d['gt_xy'][a]
            target = np.r_[np.array([[np.cos(h0), np.sin(h0)], [-np.sin(h0), np.cos(h0)]]) @ delta_gt, d['gt_heading'][b]-h0]
            err = target-pred; err[2] = np.arctan2(np.sin(err[2]), np.cos(err[2]))
            duration = t[b]-t[a]
            aa[weak_count].append(js/duration); yy[weak_count].append(err/duration)
    results = {}
    for count in (1, 2):
        if aa[count]:
            a = np.array(aa[count]).reshape(-1, 2*p); y = np.array(yy[count]).reshape(-1)
            results[count] = (a.T @ a, a.T @ y, len(aa[count]))
        else:
            results[count] = (np.zeros((2*p, 2*p)), np.zeros(2*p), 0)
    return old_pairs, results


def confidence_systems(entries):
    original = normal_system(entries)
    additions = {}
    audit = []
    for setup, system in original.items():
        es = [e for e in entries if e['setup'] == setup]
        group_counts = Counter(); pending = []
        for e in es:
            old_pairs, extra = added_endpoint_systems(e, system['mean'], system['std'])
            group_counts[e['group']] += old_pairs
            pending.append((e['group'], extra))
            audit.append(dict(id=e['row']['id'], setup=setup, group=e['group'], observed_pairs=old_pairs,
                              one_processed_pairs=extra[1][2], two_processed_pairs=extra[2][2]))
        if sum(group_counts.values()) != system['endpoint_pairs']:
            raise RuntimeError('Observed pair count differs')
        goodgroups = sum(n > 0 for n in group_counts.values())
        ce = {k: np.zeros_like(system['endpoint']) for k in (1, 2)}
        re = {k: np.zeros_like(system['endpoint_rhs']) for k in (1, 2)}
        totals = Counter(); unsupported = 0
        for group, extra in pending:
            if not group_counts[group]:
                unsupported += sum(extra[k][2] for k in (1, 2))
                continue
            denominator = goodgroups*group_counts[group]
            for k in (1, 2):
                c, r, n = extra[k]
                ce[k] += c/denominator; re[k] += r/denominator; totals[k] += n
        additions[setup] = dict(cov=ce, rhs=re, pairs=totals, unsupported_pairs=unsupported)
        print('Weak systems', setup, 'one/two processed pairs', dict(totals), 'unsupported', unsupported, flush=True)
    return original, additions, audit


def weighted_system(original, added, confidence):
    systems = {}
    for setup, q in original.items():
        a = added[setup]
        systems[setup] = dict(q,
            endpoint=q['endpoint']+confidence*a['cov'][1]+confidence**2*a['cov'][2],
            endpoint_rhs=q['endpoint_rhs']+confidence*a['rhs'][1]+confidence**2*a['rhs'][2])
    return systems


def name(weight):
    return 'confidence_' + str(weight).replace('.', 'p')


def main():
    started = time.perf_counter(); torch.set_num_threads(4)
    if OUT.exists():
        raise RuntimeError('Preserve previous v33 weak-label run')
    OUT.mkdir(); (OUT/'trajectories').mkdir()
    original_model = json.loads((ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text())
    candidate = {k: original_model['candidate'][k] for k in ('basis', 'alpha', 'endpoint_weight', 'gain')}
    source = ROOT/'outputs_observed_reference_v7'
    cfg = json.loads((source/'run.json').read_text())['settings']
    recovered = ROOT/'outputs_recovered_training_v32'
    recovered_manifest = json.loads((recovered/'artifact_manifest.json').read_text())['sha256']
    save_json(OUT/'protocol.json', dict(confidences=WEIGHTS, endpoint_pair_confidence='Product of endpoint confidence: observed=1; stored-processed=w. Original observed pairs always weight1.',
        added_equation_normalization='Original observed endpoint-pair denominators per training group. Groups without any observed pairs contribute no new weak equations.',
        point_labels='Only unchanged original observed derivatives', normalization='Unchanged observed-label feature statistics and clipping/caps',
        fold=sorted(FOLD), parameters=candidate, training_trials=473, validation_trials=71,
        selection='Minimum observed-frame equal-participant training-fold RMSE under <=5% worst-participant regression against confidence0.',
        caveat='Conditional correction selection: inherited base/calibration already saw training-fold participants. Reused validation is exploratory.',
        calibration_refitted=False, base_model_refitted=False, test_accessed=False))
    train = load_train(ROOT/'outputs_motion_endpoint_v16')
    for e in train:
        path = recovered/'training_reference'/(e['row']['id']+'.npz')
        if digest(path) != recovered_manifest[str(path.relative_to(recovered))]:
            raise RuntimeError('Recovered training cache changed: '+path.name)
        with np.load(path, allow_pickle=False) as z:
            if not np.array_equal(z['original_observed_valid'], e['data']['gt_valid']):
                raise RuntimeError('Original mask differs')
            e['restored'] = {k: z[k] for k in ('gt_xy', 'gt_heading', 'gt_valid')}
        valid = e['data']['gt_valid']
        if not np.array_equal(e['restored']['gt_xy'][valid], e['data']['gt_xy'][valid]):
            raise RuntimeError('Original observed coordinates differ')
    inner = [e for e in train if e['row']['participant'] in FOLD]
    fitting = [e for e in train if e['row']['participant'] not in FOLD]
    clips = bounds(fitting); fitrows = adapted(fitting, candidate['basis'], clips)
    innerrows = adapted(inner, candidate['basis'], clips)
    original, added, audit = confidence_systems(fitrows)
    write_csv(OUT/'inner_endpoint_pair_audit.csv', audit)
    selection = []; all_inner_trials = []; all_inner_people = []; base_people = None
    for weight in WEIGHTS:
        fits = fit(weighted_system(original, added, weight), candidate['alpha'], candidate['endpoint_weight'])
        (summary, people, _), records = score(innerrows, fits, candidate, cfg)
        if base_people is None:
            base_people = {p['participant']: p['mean_trial_position_rmse_m'] for p in people}
        result = dict(confidence=weight, name=name(weight), score=summary['equal_participant_mean_position_rmse_m'],
            heading=summary['equal_participant_mean_heading_rmse_deg'],
            worst_person_ratio=max(p['mean_trial_position_rmse_m']/base_people[p['participant']] for p in people))
        selection.append(result); all_inner_trials.extend(dict(confidence=weight, **r) for r in records)
        all_inner_people.extend(dict(confidence=weight, **r) for r in people)
        print('Training-fold confidence result', result, flush=True)
    selected = min((q for q in selection if q['worst_person_ratio'] <= 1.05), key=lambda q: q['score'])
    save_json(OUT/'selection.json', dict(selected=selected, candidates=selection, validation_used_for_selection=False))
    write_csv(OUT/'inner_trials.csv', all_inner_trials); write_csv(OUT/'inner_participants.csv', all_inner_people)
    del original, added, innerrows, fitrows, fitting, inner
    clips = bounds(train); allrows = adapted(train, candidate['basis'], clips)
    original, added, audit = confidence_systems(allrows)
    write_csv(OUT/'all_training_endpoint_pair_audit.csv', audit)
    models = {}
    for weight in WEIGHTS:
        fits = fit(weighted_system(original, added, weight), candidate['alpha'], candidate['endpoint_weight'])
        model = dict(candidate=candidate, fits=fits, feature_clip=clips, confidence=weight,
                     training_ids=[e['row']['id'] for e in train], test_accessed=False)
        models[name(weight)] = model; save_json(OUT/(name(weight)+'_model.json'), model)
    control = models[name(0.)]
    coefficient_delta = max(float(np.max(np.abs(np.array(control['fits'][k]['weights'])-original_model['fits'][k]['weights']))) for k in control['fits'])
    if coefficient_delta > 1e-6:
        raise RuntimeError('Confidence0 does not reproduce v21 coefficients')
    train_people = {e['row']['participant'] for e in train}
    del train, allrows, original, added
    cal = json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    states = {q['id']: q for q in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
    manifest = json.loads((source/'artifact_manifest.json').read_text()); ridge = load_observed_ridge()
    records = {k: [] for k in models}
    for row, d, _ in observed_rows(source, cfg, 'validation', manifest):
        if row['participant'] in train_people:
            raise RuntimeError('Participant leakage')
        sensor = {k: d[k] for k in ('setup', 't', 'raw', 'imu_valid')}; motion = ridge(sensor)
        x = feature_matrix(sensor, motion, cal[row['setup']], states[row['id']], 'gravity_rotation')
        e = dict(row=row, data=d, motion=motion, linear=x, nonlinear=nonlinear_features(x), setup=row['setup'])
        arrays = dict(time_s=d['t'], reference_xy_m=d['gt_xy'], reference_heading_rad=d['gt_heading'], reference_valid=d['gt_valid'], imu_valid=d['imu_valid'])
        # Retain v32 display only; these extra positions never enter scores.
        with np.load(recovered/'trajectories'/(row['id']+'.npz'), allow_pickle=False) as z:
            for k in ('stored_reference_xy_m', 'stored_reference_valid', 'stored_processed_valid'):
                arrays[k] = z[k]
        for key, model in models.items():
            ee = adapted([e], candidate['basis'], model['feature_clip'])[0]
            m = correction(dict(ee, x={'gravity_rotation': ee['x']}), model['fits'], dict(candidate, mode='gravity_rotation'))
            xy, h = integrate(d, m)
            records[key].append(dict(id=row['id'], participant=row['participant'], condition=row['condition'], **metrics(d, xy, h, cfg)))
            arrays[key+'_xy_m'] = xy; arrays[key+'_heading_rad'] = h; arrays[key+'_motion'] = m
        np.savez_compressed(OUT/'trajectories'/(row['id']+'.npz'), **arrays)
    summaries = {}
    for key, rows in records.items():
        summaries[key], people, maneuvers = summarize(rows)
        for suffix, values in [('trials', rows), ('participants', people), ('maneuvers', maneuvers)]:
            write_csv(OUT/(key+'_'+suffix+'.csv'), values)
    expected = json.loads((ROOT/'outputs_trajectory_best_v21/summary.json').read_text())['models']['Nonlinear interval correction v21']['equal_participant_mean_position_rmse_m']
    if abs(summaries[name(0.)]['equal_participant_mean_position_rmse_m']-expected) > 1e-8:
        raise RuntimeError('Confidence0 validation reproduction failed')
    result = dict(summary=summaries, selected=selected, training_trials=473, validation_trials=71,
                  control_max_coefficient_difference=coefficient_delta, test_accessed=False,
                  base_model_refitted=False, calibration_refitted=False, validation_used_for_selection=False,
                  runtime_seconds=time.perf_counter()-started,
                  source_sha256={str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), recovered/'artifact_manifest.json',
                      ROOT/'outputs_nonlinear_endpoint_v21/model.json', ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json', source/'artifact_manifest.json', ROOT/'outputs_amended_v2/split.json']})
    save_json(OUT/'run.json', result)
    lines = ['# Confidence-weighted recovered endpoint experiment v33', '',
             'Original observed endpoints retain full weight. One processed endpoint contributes weight w; two contribute w². Original observed derivative labels, fitting statistics, nonlinear clipping and caps remain unchanged. No processed derivative labels enter this model.', '',
             f'Training-fold selection: {selected}', '', '| Confidence | Validation RMSE (mm) |', '|---|---:|']
    lines += [f'| {models[k]["confidence"]} | {s["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for k, s in summaries.items()]
    lines += ['', 'Scores use unchanged directly-observed v7 reference frames for all71 validation trajectories. All473 training records remain present. Confidence0 reproduces originalv21 coefficients and validation score. The selected model is determined solely by the training fold; all reported validation variants are exploratory. Full nested base/calibration fitting remains outstanding. Test recordings were untouched.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    save_json(OUT/'artifact_manifest.json', dict(sha256={str(p.relative_to(OUT)): digest(p) for p in OUT.rglob('*') if p.is_file()}))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
