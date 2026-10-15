"""Resume saved full-TRAIN coefficients and verify the callable model; no refit."""
import json
import numpy as np
import pipeline as p
from reservoir_path_v121 import reservoir,fit,prediction,CAP
from nonlinear_endpoint_experiment_v21 import nonlinear_features,adapted
from dynamic_tilt_experiment_v33 import dynamic_features,expanded
from dynamic_tilt_blend_v34 import corrected_entry
from combined_physics_folds_v58 import verified_json
from trajectory_calibration_v10 import integrate

OUT=p.ROOT/'models/reservoir_path_v121_completed'


def main():
    if (p.ROOT/'research_state/STOP').exists():raise RuntimeError('STOP')
    run=verified_json(p.ROOT/'outputs_reservoir_path_v121','run.json');lam=run['selected']['penalty']
    assert lam==10 and run['selected']['eligible']
    protocol=verified_json(p.ROOT/'outputs_reservoir_path_v121','protocol.json')
    original=verified_json(p.ROOT/'outputs_nonlinear_endpoint_v21','model.json')
    tilt=verified_json(p.ROOT/'outputs_dynamic_tilt_v33','tilt_0.3_model.json')
    prep=p.ROOT/'outputs_motion_endpoint_v16';pm=json.loads((prep/'artifact_manifest.json').read_text())['sha256']
    cal=json.loads((p.ROOT/'outputs_amended_v2/calibration.json').read_text());entries=[]
    prov=verified_json(prep,'run.json')['provenance'];expected={k.replace(chr(92),'/'):v for k,v in prov.items()}
    assert p.digest(p.ROOT/'outputs_amended_v2/calibration.json')==expected['outputs_amended_v2/calibration.json']
    saved=verified_json(p.ROOT/'models/reservoir_path_v121','model.json')
    assert saved['training_ids']==protocol['training_ids'] and saved['penalty']==lam
    OUT.mkdir(parents=True,exist_ok=False)
    for ident in protocol['training_ids']:
        path=prep/'prepared_training'/(ident+'.npz');meta=path.with_suffix('.json')
        for f in (path,meta):assert p.digest(f)==pm[str(f.relative_to(prep))]
        info=json.loads(meta.read_text());assert info['row']['partition']=='train'
        with np.load(path) as z:d={k:z[k] for k in z.files}
        x=d.pop('features');m=d.pop('ridge_motion');d.pop('residual_target');d.pop('residual_label_valid')
        e=dict(row=info['row'],data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=info['row']['setup'],initialization=info['initialization'])
        e['extra']=dynamic_features(d,m,cal[e['setup']],info['initialization'],.3);entries.append(e)
    aa=adapted(entries,'physical_products',original['feature_clip']);bb=expanded(entries,tilt['feature_clip'],tilt['extra_clip'])
    normalization=saved['normalization']
    for e,a,b in zip(entries,aa,bb):
        e['base']=.25*corrected_entry(a,original['fits'])+.75*corrected_entry(b,tilt['fits'])
        d=e['data'];xy,h=integrate(d,e['base']);mask=d['gt_valid']&np.isfinite(xy).all(1)&np.isfinite(h)&np.isfinite(d['gt_heading'])
        e['ix']=np.flatnonzero(mask)[::10];assert len(e['ix'])
        e['z']=reservoir(e['linear'][:,30:45],d['imu_valid'],normalization[e['setup']])
    fits=saved['fits']
    sources=['legacy_inference_compat_v121.py','test_legacy_inference_compat_v121.py','models/reservoir_path_v121/model.json','reservoir_inference_v121.py','reservoir_path_v121.py','dynamic_blend_inference_v34.py',
        'observed_ridge_inference.py','stationary_gravity_experiment_v14.py','stationary_gravity_inference_v14.py',
        'pipeline.py','finalize_reservoir_v121.py','outputs_amended_v2/calibration.json',
        'outputs_dynamic_blend_v34/artifact_manifest.json','outputs_nonlinear_endpoint_v21/artifact_manifest.json',
        'outputs_dynamic_tilt_v33/artifact_manifest.json']
    p.save_json(OUT/'model.json',dict(penalty=lam,fits=fits,normalization=normalization,training_ids=protocol['training_ids'],
        baseline='frozen full-TRAIN v34 .75',selected_fold_result=run['selected'],
        dependencies={s:p.digest(p.ROOT/s) for s in sources},validation_evaluated=False,test_evaluated=False))
    # Temporary seal lets the public loader verify the completed coefficient file.
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={'model.json':p.digest(OUT/'model.json')}))
    from reservoir_inference_v121 import load_reservoir_model
    predict=load_reservoir_model();maximum=0;checks=[]
    for e in entries:
        sensor={k:e['data'][k] for k in ('t','raw','imu_valid')};sensor.update(setup=e['setup'],initialization=e['initialization'])
        expected_motion=prediction(e,np.array(fits[e['setup']]['weights']))[0]
        actual=predict(sensor);error=float(np.max(np.abs(actual-expected_motion)));maximum=max(maximum,error)
        assert error<1e-7
        sensor.update(gt_xy=np.full((len(sensor['t']),2),1e9),condition='poison',participant='poison')
        assert np.array_equal(predict(sensor),actual)
        checks.append(dict(id=e['row']['id'],maximum_motion_difference=error))
        if len(checks)%20==0:print(f'Verified {len(checks)}/207',flush=True)
    sensor['gt_xy']=np.full((len(sensor['t']),2),1e9);sensor['condition']='poison';sensor['participant']='poison'
    assert np.array_equal(predict(sensor),actual)
    p.save_json(OUT/'trial_verification.json',checks)
    assert len(checks)==207
    p.save_json(OUT/'verification.json',dict(reused_coefficients=True,source_model_sha256=p.digest(p.ROOT/'models/reservoir_path_v121/model.json'),recordings=len(entries),maximum_motion_difference=maximum,optical_and_identity_poisoning_invariant=True,
        note='Full TRAIN inference reproduction only; these are not held-out accuracy results'))
    (OUT/'README.md').write_text('''# Reservoir path v121

Callable full-TRAIN candidate, frozen after selection on three participant folds.
Held-fold ATE129.739811mm versus matched retainedv34 132.240200mm; all original
guards pass. No validation/test result or universal superiority claim.

```python
from reservoir_inference_v121 import load_reservoir_model
predict = load_reservoir_model()
motion = predict(sensor)
```

Run CPU with CUDA_VISIBLE_DEVICES=-1 before importing torch. sensor contains
setup,t,raw(Nx18),imu_valid and initialization or original startup_imu history.
Motion columns: forwardm/s,lateralm/s,yawrad/s. No optical or maneuver inputs.
Use the existing dynamic_blend_inference_v34.integrate_motion with a separately
supplied initial pose. Original clocks/crop/support assumptions still apply.
Inherited base models and their local sealed artifacts are required. Model is
offline (base uses future context), and inherited calibration includes legacy data.
New residual fits use only207 identified TRAIN recordings. No deployment promotion.
''',encoding='utf-8')
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file() and f.name!='artifact_manifest.json'}))
    print(json.dumps(dict(full_train_recordings=len(entries),maximum_motion_difference=maximum,ready_for_frozen_validation=True)),flush=True)


if __name__=='__main__':main()
