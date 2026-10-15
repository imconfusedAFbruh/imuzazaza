"""TRAIN-only fold preprocessing contract and geometry-support audit."""
import json
import numpy as np
import pipeline as p
from participant_folds_experiment_v24 import FOLDS
from observed_reference_experiment import observed_markers
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_strict_preprocessing_v70'


def assert_disjoint(fit,held):
    assert not set(fit)&set(held), 'Held ID entered fitting'


def main():
    try: assert_disjoint(['a'],['a'])
    except AssertionError: pass
    else: raise AssertionError('Overlap check failed')
    OUT.mkdir(exist_ok=False)
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    people=set.union(*FOLDS)
    ids=[i for i in protocol['training_ids'] if inv[i]['participant'] in people]
    assert len(ids)==207 and all(inv[i]['partition']=='train' for i in ids)
    manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    geometry_ids={r['id'] for r in protocol['old_clock_settings']['reference_geometry']['audit']}
    bootstrap=verified_json(NEW,'bootstrap_calibration.json')
    bootstrap_ids=set.union(*[set(c['training_trials']) for c in bootstrap.values()])
    p.save_json(OUT/'protocol.json',dict(family='2 complete preprocessing refit',configuration='Training-only geometry and sync bootstrap, original fixed algorithms, no tuning',
        training_ids=ids,folds=[sorted(f) for f in FOLDS],reserved_test_accessed=False,validation_accessed=False,
        historical_support='Inherited reference/clock track retained unchanged',strict_support='Fold-fitted geometry; changes reported, cannot directly claim lower RMSE than historical mask',
        no_unknown_identity_pretraining=True,accepted_ids_frozen=True,no_candidate_selection=True))
    raw_markers={}; observed={}; caches={}
    for i in ids:
        r=inv[i]; path=p.ROOT/r['c3d']
        raw_markers[str(path)]=p.read_markers(path)
        observed[i]=observed_markers(path)
        src=OLD if i in protocol['fallback_old_clock_ids'] else NEW
        caches[i]=load_cache(src,i,manifests[src])[0]
    rows=[]; folds={}
    original=p.read_markers
    for fold,held_people in enumerate(FOLDS):
        fit=[i for i in ids if inv[i]['participant'] not in held_people]
        held=[i for i in ids if inv[i]['participant'] in held_people]; assert_disjoint(fit,held)
        try:
            p.read_markers=lambda path:raw_markers[str(path)]
            geometry=p.fit_geometry_policy([inv[i] for i in fit],p.ROOT)
        finally: p.read_markers=original
        assert set(r['id'] for r in geometry['audit']) <= set(fit)
        cfg=dict(protocol['old_clock_settings'],reference_geometry=geometry)
        calibration=p.calibrate([(inv[i],caches[i],{}) for i in fit],cfg)
        assert all(set(c['training_trials'])<=set(fit) for c in calibration.values())
        # Bootstrap is isolated by fit IDs, but its seed labels still inherit old clocks.
        # This dependency is explicitly not certified as a completely nested clock fit.
        record=dict(fit_ids=fit,held_ids=held,geometry=geometry,provisional_sync_calibration=calibration,
            inherited_geometry_held_id_overlap=len(set(held)&geometry_ids),inherited_sync_bootstrap_held_id_overlap=len(set(held)&bootstrap_ids),
            calibration_fit_id_overlap=0,seed_label_clock_provenance='Inherited frozen caches; unresolved bootstrapping dependency',strict_clock_certified=False)
        folds[str(fold)]=record
        for i in held:
            r=inv[i]; points,valid,hz=observed[i]; sep=np.linalg.norm(points[:,0]-points[:,1],axis=1)
            policy=geometry['setups'][r['setup']]; oldpolicy=protocol['old_clock_settings']['reference_geometry']['setups'][r['setup']]
            median=float(np.median(sep[valid])) if valid.any() else 0.
            def mask(q):
                bands=np.zeros(len(valid),bool)
                for b in q['bands']: bands|=(sep>=b['lower_m'])&(sep<=b['upper_m'])
                return valid & bands & (np.abs(sep-median)<=q['rigidity_tolerance_m'])
            a,b=mask(oldpolicy),mask(policy)
            rows.append(dict(id=i,participant=r['participant'],condition=r['condition'],fold=fold,
                old_observed_frames=int(a.sum()),fold_observed_frames=int(b.sum()),lost_frames=int((a&~b).sum()),gained_frames=int((b&~a).sum()),
                completely_lost=bool(a.any() and not b.any()),native_frames=len(valid),reference_hz=hz))
    assert len(rows)==207
    p.save_json(OUT/'folds.json',folds); p.write_csv(OUT/'support.csv',rows)
    summary=dict(trials=207,folds=3,held_overlap_in_inherited_geometry={k:v['inherited_geometry_held_id_overlap'] for k,v in folds.items()},
        held_overlap_in_inherited_sync={k:v['inherited_sync_bootstrap_held_id_overlap'] for k,v in folds.items()},
        lost_observed_frames=sum(r['lost_frames'] for r in rows),gained_observed_frames=sum(r['gained_frames'] for r in rows),
        fully_lost_trials=sum(r['completely_lost'] for r in rows),changed_trials=sum(bool(r['lost_frames'] or r['gained_frames']) for r in rows),
        strictly_nested_clock=False,no_prediction_accuracy_claim=True,validation_accessed=False,test_accessed=False)
    p.save_json(OUT/'run.json',summary)
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
