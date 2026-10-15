"""TRAIN-only speed/yaw shrinkage; reuse frozen v124 features and loss."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OPENBLAS_NUM_THREADS'] = '4'
import csv
import json
import time
import numpy as np
import torch
import pipeline as p
import trial_rmse_v124 as previous
from reservoir_path_v121 import prediction
from participant_folds_experiment_v24 import FOLDS
from metric_contract_v74 import metrics

OUT = p.ROOT/'outputs_axis_prior_v125'
CONFIGS = {'speed1_yaw10': (1., 10.), 'speed10_yaw1': (10., 1.),
           'speed3_yaw3': (3., 3.)}
CONTROLS = ('v34', 'v121', 'v124')


def objective(es, weights, penalties, prior, normal=False):
    penalties = np.asarray(penalties, dtype=float)
    assert penalties.shape == (2,) and np.isfinite(penalties).all() and (penalties > 0).all()
    minimum = float(penalties.min())
    result = previous.objective(es, weights, minimum, prior, normal)
    extra = np.broadcast_to(penalties-minimum, weights.shape)
    delta = weights-prior
    loss = (result[0] if normal else result)+np.sum(extra*delta**2)
    if not normal:
        return float(loss)
    _, cov, rhs = result
    return float(loss), cov+np.diag(extra.T.ravel()), rhs-(extra*delta).T.ravel()


def fit(es, penalties, prior):
    weights = prior.copy()
    history = []
    for iteration in range(12):
        old, cov, rhs = objective(es, weights, penalties, prior, True)
        step = np.linalg.solve(cov, rhs).reshape(2, 17).T
        chosen, value = 0., old
        for gain in (1., .5, .25, .125):
            candidate = objective(es, weights+gain*step, penalties, prior)
            if candidate < old:
                chosen, value = gain, candidate
                break
        weights += chosen*step
        history.append(dict(iteration=iteration, objective=value, step=chosen))
        if not chosen:
            break
    assert np.isfinite(weights).all()
    return dict(weights=weights.tolist(), history=history)


def main():
    started = time.perf_counter()
    torch.set_num_threads(4)
    previous.check_stop()
    OUT.mkdir(exist_ok=False)
    (OUT/'predictions').mkdir()
    inputs = {}
    entries, cfg = previous.load_train(inputs)
    parent = p.ROOT/'outputs_trial_rmse_v124'
    prior_protocol = previous.sealed(parent, 'protocol.json', inputs)
    old_run = previous.sealed(parent, 'run.json', inputs)
    assert old_run['selected']['candidate'] == 'lambda_10'
    assert [e['row']['id'] for e in entries] == prior_protocol['training_ids']
    manifest = json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    assert p.digest(parent/'trials.csv') == manifest['trials.csv']
    inputs[str((parent/'trials.csv').relative_to(p.ROOT))] = p.digest(parent/'trials.csv')
    with (parent/'trials.csv').open(newline='') as stream:
        old = {(r['id'], r['candidate']): r for r in csv.DictReader(stream)}
    names = list(prior_protocol['sources']) + ['axis_prior_v125.py',
             'test_axis_prior_v125.py', 'research_docs/axis_prior_v125.md']
    sources = {name: p.digest(p.ROOT/name) for name in names}
    assert all(sources[name] == sha for name, sha in prior_protocol['sources'].items())
    p.save_json(OUT/'protocol.json', dict(configs=CONFIGS, sources=sources,
                training_ids=prior_protocol['training_ids'], controls=CONTROLS,
                validation_accessed=False, test_accessed=False))
    folds, checks = [], []
    for fold, held in enumerate(FOLDS):
        es, prior, normalization = previous.prepare_fold(entries, fold, inputs)
        saved_fit = previous.sealed(parent, f'fold_{fold}_models.json', inputs)
        assert saved_fit['normalization'] == normalization
        expected_ids = {e['row']['id'] for e in es if e['row']['participant'] not in held}
        assert set(saved_fit['fitting_ids']) == expected_ids
        best = {s: np.array(m['weights']) for s, m in saved_fit['models']['10.0'].items()}
        folds.append((es, prior, normalization, best))
        for e in es:
            if e['row']['participant'] not in held:
                continue
            ident, d = e['row']['id'], e['data']
            source = parent/'predictions'/(ident+'.npz')
            assert p.digest(source) == manifest[str(source.relative_to(parent))]
            inputs[str(source.relative_to(p.ROOT))] = p.digest(source)
            with np.load(source) as z:
                for key in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid'):
                    assert np.array_equal(d[key], z[key], equal_nan=True)
                for control, prefix, weights in (
                    ('v34', 'v34', np.zeros((17, 2))),
                    ('v121', 'v121', prior[e['setup']]),
                    ('v124', 'lambda_10', best[e['setup']])):
                    motion, xy, heading = prediction(e, weights)
                    for key, value in (('motion', motion), ('xy', xy), ('heading', heading)):
                        np.testing.assert_allclose(value, z[prefix+'_'+key], rtol=1e-10, atol=1e-12)
                    score = p.metrics(d, xy, heading, cfg)
                    baseline = old[(ident, prefix)]
                    assert score['scored_frames'] == int(baseline['scored_frames'])
                    for key in ('position_rmse_m', 'heading_rmse_deg'):
                        assert np.isclose(score[key], float(baseline[key]), rtol=1e-10, atol=1e-12)
                    checks.append(dict(id=ident, control=control, **score))
    assert len(checks) == 621
    p.save_json(OUT/'baseline_reproduction.json', checks)
    p.save_json(OUT/'inputs.json', inputs)
    print('All207 v34/v121/v124 controls reproduced before candidate fitting', flush=True)
    records = []
    for fold, (es, prior, normalization, best) in enumerate(folds):
        previous.check_stop()
        held = FOLDS[fold]
        fitting = [e for e in es if e['row']['participant'] not in held]
        models = {}
        for name, penalties in CONFIGS.items():
            previous.check_stop()
            models[name] = {setup: fit([e for e in fitting if e['setup'] == setup], penalties,
                                      prior[setup]) for setup in prior}
            print('Fitted fold', fold, name, flush=True)
        p.save_json(OUT/f'fold_{fold}_models.json', dict(models=models, normalization=normalization,
                    fitting_ids=[e['row']['id'] for e in fitting], held_people=sorted(held)))
        for e in es:
            row, d = e['row'], e['data']
            if row['participant'] not in held:
                continue
            arrays = {k: d[k] for k in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid')}
            support = None
            candidates = [('v34', np.zeros((17, 2))), ('v121', prior[e['setup']]),
                          ('v124', best[e['setup']])]
            candidates += [(name, np.array(model[e['setup']]['weights'])) for name, model in models.items()]
            for name, weights in candidates:
                motion, xy, heading = prediction(e, weights)
                mask = d['gt_valid'] & np.isfinite(xy).all(1)
                if support is None:
                    support = mask
                assert np.array_equal(mask, support) and np.isfinite(heading[mask]).all()
                assert np.isfinite(motion[d['imu_valid']]).all()
                records.append(dict(id=row['id'], participant=row['participant'], condition=row['condition'],
                    fold=fold, candidate=name, **p.metrics(d, xy, heading, cfg),
                    **metrics(d, xy, heading, motion)))
                arrays.update({name+'_motion': motion, name+'_xy': xy, name+'_heading': heading})
            np.savez_compressed(OUT/'predictions'/(row['id']+'.npz'), **arrays)
        p.write_csv(OUT/'trials.csv', records)
        p.save_json(OUT/'checkpoint.json', dict(completed_folds=fold+1, rows=len(records), status='running'))
        print('Completed fold', fold, flush=True)
    controls = {name: [r for r in records if r['candidate'] == name] for name in CONTROLS}
    baseline_score = p.summarize(controls['v124'])[0]['equal_participant_mean_position_rmse_m']
    assert np.isclose(baseline_score, .12887285434811182, rtol=1e-10, atol=1e-12)
    choices = []
    for name in ('v124', *CONFIGS):
        rr = [r for r in records if r['candidate'] == name]
        assert len(rr) == len({r['id'] for r in rr}) == 207
        assert sum(int(r['scored_frames']) for r in rr) == 314498
        summary, people, maneuvers = p.summarize(rr)
        guards = {control: previous.guards(rr, rows) for control, rows in controls.items()}
        passed = all(value <= 1.05 for g in guards.values() for ratios in g.values() for value in ratios.values())
        eligible = name == 'v124' or (passed and summary['equal_participant_mean_position_rmse_m'] < baseline_score)
        choices.append(dict(candidate=name, eligible=eligible, **summary, guards=guards))
        p.write_csv(OUT/f'{name}_participants.csv', people)
        p.write_csv(OUT/f'{name}_maneuvers.csv', maneuvers)
    selected = min((c for c in choices if c['eligible']), key=lambda c: c['equal_participant_mean_position_rmse_m'])
    p.save_json(OUT/'run.json', dict(candidates=choices, selected=selected,
                validation_accessed=False, test_accessed=False, runtime_s=time.perf_counter()-started))
    p.save_json(OUT/'inputs.json', inputs)
    p.save_json(OUT/'checkpoint.json', dict(completed_folds=3, rows=len(records), status='complete'))
    assert all(p.digest(p.ROOT/name) == sha for name, sha in {**inputs, **sources}.items())
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={str(f.relative_to(OUT)): p.digest(f)
                for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps([dict(candidate=c['candidate'], eligible=c['eligible'],
                     ATE_mm=1000*c['equal_participant_mean_position_rmse_m']) for c in choices]), flush=True)


if __name__ == '__main__':
    main()
