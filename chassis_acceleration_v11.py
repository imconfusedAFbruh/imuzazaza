"""Training-only empirical acceleration-assisted forward velocity smoother."""
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from scipy.signal import butter,sosfiltfilt
from scipy.linalg import solve_banded
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize,runs
from learning import training_group
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from trajectory_calibration_v10 import integrate

FOLD={'No.3','No.8','No.15','No.20'}

def smooth(x):
    if len(x)<40:return x.copy()
    return sosfiltfilt(butter(2,6,fs=100,output='sos'),x,axis=0)

def features(d,m,cal):
    raw=d['raw'];wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in cal['terms'][:2]]]
    wheel=smooth(wheel);wa=np.gradient(wheel.mean(axis=1),d['t'])
    x=np.c_[smooth(raw[:,12:18]),wheel,m[:,0],m[:,2],m[:,0]*m[:,2],wa]
    return x,wa

def prepare(row,d,m,cal):
    x,wa=features(d,m,cal);a=np.full(len(x),np.nan);valid=np.zeros(len(x),bool)
    mask=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])
    for lo,hi in runs(mask):
        if hi-lo<40:continue
        a[lo:hi]=np.gradient(d['gt_v'][lo:hi],d['t'][lo:hi]);valid[lo+15:hi-15]=True
    return dict(row=row,data=d,motion=m,x=x,wa=wa,target=a,valid=valid,setup=str(d['setup']),group=training_group(row))

def fit(entries,alpha):
    fits={}
    for setup in sorted({e['setup'] for e in entries}):
        members=[e for e in entries if e['setup']==setup];groups=[];xs=[];ys=[]
        for e in members:
            ids=np.flatnonzero(e['valid'])[::5];xs.append(e['x'][ids]);ys.append(e['target'][ids]);groups.extend([e['group']]*len(ids))
        x=np.concatenate(xs);y=np.concatenate(ys);counts=Counter(groups);w=np.array([1/counts[g] for g in groups]);w/=w.sum()
        mean=np.sum(x*w[:,None],axis=0);std=np.maximum(np.sqrt(np.sum((x-mean)**2*w[:,None],axis=0)),1e-5)
        design=np.c_[(x-mean)/std,np.ones(len(x))];cov=design.T@(design*w[:,None]);rhs=design.T@(y*w)
        penalty=alpha*np.eye(len(mean)+1);penalty[-1,-1]=0
        weight=np.linalg.solve(cov+penalty,rhs);pred=design@weight
        delta=pred-x[:,-1];threshold=max(float(np.quantile(np.abs(delta),.8)),.1)
        fits[setup]=dict(mean=mean.tolist(),std=std.tolist(),weights=weight.tolist(),accel_cap=max(float(np.quantile(np.abs(y),.995)),.1),disagreement_threshold=threshold,samples=len(x))
    return fits

def acceleration(e,fits):
    f=fits[e['setup']];x=np.c_[(e['x']-f['mean'])/f['std'],np.ones(len(e['x']))]
    return np.clip(x@f['weights'],-f['accel_cap'],f['accel_cap'])

def correct(e,fits,lam,floor,gain):
    m=e['motion'].copy()
    if not gain:return m
    a=acceleration(e,fits);threshold=fits[e['setup']]['disagreement_threshold']
    # Wheel deceleration exceeds chassis acceleration: IMU-only braking disagreement.
    gate=np.clip((a-e['wa'])/threshold,0,1)*np.clip(-e['wa']/threshold,0,1)
    prior=1-(1-floor)*gate
    for lo,hi in runs(e['data']['imu_valid']):
        if hi-lo<2:continue
        dt=np.diff(e['data']['t'][lo:hi]);n=hi-lo;q=lam/dt**2
        diag=prior[lo:hi].copy();diag[:-1]+=q;diag[1:]+=q
        bands=np.zeros((3,n));bands[1]=diag;bands[0,1:]=-q;bands[2,:-1]=-q
        rhs=prior[lo:hi]*m[lo:hi,0];force=lam*(a[lo:hi-1]+a[lo+1:hi])/2/dt
        rhs[:-1]-=force;rhs[1:]+=force
        solved=solve_banded((1,1),bands,rhs)
        m[lo:hi,0]+=gain*(solved-m[lo:hi,0])
    return m

