"""TRAIN-only oracle component replacement; no fitting, selection or resets."""
import itertools, json, time
import numpy as np
import pipeline as p
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from projected_yaw_folds_v52 import proxy
from trajectory_calibration_v10 import integrate
from planar_experiment import lateral_labels
from research_metrics_v59 import trajectory_metrics, aggregate
from audit_fold_routes_v59 import verified_json

OUT = p.ROOT / 'outputs_train_error_budget_v63'
AXES = {'speed': 0, 'lateral': 1, 'yaw': 2}


def name(subset):
    return '+'.join(subset) if subset else 'predicted'


def main():
    started = time.perf_counter()
    OUT.mkdir(exist_ok=False)
    clock = json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())
    inv = {r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    folds = verified_json(p.ROOT/'outputs_braking_hysteresis_v56', 'fold_models.json')
    manifests = {s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD, NEW)}
    subsets = [q for n in range(4) for q in itertools.combinations(AXES, n)]
    p.save_json(OUT/'protocol.json', dict(diagnostic_only=True, estimator=False, model_selection=False,
        data='207 identified TRAIN held-fold records; v52 projected-yaw + fold-refitted physics speed control',
        replacement='Observed derivative components only on common label-valid/finite support, predicted fallback everywhere else',
        integration='Original initialization once, no C3D resets, pose fitting, changes to clocks or geometry',
        lateral='Existing lateral_labels optical derivative proxy; cannot establish physical tire slip',
        components=list(AXES), subsets=[name(s) for s in subsets],
        validation_accessed=False, test_accessed=False))
    rows, budgets = [], []
    for fold, q in folds.items():
        yaw = verified_json(p.ROOT/'outputs_projected_yaw_v52', f'fold_{fold}_models.json')
        assert yaw['calibration'] == q['calibration']
        assert set(yaw['fitting_ids']) == set(q['fit_ids'])
        for ident in q['held_ids']:
            r = inv[ident]; assert r['partition'] == 'train'
            source = OLD if ident in clock['fallback_old_clock_ids'] else NEW
            d, _ = load_cache(source, ident, manifests[source])
            cal = q['calibration'][r['setup']]
            v = p.velocities(d, cal)
            ym = yaw['yaw'][r['setup']]
            m = np.c_[v[:, 0], np.zeros(len(v)), proxy(d, cal)*ym['scale']+ym['intercept']]
            side, side_valid = lateral_labels(d)
            label = d['label_valid'] & d['imu_valid'] & side_valid
            truth = np.c_[d['gt_v'], side, d['gt_yaw']]
            label &= np.isfinite(truth).all(axis=1)
            scores = {}
            for subset in subsets:
                cm = m.copy()
                for key in subset:
                    cm[label, AXES[key]] = truth[label, AXES[key]]
                xy, heading = integrate(d, cm)
                metric = trajectory_metrics(d, xy, heading)
                scores[subset] = metric['position_rmse_m'] ** 2
                rows.append(dict(id=ident, participant=r['participant'], condition=r['condition'],
                    fold=fold, method=name(subset), label_fraction=float(label.mean()),
                    scorable_label_fraction=float(label[d['gt_valid']].mean()), **metric))
            credit = {}
            for key in AXES:
                others = [a for a in AXES if a != key]
                value = 0.
                for n in range(3):
                    for subset in itertools.combinations(others, n):
                        old = tuple(a for a in AXES if a in subset)
                        new = tuple(a for a in AXES if a in subset or a == key)
                        weight = (1/3) if n in (0, 2) else (1/6)
                        value += weight * (scores[old] - scores[new])
                credit[key] = value
            reduction = scores[()] - scores[tuple(AXES)]
            assert abs(sum(credit.values()) - reduction) < 1e-10
            budgets.append(dict(id=ident, participant=r['participant'], condition=r['condition'],
                fold=fold, label_fraction=float(label.mean()), baseline_mse_m2=scores[()],
                all_truth_mse_m2=scores[tuple(AXES)], total_mse_reduction_m2=reduction,
                single_reduction_sum_m2=sum(scores[()]-scores[(a,)] for a in AXES),
                nonadditivity_m2=reduction-sum(scores[()]-scores[(a,)] for a in AXES),
                **{key+'_shapley_mse_reduction_m2':value for key,value in credit.items()}))
            print(fold, ident, flush=True)
    assert len(budgets) == 207
    summary = aggregate(rows, ('method',))
    assert abs(next(r['position_rmse_m'] for r in summary if r['method']=='predicted') - .14774650809690637) < 1e-10
    p.write_csv(OUT/'trials.csv', rows); p.write_csv(OUT/'budgets.csv', budgets)
    for keys, filename in [(('method',), 'summary'), (('method','participant'),'participants'),
                           (('method','condition'),'maneuvers')]:
        p.write_csv(OUT/(filename+'.csv'), aggregate(rows, keys))
    fields = ('label_fraction','baseline_mse_m2','all_truth_mse_m2','total_mse_reduction_m2',
              'nonadditivity_m2','speed_shapley_mse_reduction_m2','lateral_shapley_mse_reduction_m2','yaw_shapley_mse_reduction_m2')
    def budget_mean(subset):
        people = sorted({r['participant'] for r in subset})
        return {field:float(np.mean([np.mean([r[field] for r in subset if r['participant']==person]) for person in people])) for field in fields}
    p.save_json(OUT/'run.json', dict(summary=summary, budget=budget_mean(budgets),
        maneuver_budget={c:budget_mean([r for r in budgets if r['condition']==c]) for c in sorted({r['condition'] for r in budgets})},
        diagnostic_only=True, selection=False, validation_accessed=False, test_accessed=False,
        caveat='Oracle replacement on common finite derivative support only; gap/boundary fallback and derivative filtering leave all-truth residual. Shapley is MSE reduction conditional on frozen clocks/initial pose, not physical causal attribution.',
        runtime_s=time.perf_counter()-started))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))


if __name__ == '__main__':
    main()
