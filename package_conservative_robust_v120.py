"""Export and reproduce the guard-selected v120 research fold model."""
import csv
import json
import numpy as np
import pipeline as p
from combined_physics_folds_v58 import verified_json
from clock_refit_experiment_v38 import OLD,NEW,load_cache
from conservative_robust_inference_v120 import predict_motion

OUT=p.ROOT/'models/conservative_robust_v120'
RUN=p.ROOT/'outputs_conservative_robust_v120'


def main():
    run=verified_json(RUN,'run.json');selected=run['selected']
    if not selected['eligible'] or selected['gain']==0:raise RuntimeError('No improving guard-passing model to export')
    OUT.mkdir(parents=True,exist_ok=False)
    models=[]
    for fold in range(3):
        baseline=verified_json(p.ROOT/'outputs_projected_yaw_v52',f'fold_{fold}_models.json')
        robust=verified_json(p.ROOT/'outputs_joint_robust_motion_v119',f'fold_{fold}_models.json')
        assert set(baseline['fitting_ids'])==set(robust['fitting_ids'])
        model=dict(gain=selected['gain'],calibration=baseline['calibration'],yaw=baseline['yaw'],
            residual=robust['models']['3.0'],fitting_ids=robust['fitting_ids'],held_people=robust['held_people'],fold=fold)
        models.append(model);p.save_json(OUT/f'fold_{fold}.json',model)
    q=verified_json(p.ROOT/'outputs_clock_arbitrated_v42','protocol.json')
    manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    result_manifest=json.loads((RUN/'artifact_manifest.json').read_text())['sha256']
    assert p.digest(RUN/'trials.csv')==result_manifest['trials.csv']
    rows=[r for r in csv.DictReader((RUN/'trials.csv').open(newline='')) if float(r['gain'])==selected['gain']]
    inventory={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    errors=[]
    for row in rows:
        ident=row['id'];assert inventory[ident]['partition']=='train'
        folder=OLD if ident in q['fallback_old_clock_ids'] else NEW
        d,_=load_cache(folder,ident,manifests[folder])
        sensor={k:d[k] for k in ('t','raw','imu_valid')}
        model=models[int(row['fold'])]
        assert row['participant'] in model['held_people'] and ident not in model['fitting_ids']
        motion=predict_motion(sensor,inventory[ident]['setup'],model)
        path=RUN/'predictions'/(ident+'.npz');assert p.digest(path)==result_manifest[str(path.relative_to(RUN))]
        with np.load(path) as z:expected=z[f"gain_{selected['gain']:g}_motion"]
        error=float(np.max(np.abs(motion-expected)));assert error<1e-12
        errors.append(error)
    assert len(errors)==207
    source_names=['conservative_robust_inference_v120.py','package_conservative_robust_v120.py',
        'braking_hysteresis_folds_v56.py','projected_yaw_folds_v52.py','pipeline.py']
    p.save_json(OUT/'model_card.json',dict(name='Conservative joint robust motion v120',status='accepted TRAIN development model; not validation-promoted',
        gain=selected['gain'],delta=3,selected=selected,verified_recordings=len(errors),max_motion_error=max(errors),
        inputs=['t','raw Nx18 IMU counts','imu_valid','known setup calibration'],outputs=['forward m/s','lateral m/s=0','yaw rad/s'],
        caveats=['research fold replicas, not a full-data refit','offline projected gravity filter','inherited calibration/clocks/crop dependencies','initial pose required separately for trajectory','validation/test not evaluated'],
        sources={s:p.digest(p.ROOT/s) for s in source_names},parent_manifest_sha256=p.digest(RUN/'artifact_manifest.json')))
    (OUT/'README.md').write_text('''# Conservative joint robust motion v120

Accepted TRAIN development model. Three participant-fold replicas preserve the
exact evaluated models. This bundle is not a full-data deployment refit or a
validated replacement for v34. See model_card.json for metrics and limitations.

From the research repository (local NumPy/SciPy and existing helpers required):

```python
from conservative_robust_inference_v120 import load_fold, predict_motion
model = load_fold("models/conservative_robust_v120", fold=0)
motion = predict_motion(sensor, setup, model)
```

sensor contains t (seconds), raw (N by18 IMU counts in the existing channel order)
and imu_valid (boolean). setup must match an available calibration key. Output
columns are forward m/s, zero lateral m/s, yaw rad/s. No optical values or
maneuver labels are read by motion inference. Trajectory integration separately
requires the same initial pose and inherited time/support conventions.

All207 held TRAIN motions reproduced the sealed evaluation within1e-12.
Do not average fold models or choose a fold from the true maneuver: neither
operation was evaluated. Use the recorded held_people mapping for reproduction.
''',encoding='utf-8')
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps(dict(gain=selected['gain'],verified_recordings=207,max_motion_error=max(errors))),flush=True)


if __name__=='__main__':main()