def score(entries,fits,candidate,cfg):
    records=[]
    for e in entries:
        motion=correct(e,fits,candidate['lambda'],candidate['prior_floor'],candidate['gain'])
        xy,h=integrate(e['data'],motion)
        records.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],setup=e['setup'],**metrics(e['data'],xy,h,cfg)))
    return summarize(records),records

def main():
    started=time.perf_counter();out=ROOT/'outputs_chassis_acceleration_v11'
    if out.exists():raise RuntimeError('Preserve completed run')
    out.mkdir();torch.set_num_threads(4);source=ROOT/'outputs_observed_reference_v7'
    cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    train=[]
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};train.append(prepare(row,d,ridge(imu),cal[row['setup']]))
        if len(train)%50==0:print('Prepared training',len(train),flush=True)
    inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD]
    if len({e['row']['participant'] for e in inner})!=4:raise RuntimeError('Fold coverage changed')
    baseline=dict(alpha=0.,**{'lambda':0.},prior_floor=1.,gain=0.)
    (summary,ppl,_),_=score(inner,{},baseline,cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in ppl}
    candidates=[dict(**baseline,score=summary['equal_participant_mean_position_rmse_m'],worst_person_ratio=1.)]
    for alpha in (.1,1.):
        fits=fit(fitrows,alpha)
        for lam in (.01,.1,.3):
            for floor in (.2,1.):
                for gain in (.25,1.):
                    c=dict(alpha=alpha,**{'lambda':lam},prior_floor=floor,gain=gain)
                    (summary,ppl,_),_=score(inner,fits,c,cfg)
                    c.update(score=summary['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in ppl));candidates.append(c)
                    print('Inner',c,flush=True)
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score'])
    save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),rule='Minimum equal-participant path RMSE with <=5% worst-person regression; unchanged ridge candidate',caveat='Inherited base model saw these participants; conditional acceleration-model selection.'))
    fits=fit(train,selected['alpha']) if selected['gain'] else {}
    save_json(out/'model.json',dict(fits=fits,candidate=selected,training_ids=[e['row']['id'] for e in train],features='Filtered center raw accel3+gyro3, wheel speeds2, ridge forward/yaw/forward*yaw, wheel midpoint acceleration. Empirical units.'))
    validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};validation.append(prepare(row,d,ridge(imu),cal[row['setup']]))
    summaries={};diagnostics=[]
    for name,c,f in [('ridge',baseline,{}),('acceleration',selected,fits)]:
        (summary,ppl,conditions),records=score(validation,f,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',ppl),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    for e in validation:
        a=acceleration(e,fits) if fits else np.zeros(len(e['x']));mask=e['valid']
        diagnostics.append(dict(id=e['row']['id'],condition=e['row']['condition'],accel_rmse_mps2=float(np.sqrt(np.mean((a[mask]-e['target'][mask])**2))) if mask.any() else 0))
    write_csv(out/'acceleration_diagnostics.csv',diagnostics)
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=len(train),validation_trials=len(validation),test_evaluated=False,runtime_seconds=time.perf_counter()-started,provenance={str(f.relative_to(ROOT)):digest(f) for f in [Path(__file__),source/'artifact_manifest.json',ROOT/'observed_ridge_inference.py',ROOT/'outputs_observed_ridge_v8/artifact_manifest.json']}))
    lines=['# Empirical chassis acceleration smoother v11','','Only forward velocity changes. Ridge lateral and yaw outputs remain identical. Center acceleration conversion is supervised empirically from observed training dv/dt; factory units/mount calibration are not claimed.','',f'Fixed-fold selection: {selected}','','| Model | Overall RMSE (mm) |','|---|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for k,v in summaries.items()]+['','All 473 training recordings and 71 validation recordings use the frozen observed-reference protocol. Final evaluation occurs after fixed-fold selection and full-training refit. No test signals read. No ground-truth inputs at prediction; one initial pose is supplied separately. Center filtering and velocity smoothing use future IMU samples over the available recording and therefore are offline. Baseline velocity and acceleration features share sensors/model outputs, so this is a regularized empirical smoother, not independent-measurement uncertainty fusion. No condition/participant-specific inference rules. A negative result does not justify replacing the selected ridge.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
