"""Separate frozen evaluator references from train-fitted geometry applicability."""
import csv,json
import numpy as np
import pipeline as p
from basin_completeness_v91 import verify,DOC
from native_refit_v81 import OUT as FROZEN
from seedless_clock_v83 import OUT as REFERENCES

OUT=p.ROOT/'outputs_geometry_roles_v92'
GEOMETRY=p.ROOT/'outputs_strict_preprocessing_v70'


def check(fit,held,fit_people,held_people,audit):
    assert not set(fit)&set(held)
    assert not set(fit_people)&set(held_people)
    assert set(audit)<=set(fit)


def main():
    check(['a'],['b'],['A'],['B'],['a'])
    try:check(['a'],['b'],['A'],['A'],['a'])
    except AssertionError:pass
    else:raise AssertionError('Participant overlap accepted')
    hashes=sum(verify(q) for q in (GEOMETRY,FROZEN,REFERENCES))
    folds=json.loads((GEOMETRY/'folds.json').read_text())
    support={r['id']:r for r in csv.DictReader((GEOMETRY/'support.csv').open())}
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    OUT.mkdir(exist_ok=False);rows=[];contract={}
    for fold,q in folds.items():
        fit=q['fit_ids'];held=q['held_ids']
        check(fit,held,[inv[i]['participant'] for i in fit],[inv[i]['participant'] for i in held],[a['id'] for a in q['geometry']['audit']])
        contract[fold]=dict(fit_ids=fit,held_ids=held,training_geometry=q['geometry'],
            training_geometry_role='Training-side applicability only; never filters held scoring',
            evaluator_role='Inherited frozen reference instrument/QC; not a train-fitted policy',
            completely_nested=False)
        for ident in held:
            assert inv[ident]['partition']=='train'
            with np.load(REFERENCES/'references'/(ident+'.npz')) as z:a={k:z[k] for k in ('t','xy','heading','valid')}
            with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:b={k:z[k] for k in ('native_c3d_time_s','reference_xy_m','reference_heading_rad','reference_valid','imu_valid')}
            ix=np.searchsorted(a['t'],b['native_c3d_time_s']);assert (ix<len(a['t'])).all()
            for key,other in [('t','native_c3d_time_s'),('xy','reference_xy_m'),('heading','reference_heading_rad'),('valid','reference_valid')]:
                assert np.array_equal(a[key][ix],b[other],equal_nan=True),(ident,key)
            s=support[ident];assert str(fold)==s['fold']
            row=dict(id=ident,participant=inv[ident]['participant'],fold=fold,
                native_scoring_frames=int((b['reference_valid']&b['imu_valid']).sum()),
                hypothetical_geometry_lost_frames=int(s['lost_frames']),
                training_geometry_applicable=s['completely_lost']=='False',
                scoring_retained=True,reference_arrays_exact=True,initial_pose_exact=True,
                frozen_reference_sha256=p.digest(REFERENCES/'references'/(ident+'.npz')),
                frozen_trajectory_sha256=p.digest(FROZEN/'common_trajectories'/(ident+'.npz')))
            assert row['native_scoring_frames']>0
            rows.append(row)
    assert len(rows)==len({r['id'] for r in rows})==207
    no20=[r for r in rows if r['participant']=='No.20'];assert len(no20)==15
    assert all(r['scoring_retained'] for r in no20)
    p.save_json(OUT/'contract.json',dict(preregistration_sha256=p.digest(DOC),folds=contract,
        immutable_scoring='Reference arrays, accepted identities, support and initial pose bound by artifact hashes',
        outstanding='Inherited instrument geometry/QC/acceptance; unknown physical front and acquisition provenance; clocks199/207'))
    p.write_csv(OUT/'roles.csv',rows)
    p.save_json(OUT/'run.json',dict(trials=207,no20_retained=15,exact_reference_and_pose_checks=len(rows),parent_hashes_verified=hashes,
        scoring_frames=sum(r['native_scoring_frames'] for r in rows),
        hypothetical_geometry_loss=sum(r['hypothetical_geometry_lost_frames'] for r in rows),
        held_trials_outside_training_geometry=sum(not r['training_geometry_applicable'] for r in rows),
        geometry_role_separated=True,production_policy_changed=False,fully_nested=False,
        promotion=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
