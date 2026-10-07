"""TRAIN-only fold-refitted dynamic gravity-projected yaw, empirical proxy."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfiltfilt
import pipeline as p
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD,NEW,load_cache
from trajectory_calibration_v10 import integrate
OUT=p.ROOT/'outputs_projected_yaw_v52';WEIGHTS=(0.,.25,.5,.75,1.)
def proxy(d,cal):
    a=d['raw'][:,12:15].copy();g=np.repeat(np.array(cal['center_gravity_direction'])[None],len(a),axis=0)
    for lo,hi in p.runs(d['imu_valid']):
        if hi-lo>30:
            filtered=sosfiltfilt(butter(2,.3,fs=100,output='sos'),a[lo:hi],axis=0);g[lo:hi]=filtered/np.maximum(np.linalg.norm(filtered,axis=1,keepdims=True),1e-8)
    return np.sum((d['raw'][:,15:18]-cal['gyro_bias_counts'][2])*g,axis=1)
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve artifact')
    OUT.mkdir();q=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text());cfg=q['old_clock_settings'];fallback=set(q['fallback_old_clock_ids']);inventory={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())};people=set.union(*FOLDS);ids=[id for id in q['training_ids'] if inventory[id]['participant'] in people];manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)};trials=[]
    p.save_json(OUT/'protocol.json',dict(hypothesis='Dynamic gravity projection reduces pitch/roll cross-axis contamination of center yaw',cutoff_hz=.3,filter_order=2,weights=WEIGHTS,scope='207knownTRAIN only; foldcalibration and yawscalar/intercept fitexcludeheld; clocks/QC/geometry inherited',caveat='Accelerationlowpass direction is a proxy, not verified attitude. Offlinefuturedata; isotropicgyro scale and mountingunverified.',validation_accessed=False,test_accessed=False))
    for id in ids:
        r=inventory[id];assert r['partition']=='train';src=OLD if id in fallback else NEW;d,_=load_cache(src,id,manifests[src]);trials.append((r,d,{}))
    records=[]
    for i,held in enumerate(FOLDS):
        cal=json.loads((p.ROOT/f'outputs_simple_refit_folds_v49/fold_{i}_calibration.json').read_text());models={}
        for setup in cal:
            xs=[];ys=[]
            for r,d,_ in trials:
                if r['participant'] in held or r['setup']!=setup:continue
                mask=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_yaw']);ix=np.flatnonzero(mask)[::5];xs.append(proxy(d,cal[setup])[ix]);ys.append(d['gt_yaw'][ix])
            models[setup]=p.robust_line(np.concatenate(xs),np.concatenate(ys))
        p.save_json(OUT/f'fold_{i}_models.json',dict(calibration=cal,yaw=models,fitting_ids=[r['id'] for r,d,_ in trials if r['participant'] not in held]))
        for r,d,_ in trials:
            if r['participant'] not in held:continue
            v=p.velocities(d,cal[r['setup']]);model=models[r['setup']];new=proxy(d,cal[r['setup']])*model['scale']+model['intercept']
            for w in WEIGHTS:
                motion=np.c_[v[:,0],np.zeros(len(v)),(1-w)*v[:,1]+w*new];xy,h=integrate(d,motion);records.append(dict(id=r['id'],participant=r['participant'],condition=r['condition'],fold=i,weight=w,**p.metrics(d,xy,h,cfg)))
        print('Completed projectionfold',i,flush=True)
    p.write_csv(OUT/'trials.csv',records);base={r['participant']:r['mean_trial_position_rmse_m'] for r in p.summarize([r for r in records if r['weight']==0])[1]};candidates=[]
    for w in WEIGHTS:
        s,pp,mm=p.summarize([r for r in records if r['weight']==w]);ratios={r['participant']:r['mean_trial_position_rmse_m']/base[r['participant']] for r in pp};candidates.append(dict(weight=w,score=s['equal_participant_mean_position_rmse_m'],heading=s['equal_participant_mean_heading_rmse_deg'],worst_ratio=max(ratios.values()),participant_ratios=ratios));p.write_csv(OUT/f'weight_{w:g}_participants.csv',pp);p.write_csv(OUT/f'weight_{w:g}_maneuvers.csv',mm)
    selected=min([q for q in candidates if q['worst_ratio']<=1.05],key=lambda q:q['score']);p.save_json(OUT/'run.json',dict(candidates=candidates,selected=selected,validation_accessed=False,test_accessed=False,runtime_s=time.perf_counter()-start));p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(candidates,indent=2),flush=True)
if __name__=='__main__':main()
