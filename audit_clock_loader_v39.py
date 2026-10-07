"""Independent v38 split/cache mapping plus fresh IMU-only loader reproduction."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json,csv,time,hashlib
from pathlib import Path
import numpy as np
import torch
import pipeline as p
from clock_refit_inference_v38 import load_clock_refit

OUT=p.ROOT/'outputs_clock_loader_v39';MODEL=p.ROOT/'outputs_clock_refit_v38'
def main():
    started=time.perf_counter();torch.set_num_threads(4)
    if OUT.exists():raise RuntimeError('Preserve audit')
    OUT.mkdir();protocol=json.loads((MODEL/'protocol.json').read_text());model=json.loads((MODEL/'v21_model.json').read_text());tilt=json.loads((MODEL/'tilt_model.json').read_text())
    manifest=json.loads((MODEL/'artifact_manifest.json').read_text())['sha256']
    for name,sha in manifest.items():
        if p.digest(MODEL/name)!=sha:raise RuntimeError('Changed v38artifact:'+name)
    inventory={q['id']:q for q in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    old=p.ROOT/'outputs_observed_reference_v7';new=p.ROOT/'outputs_observed_sync_v9'
    oldqc=list(csv.DictReader((old/'qc.csv').open(newline='')));newqc=list(csv.DictReader((new/'qc.csv').open(newline='')))
    train={q['id'] for q in oldqc if q['status']=='accepted' and q['partition']=='train'};valid={q['id'] for q in oldqc if q['status']=='accepted' and q['partition']=='validation'}
    accepted={q['id'] for q in newqc if q['status']=='accepted'};fallback=train-accepted
    assert train==set(protocol['training_ids'])==set(model['training_ids'])==set(tilt['training_ids']) and len(train)==473
    assert valid==set(protocol['validation_ids']) and len(valid)==71 and valid<=accepted
    assert fallback==set(protocol['fallback_old_clock_ids']) and len(fallback)==8
    assert not ({inventory[id]['participant'] for id in train}&{inventory[id]['participant'] for id in valid})
    changes={q['id']:q for q in csv.DictReader((MODEL/'clock_changes.csv').open(newline=''))};samples={};mappings=[]
    sm={f:json.loads((f/'artifact_manifest.json').read_text())['sha256'] for f in (old,new)}
    for id in sorted(train|valid):
        source=old if id in fallback else new;file=source/'cache'/(id+'.npz');meta=file.with_suffix('.json')
        for f in (file,meta):
            if p.digest(f)!=sm[source][str(f.relative_to(source))]:raise RuntimeError('Changed mappedcache:'+id)
        metadata=json.loads(meta.read_text());row=inventory[id]
        # Raw identity binds each correction target to its acquisition. No test.
        for kind in ('imu','c3d'):
            if p.digest(p.ROOT/row[kind])!=metadata['signature'][kind+'_sha256']:raise RuntimeError('Changed acquisition:'+id)
        assert changes[id]['source']==source.name and float(changes[id]['new_offset_s'])==metadata['synchronization']['offset_s']
        if id in fallback:assert float(changes[id]['offset_delta_s'])==0.
        with np.load(file) as z:
            label=z['label_valid']&z['imu_valid']&np.isfinite(z['gt_v'])&np.isfinite(z['gt_yaw'])
            assert (label<=z['gt_valid']).all()
            count=len(np.flatnonzero(label)[::10])
            if id in train:samples[row['setup']]=samples.get(row['setup'],0)+count
            mappings.append(dict(id=id,partition=row['partition'],source=source.name,fallback=id in fallback,label_frames=int(label.sum()),point_samples=count))
    for setup,count in samples.items():assert count==model['fits'][setup]['samples']==tilt['fits'][setup]['samples']
    predict=load_clock_refit();states={q['id']:q for q in json.loads((p.ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};reproduction=[]
    for n,id in enumerate(sorted(valid)):
        row=inventory[id]
        with np.load(new/'cache'/(id+'.npz')) as z:sensor={k:z[k] for k in ('setup','t','raw','imu_valid')}
        result,state=predict(sensor,p.ROOT/row['imu'])
        with np.load(MODEL/'new_clock_trajectories'/(id+'.npz')) as z:expected=z['new_clock_refit_blend_motion']
        error=float(np.max(np.abs(result-expected)));gravity=float(np.max(np.abs(np.array(state['gravity'])-states[id]['gravity'])));bias=float(np.max(np.abs(np.array(state['gyro_bias'])-states[id]['gyro_bias'])))
        if error>1e-7 or gravity>1e-10 or bias>1e-10 or state['eligible']!=states[id]['eligible']:raise RuntimeError('Freshstartup/motion reproduction failed:'+id)
        reproduction.append(dict(id=id,max_motion_error=error,max_gravity_error=gravity,max_bias_error=bias,startup_eligible=state['eligible']))
        if (n+1)%10==0:print('Reproduced',n+1,flush=True)
    p.write_csv(OUT/'mapped_cache_audit.csv',mappings);p.write_csv(OUT/'fresh_startup_motion.csv',reproduction)
    p.save_json(OUT/'run.json',dict(training_ids_verified=473,validation_ids_verified=71,fallback_ids=sorted(fallback),all_train_label_counts_match_models=True,
        parent_seals_unchanged=True,test_accessed=False,no_reference_predictor_inputs=True,fresh_startup_reproduced=71,max_motion_error=max(q['max_motion_error'] for q in reproduction),
        runtime_seconds=time.perf_counter()-started,loader_sha256=p.digest(p.ROOT/'clock_refit_inference_v38.py'),audit_sha256=p.digest(Path(__file__))))
    (OUT/'report.md').write_text('# v38 IMU-only loader audit v39\n\nAll473train/71validationIDs, exact8oldclockfallbacks, rawacquisition/cachehashes, labelsupport andper-setup point counts verified independently. Allv38sealedartifacthashes unchanged. No test.\n\nFresh originalfirst5s IMU-onlystartup reproduced all71storedgravity/bias/eligibilitystates and all71newclockrefitblendmotionarrays to numerical tolerance. Loader accepts exactlysetup,t,raw,imu_valid plusnativeIMUCSVpath; reference/participant fields rejected. It returnsmotion andstartupstate, not absolute global pose. Integration requires a separately declared initialpose.\n\nOffline futureIMUcontext andlowpass remain; calibration/baseinherited, unitsunverified, no completepipelinefoldrefit. No accuracy promotion based solely on this loader audit.\n',encoding='utf-8')
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print('Audit passed',flush=True)

if __name__=='__main__':main()
