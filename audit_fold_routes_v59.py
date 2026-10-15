"""Reconstruct saved TRAIN held-fold v52/v56 predictions without fitting."""
import json, time
import numpy as np
import pipeline as p
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from trajectory_calibration_v10 import integrate
from projected_yaw_folds_v52 import proxy
from braking_hysteresis_folds_v56 import prepare_entry, corrected_motion
from research_metrics_v59 import trajectory_metrics, aggregate, METRICS

OUT = p.ROOT / 'outputs_fold_route_audit_v59'


def verified_json(folder, name):
    manifest = json.loads((folder / 'artifact_manifest.json').read_text())['sha256']
    path = folder / name
    if p.digest(path) != manifest[name]:
        raise RuntimeError('Changed sealed artifact: ' + str(path))
    return json.loads(path.read_text())


def main():
    started = time.perf_counter()
    if OUT.exists():
        raise RuntimeError('Preserve completed audit')
    OUT.mkdir()
    protocol = json.loads((p.ROOT / 'outputs_clock_arbitrated_v42/protocol.json').read_text())
    inventory = {r['id']: r for r in json.loads((p.ROOT / 'outputs_amended_v2/inventory.json').read_text())}
    frozen = verified_json(p.ROOT / 'outputs_braking_hysteresis_v56', 'fold_models.json')
    manifests = {s: json.loads((s / 'artifact_manifest.json').read_text()) for s in (OLD, NEW)}
    rows = []
    for fold, model in frozen.items():
        yaw = verified_json(p.ROOT / 'outputs_projected_yaw_v52', f'fold_{fold}_models.json')
        if model['calibration'] != yaw['calibration']:
            raise RuntimeError('v52/v56 calibration differs')
        if set(model['fit_ids']) != set(yaw['fitting_ids']):
            raise RuntimeError('v52/v56 fitting IDs differ')
        if set(model['fit_ids']) & set(model['held_ids']):
            raise RuntimeError('Fold overlap')
        for trial_id in model['held_ids']:
            r = inventory[trial_id]
            assert r['partition'] == 'train'
            src = OLD if trial_id in protocol['fallback_old_clock_ids'] else NEW
            d, _ = load_cache(src, trial_id, manifests[src])
            cal = model['calibration'][r['setup']]
            e = prepare_entry(r, d, cal)
            m = e['motion'].copy()
            ym = yaw['yaw'][r['setup']]
            projected = m.copy()
            projected[:, 2] = proxy(d, cal) * ym['scale'] + ym['intercept']
            for name, motion in [('physics', m), ('v52_projected_yaw', projected),
                                 ('v56_braking_gain025', corrected_motion(e, model['models'], .25))]:
                xy, h = integrate(d, motion)
                rows.append(dict(id=trial_id, participant=r['participant'], condition=r['condition'],
                                 fold=fold, model=name, **trajectory_metrics(d, xy, h)))
            print(fold, trial_id, flush=True)
    for keys, name in [(('model',), 'summary'), (('model', 'participant'), 'participants'),
                       (('model', 'condition'), 'maneuvers')]:
        p.write_csv(OUT / (name + '.csv'), aggregate(rows, keys))
    p.write_csv(OUT / 'trials.csv', rows)
    results = {}
    for name in ('v52_projected_yaw', 'v56_braking_gain025'):
        results[name] = {}
        for group in ('participant', 'condition'):
            base = {r[group]: r for r in aggregate([r for r in rows if r['model'] == 'physics'], (group,))}
            candidate = aggregate([r for r in rows if r['model'] == name], (group,))
            results[name][group] = {metric: max(
                ((r[metric] / max(base[r[group]][metric], 1e-12), r[group]) for r in candidate))
                for metric in METRICS}
    p.save_json(OUT / 'run.json', dict(summary=aggregate(rows, ('model',)), worst_ratios=results,
        runtime_s=time.perf_counter()-started, validation_accessed=False, test_accessed=False,
        fitting='None: uses sealed per-fold v52 and v56 coefficients, exact calibration and fit membership equality verified',
        reference='Shared original gt_valid support; last supported endpoint may precede recording end; disconnected gaps never bridged',
        route='10mm arc queries to exact supported polyline; directions weighted equally; P95 weighted bidirectional; Hausdorff is sampled query maximum',
        frechet='25mm-spatially-resampled discrete Frechet maximum across temporally corresponding supported runs; partial-route metric',
        selection='No new selection: supplements existing selected v52 weight1 and v56 gain.25; conditional inherited clock/QC/geometry'))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={str(q.relative_to(OUT)):p.digest(q) for q in OUT.rglob('*') if q.is_file()}))


if __name__ == '__main__':
    main()
