"""TRAIN-only trial-RMSE readout, with frozen v121 features and weight prior."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OPENBLAS_NUM_THREADS'] = '4'
import csv
import json
import time
from collections import Counter
import numpy as np
import torch
import pipeline as p
from reservoir_path_v121 import prediction, reservoir
from participant_folds_experiment_v24 import FOLDS
from nonlinear_endpoint_experiment_v21 import nonlinear_features, adapted
from dynamic_tilt_experiment_v33 import dynamic_features, expanded
from dynamic_tilt_blend_v34 import corrected_entry
from trajectory_calibration_v10 import integrate
from combined_physics_folds_v58 import verified_json
from metric_contract_v74 import metrics
from joint_robust_motion_v119 import balanced

OUT = p.ROOT/'outputs_trial_rmse_v124'
PENALTIES = (.1, 1., 10.)
GUARDS = ('Position_P95_mm', 'Last_Supported_Endpoint_Error_mm', 'heading_rmse_deg')


def objective(es, weights, lam, prior, normal=False):
    counts = Counter(e['row']['participant'] for e in es)
    delta = weights-prior
    loss = lam*np.sum(delta**2)
    cov = lam*np.eye(34)
    rhs = -lam*delta.T.ravel()
    for e in es:
        result = prediction(e, weights, normal)
        _, xy, heading = result[:3]
        d, ix = e['data'], e['ix']
        err = np.c_[xy[ix]-d['gt_xy'][ix],
                    np.angle(np.exp(1j*(heading[ix]-d['gt_heading'][ix])))]*10
        trial_weight = 1/(len(counts)*counts[e['row']['participant']])
        for columns, gain in ((slice(0, 2), 1.), (slice(2, 3), .1)):
            residual = err[:, columns].ravel()
            rho = np.sqrt(np.sum(residual**2)/len(ix)+.01**2)
            loss += trial_weight*gain*2*rho
            if normal:
                jac = (result[3][ix, columns, :]*10).reshape(-1, 34)
                w = trial_weight*gain/(len(ix)*rho)
                cov += w*jac.T@jac
                rhs -= w*jac.T@residual
    return (float(loss), cov, rhs) if normal else float(loss)


def fit(es, lam, prior):
    weights = prior.copy()
    history = []
    for iteration in range(12):
        old, cov, rhs = objective(es, weights, lam, prior, True)
        step = np.linalg.solve(cov, rhs).reshape(2, 17).T
        chosen, value = 0., old
        for gain in (1., .5, .25, .125):
            candidate = objective(es, weights+gain*step, lam, prior)
            if candidate < old:
                chosen, value = gain, candidate
                break
        weights += chosen*step
        history.append(dict(iteration=iteration, objective=value, step=chosen))
        if not chosen:
            break
    assert np.isfinite(weights).all()
    return dict(weights=weights.tolist(), history=history)


def ratio(value, baseline):
    return value/baseline if baseline else (1. if value == 0 else float('inf'))


def check_stop():
    if (p.ROOT/'research_state/STOP').exists():
        raise RuntimeError('STOP')


def sealed(folder, name, inputs):
    result = verified_json(folder, name)
    for path in (folder/name, folder/'artifact_manifest.json'):
        inputs[str(path.relative_to(p.ROOT))] = p.digest(path)
    return result


def load_train(inputs):
    parent = p.ROOT/'outputs_reservoir_path_v121'
    protocol = sealed(parent, 'protocol.json', inputs)
    ids = protocol['training_ids']
    assert len(ids) == len(set(ids)) == 207
    prep = p.ROOT/'outputs_motion_endpoint_v16'
    pm = json.loads((prep/'artifact_manifest.json').read_text())['sha256']
    prepared = sealed(prep, 'run.json', inputs)
    provenance = {k.replace(chr(92), '/'): v for k, v in prepared['provenance'].items()}
    cal_path = p.ROOT/'outputs_amended_v2/calibration.json'
    assert p.digest(cal_path) == provenance['outputs_amended_v2/calibration.json']
    inputs[str(cal_path.relative_to(p.ROOT))] = p.digest(cal_path)
    calibration = json.loads(cal_path.read_text())
    cfg = sealed(p.ROOT/'outputs_observed_reference_v7', 'run.json', inputs)['settings']
    entries = []
    for ident in ids:
        path = prep/'prepared_training'/(ident+'.npz')
        meta = path.with_suffix('.json')
        for f in (path, meta):
            sha = p.digest(f)
            assert sha == pm[str(f.relative_to(prep))]
            inputs[str(f.relative_to(p.ROOT))] = sha
        info = json.loads(meta.read_text())
        row = info['row']
        assert row['id'] == ident and row['partition'] == 'train'
        assert row['participant'] in set.union(*FOLDS)
        with np.load(path) as z:
            d = {k: z[k] for k in z.files}
        x, motion = d.pop('features'), d.pop('ridge_motion')
        d.pop('residual_target')
        d.pop('residual_label_valid')
        e = dict(row=row, data=d, motion=motion, linear=x,
                 nonlinear=nonlinear_features(x), setup=row['setup'],
                 initialization=info['initialization'])
        e['extra'] = dynamic_features(d, motion, calibration[row['setup']],
                                      info['initialization'], .3)
        entries.append(e)
    assert len({e['row']['participant'] for e in entries}) == 12
    assert sum(e['row']['participant'] == 'No.20' for e in entries) == 15
    return entries, cfg


def prepare(entries, original, tilt, normalization):
    aa = adapted(entries, 'physical_products', original['feature_clip'])
    bb = expanded(entries, tilt['feature_clip'], tilt['extra_clip'])
    es = []
    for e, a, b in zip(entries, aa, bb):
        base = .25*corrected_entry(a, original['fits'])+.75*corrected_entry(b, tilt['fits'])
        d = e['data']
        xy, h = integrate(d, base)
        ix = np.flatnonzero(d['gt_valid'] & np.isfinite(xy).all(1) &
                            np.isfinite(h) & np.isfinite(d['gt_heading']))[::10]
        assert len(ix)
        es.append(dict(e, base=base, ix=ix,
                       z=reservoir(e['linear'][:, 30:45], d['imu_valid'],
                                   normalization[e['setup']])))
    return es


def prepare_fold(entries, fold, inputs):
    held = FOLDS[fold]
    q = sealed(p.ROOT/'outputs_dynamic_blend_v34', f'fold_{fold}_models.json', inputs)
    v121 = sealed(p.ROOT/'outputs_reservoir_path_v121', f'fold_{fold}_models.json', inputs)
    fitting_ids = {e['row']['id'] for e in entries if e['row']['participant'] not in held}
    held_ids = {e['row']['id'] for e in entries if e['row']['participant'] in held}
    assert set(v121['fitting_ids']) == fitting_ids
    assert not held_ids & set(q['fit_ids'])
    assert v121['held_people'] == q['held_people'] == sorted(held)
    original = dict(feature_clip=q['feature_clip'], fits=q['original'])
    tilt = dict(feature_clip=q['feature_clip'], extra_clip=q['extra_clip'], fits=q['tilt'])
    es = prepare(entries, original, tilt, v121['normalization'])
    prior = {setup: np.array(model['weights']) for setup, model in v121['models']['10.0'].items()}
    return es, prior, v121['normalization']


def guards(rows, control):
    _, people, maneuvers = p.summarize(rows)
    _, base_people, base_maneuvers = p.summarize(control)
    bp = {r['participant']: r['mean_trial_position_rmse_m'] for r in base_people}
    bm = {r['condition']: r['equal_participant_mean_position_rmse_m'] for r in base_maneuvers}
    return dict(participant_ratios={r['participant']: ratio(r['mean_trial_position_rmse_m'], bp[r['participant']]) for r in people},
                maneuver_ratios={r['condition']: ratio(r['equal_participant_mean_position_rmse_m'], bm[r['condition']]) for r in maneuvers},
                metric_ratios={k: ratio(balanced(rows, k), balanced(control, k)) for k in GUARDS})


def main():
    started = time.perf_counter()
    torch.set_num_threads(4)
    check_stop()
    OUT.mkdir(exist_ok=False)
    (OUT/'predictions').mkdir()
    inputs = {}
    entries, cfg = load_train(inputs)
    parent = p.ROOT/'outputs_reservoir_path_v121'
    manifest = json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    for name in ('trials.csv',):
        assert p.digest(parent/name) == manifest[name]
        inputs[str((parent/name).relative_to(p.ROOT))] = p.digest(parent/name)
    with (parent/'trials.csv').open(newline='') as f:
        old = {(r['id'], float(r['penalty'])): r for r in csv.DictReader(f)}
    source_names = list(sealed(parent, 'protocol.json', inputs)['source_hashes'])
    source_names += ['trial_rmse_v124.py', 'test_trial_rmse_v124.py', 'research_docs/trial_rmse_v124.md']
    sources = {name: p.digest(p.ROOT/name) for name in source_names}
    p.save_json(OUT/'protocol.json', dict(penalties=PENALTIES, sources=sources,
                training_ids=[e['row']['id'] for e in entries],
                validation_accessed=False, test_accessed=False))
    folds, checks = [], []
    for fold, held in enumerate(FOLDS):
        es, prior, normalization = prepare_fold(entries, fold, inputs)
        folds.append((es, prior, normalization))
        for e in es:
            if e['row']['participant'] not in held:
                continue
            ident, d = e['row']['id'], e['data']
            saved = parent/'predictions'/(ident+'.npz')
            assert p.digest(saved) == manifest[str(saved.relative_to(parent))]
            inputs[str(saved.relative_to(p.ROOT))] = p.digest(saved)
            with np.load(saved) as z:
                for name in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid'):
                    assert np.array_equal(d[name], z[name], equal_nan=True)
                for penalty, weights in ((0, np.zeros((17, 2))), (10, prior[e['setup']])):
                    motion, xy, h = prediction(e, weights)
                    for key, value in (('motion', motion), ('xy', xy), ('heading', h)):
                        np.testing.assert_allclose(value, z[f'lambda_{penalty}_{key}'], rtol=1e-10, atol=1e-12)
                    score = p.metrics(d, xy, h, cfg)
                    previous = old[(ident, float(penalty))]
                    assert score['scored_frames'] == int(previous['scored_frames'])
                    for key in ('position_rmse_m', 'heading_rmse_deg'):
                        assert np.isclose(score[key], float(previous[key]), rtol=1e-10, atol=1e-12)
                    checks.append(dict(id=ident, control=f'v{34 if penalty == 0 else 121}', **score))
    assert len(checks) == 414
    p.save_json(OUT/'baseline_reproduction.json', checks)
    p.save_json(OUT/'inputs.json', inputs)
    print('All207 v34 and v121 motions/trajectories/support/primary metrics reproduced', flush=True)
    records = []
    for fold, (es, prior, normalization) in enumerate(folds):
        check_stop()
        held = FOLDS[fold]
        fitting = [e for e in es if e['row']['participant'] not in held]
        models = {}
        for lam in PENALTIES:
            check_stop()
            models[str(lam)] = {setup: fit([e for e in fitting if e['setup'] == setup], lam, prior[setup]) for setup in prior}
            print('Fitted fold', fold, 'penalty', lam, flush=True)
        p.save_json(OUT/f'fold_{fold}_models.json', dict(models=models, normalization=normalization,
                    fitting_ids=[e['row']['id'] for e in fitting], held_people=sorted(held)))
        for e in es:
            row, d = e['row'], e['data']
            if row['participant'] not in held:
                continue
            arrays = {k: d[k] for k in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid')}
            support = None
            candidates = [('v34', np.zeros((17, 2))), ('v121', prior[e['setup']])]
            candidates += [(f'lambda_{lam:g}', np.array(models[str(lam)][e['setup']]['weights'])) for lam in PENALTIES]
            for name, weights in candidates:
                motion, xy, h = prediction(e, weights)
                mask = d['gt_valid'] & np.isfinite(xy).all(1)
                if support is None:
                    support = mask
                assert np.array_equal(mask, support) and np.isfinite(h[mask]).all()
                assert np.isfinite(motion[d['imu_valid']]).all()
                records.append(dict(id=row['id'], participant=row['participant'], condition=row['condition'],
                                    fold=fold, candidate=name, **p.metrics(d, xy, h, cfg), **metrics(d, xy, h, motion)))
                arrays.update({name+'_motion': motion, name+'_xy': xy, name+'_heading': h})
            np.savez_compressed(OUT/'predictions'/(row['id']+'.npz'), **arrays)
        p.write_csv(OUT/'trials.csv', records)
        p.save_json(OUT/'checkpoint.json', dict(completed_folds=fold+1, rows=len(records), status='running'))
        print('Completed fold', fold, flush=True)
    controls = {name: [r for r in records if r['candidate'] == name] for name in ('v34', 'v121')}
    baseline_score = p.summarize(controls['v121'])[0]['equal_participant_mean_position_rmse_m']
    assert np.isclose(baseline_score, .12973981099429271, rtol=1e-10, atol=1e-12)
    choices = []
    for name in ('v121', *(f'lambda_{lam:g}' for lam in PENALTIES)):
        rr = [r for r in records if r['candidate'] == name]
        assert len(rr) == len({r['id'] for r in rr}) == 207
        summary, people, maneuvers = p.summarize(rr)
        guard = {control: guards(rr, rows) for control, rows in controls.items()}
        passed = all(value <= 1.05 for g in guard.values() for ratios in g.values() for value in ratios.values())
        eligible = name == 'v121' or (passed and summary['equal_participant_mean_position_rmse_m'] < baseline_score)
        choices.append(dict(candidate=name, eligible=eligible, **summary, guards=guard))
        p.write_csv(OUT/f'{name}_participants.csv', people)
        p.write_csv(OUT/f'{name}_maneuvers.csv', maneuvers)
    selected = min((c for c in choices if c['eligible']), key=lambda c: c['equal_participant_mean_position_rmse_m'])
    p.save_json(OUT/'run.json', dict(candidates=choices, selected=selected, validation_accessed=False,
                test_accessed=False, runtime_s=time.perf_counter()-started))
    p.save_json(OUT/'inputs.json', inputs)
    p.save_json(OUT/'checkpoint.json', dict(completed_folds=3, rows=len(records), status='complete'))
    assert all(p.digest(p.ROOT/name) == sha for name, sha in {**inputs, **sources}.items())
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={str(f.relative_to(OUT)): p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps([dict(candidate=c['candidate'], eligible=c['eligible'], ATE_mm=1000*c['equal_participant_mean_position_rmse_m']) for c in choices]), flush=True)


if __name__ == '__main__':
    main()
