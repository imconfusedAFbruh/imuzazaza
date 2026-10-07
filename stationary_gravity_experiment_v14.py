"""CPU temporal residual with initial-five-second IMU gravity initialization.

Fixed participant-fold selection; original optical masks, clocks, calibration,
and initial optical pose stay preserved. Per-recording initialization uses IMU
samples before cache cropping. Gravity cannot identify mounting yaw.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,imu_streams,sample_streams,velocities,metrics,summarize,runs,save_json,write_csv,digest
from learning import training_group
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from trajectory_calibration_v10 import integrate

FOLD={'No.3','No.8','No.15','No.20'}
CONTEXT=(-.5,-.25,0.,.25,.5)
GRID=[dict(mode='control',alpha=0.,gain=0.)]+[dict(mode=mode,alpha=alpha,gain=gain) for mode in ('shared','centered','gravity_rotation') for alpha in (.1,1.,10.) for gain in (.25,.5)]

def initialization(row,cal,cfg):
    """Only original IMU acquisition's first five seconds; never optical data."""
    c=cal[row['setup']]
    default=dict(gravity=c['center_gravity_direction'],gyro_bias=c['gyro_bias_counts'][2],eligible=False,quiet_seconds=0.,algorithm='native initial five seconds',reason='No contiguous initial stationary candidate')
    try:
        streams=imu_streams(ROOT/row['imu']);t,raw,valid=sample_streams(streams,cfg)
        keep=t<=t[0]+5.;t,raw,valid=t[keep],raw[keep],valid[keep]
        if len(t)<150:return dict(default,reason='Initial shared IMU interval too short')
        acc=raw[:,12:15]/c['accel_counts_per_g'][2];gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale']);wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]]
        sd=np.sqrt(np.maximum(uniform_filter1d(acc**2,101,axis=0)-uniform_filter1d(acc,101,axis=0)**2,0));gate=(np.max(np.abs(wheel),axis=1)<.05)&(np.linalg.norm(gyro,axis=1)<.1)&(np.max(sd,axis=1)<.02)&valid
        quiet=np.zeros(len(gate),bool)
        # Avoid reflected rolling variance at acquisition/window boundaries.
        gate[:50]=False;gate[-50:]=False
        for a,b in runs(gate):
            if b-a>=100:quiet[a:b]=True
        if not quiet.any():return default
        g=np.median(acc[quiet],axis=0);bias=np.median(raw[quiet,15:18],axis=0);globalg=np.array(c['center_gravity_direction']);angle=np.rad2deg(np.arccos(np.clip(g@globalg/np.linalg.norm(g)/np.linalg.norm(globalg),-1,1)))
        return dict(gravity=g.tolist(),gyro_bias=bias.tolist(),eligible=True,quiet_seconds=float(quiet.sum()/cfg['hz']),algorithm=default['algorithm'],reason='',gravity_angle_from_date_deg=float(angle),gravity_norm_g=float(np.linalg.norm(g)),first_quiet_native_time_s=float(t[np.flatnonzero(quiet)[0]]-t[0]),last_quiet_native_time_s=float(t[np.flatnonzero(quiet)[-1]]-t[0]))
    except (ValueError,OSError,KeyError) as exc:return dict(default,reason=type(exc).__name__+': '+str(exc))

def gravity_rotation(source,target):
    """Minimum rotation between gravity vectors; leaves yaw unobserved."""
    a=np.array(source,dtype=float);b=np.array(target,dtype=float);a/=np.linalg.norm(a);b/=np.linalg.norm(b);v=np.cross(a,b);c=float(a@b);s=float(np.linalg.norm(v))
    if s<1e-10:return np.eye(3) # opposite gravity is not expected; conservative fallback
    k=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+k+k@k*((1-c)/(s*s))

def feature_matrix(sensor,motion,c,state,mode):
    raw=sensor['raw'];t=sensor['t'];a=raw[:,12:15]/c['accel_counts_per_g'][2];globalg=np.array(c['center_gravity_direction']);globalb=np.array(c['gyro_bias_counts'][2]);g=np.array(state['gravity']);b=np.array(state['gyro_bias'])
    if mode=='shared':acc=a-globalg;gyro=(raw[:,15:18]-globalb)*abs(c['terms'][2]['scale'])
    elif mode=='centered':acc=a-g;gyro=(raw[:,15:18]-b)*abs(c['terms'][2]['scale'])
    elif mode=='gravity_rotation':
        r=gravity_rotation(g,globalg);acc=(a-g)@r.T;gyro=(raw[:,15:18]-b)@r.T*abs(c['terms'][2]['scale'])
    else:raise ValueError(mode)
    wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]];wheel_yaw=(wheel[:,1]-wheel[:,0])/c['track_width_m'];base=velocities(sensor,c)
    # Same dimensions/context and source channels for all compared modes.
    vertical=gyro@(globalg/np.linalg.norm(globalg) if mode in ('shared','gravity_rotation') else g/np.linalg.norm(g))
    f=np.c_[acc,gyro,wheel,motion[:,0],motion[:,2],wheel_yaw-base[:,1],np.gradient(base[:,0],t),vertical,vertical-motion[:,2],np.full(len(t),float(state['eligible']))]
    return np.c_[*[np.c_[*[np.interp(t+offset,t,f[:,j]) for j in range(f.shape[1])]] for offset in CONTEXT]].astype(np.float32)

def fit(entries,mode,alpha):
    fits={}
    for setup in sorted({e['setup'] for e in entries}):
        es=[e for e in entries if e['setup']==setup];xs=[];ys=[];groups=[]
        for e in es:
            ids=np.flatnonzero(e['label'])[::10];xs.append(e['x'][mode][ids]);ys.append(e['target'][ids]);groups.extend([e['group']]*len(ids))
        x=np.concatenate(xs).astype(float);y=np.concatenate(ys);counts=Counter(groups);w=np.array([1/counts[g] for g in groups]);w/=w.sum();mean=(x*w[:,None]).sum(0);std=np.maximum(np.sqrt(((x-mean)**2*w[:,None]).sum(0)),1e-5);z=np.c_[(x-mean)/std,np.ones(len(x))];reg=alpha*np.eye(z.shape[1]);reg[-1,-1]=0;coef=np.linalg.solve(z.T@(z*w[:,None])+reg,z.T@(y*w[:,None]));cap=np.maximum(np.quantile(np.abs(y),.995,axis=0),[.02,.01]);fits[setup]=dict(mean=mean.tolist(),std=std.tolist(),weights=coef.tolist(),cap=cap.tolist())
    return fits

def correction(entry,fit,candidate):
    m=entry['motion'].copy()
    if not candidate['gain']:return m
    model=fit[entry['setup']];x=entry['x'][candidate['mode']];z=np.c_[(x-model['mean'])/model['std'],np.ones(len(x))];r=np.clip(z@model['weights'],-np.array(model['cap']),np.array(model['cap']));m[:,[0,2]]+=candidate['gain']*r
    return m

def score(entries,fits,candidate,cfg):
    records=[]
    for e in entries:
        m=correction(e,fits,candidate);xy,h=integrate(e['data'],m);records.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(e['data'],xy,h,cfg)))
    return summarize(records),records

def prepare_rows(source,cfg,partition,manifest,cal,predict,initializations):
    entries=[]
    for row,data,_ in observed_rows(source,cfg,partition,manifest):
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')};m=predict(sensor);state=initialization(row,cal,cfg);initializations.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],partition=partition,setup=row['setup'],**state));label=data['label_valid']&data['imu_valid']&np.isfinite(data['gt_v'])&np.isfinite(data['gt_yaw']);target=np.c_[data['gt_v'],data['gt_yaw']]-m[:,[0,2]];x={mode:feature_matrix(sensor,m,cal[row['setup']],state,mode) for mode in ('shared','centered','gravity_rotation')};entries.append(dict(row=row,data=data,motion=m,target=target,label=label,x=x,setup=row['setup'],group=training_group(row)))
        if len(entries)%50==0:print(partition,'prepared',len(entries),flush=True)
    return entries

def main():
    started=time.perf_counter();out=ROOT/'outputs_stationary_gravity_v14'
    if out.exists():raise RuntimeError('Preserve prior experiment')
    out.mkdir();torch.set_num_threads(4)
    if torch.cuda.is_available():raise RuntimeError('CPU-only comparator required')
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());predict=load_observed_ridge();initializations=[]
    save_json(out/'predeclared_grid.json',dict(candidates=GRID,fold=sorted(FOLD),context_seconds=CONTEXT,gate='Nativefirst5seconds; bothwheel<.05m/s,centergyro3norm<.1rad/s,centeraccrollingSD<.02g,min1s;exclude .5svarianceboundaries;fallbackdategravity/bias',selection='Minimum equal participant trajectory RMSE with at most5%worstparticipant regression;zeroeligible',test_evaluated=False))
    train=prepare_rows(source,cfg,'train',manifest,cal,predict,initializations);save_json(out/'training_initialization.json',dict(records=initializations,interpretation='Originalfirst5secondsofIMUonly;beforecachecropping'));inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD]
    (base,people,_),_=score(inner,{},GRID[0],cfg);personbase={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates=[];inner_trials=[]
    for candidate in GRID:
        fits=fit(fitrows,candidate['mode'],candidate['alpha']) if candidate['gain'] else {}; (summary,people,conditions),records=score(inner,fits,candidate,cfg);ratio=max(p['mean_trial_position_rmse_m']/personbase[p['participant']] for p in people); result=dict(candidate,score=summary['equal_participant_mean_position_rmse_m'],heading=summary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=ratio);candidates.append(result);inner_trials.extend([dict(mode=candidate['mode'],alpha=candidate['alpha'],gain=candidate['gain'],**r) for r in records]);print('inner',result,flush=True)
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),caveat='Inherited base/calibration previously saw innerparticipants; conditional residualselection only'))
    write_csv(out/'inner_trials.csv',inner_trials);fits=fit(train,selected['mode'],selected['alpha']) if selected['gain'] else {};save_json(out/'model.json',dict(fits=fits,candidate=selected,training_ids=[e['row']['id'] for e in train],context_seconds=CONTEXT,feature_schema='centeracc3+gyro3,wheels2,ridgeforward+yaw,wheel-chassisyawconflict,wheelmeanacc,initialeligibleflag;fivecontexts;bodygravityyawunobservable'))
    # Final validation starts only after the training fold has selected parameters.
    del train,fitrows,inner
    validation=prepare_rows(source,cfg,'validation',manifest,cal,predict,initializations);summaries={}
    for name,f,c in [('cpu_ridge',{},GRID[0]),('stationary_gravity',fits,selected)]:
        (summary,people,conditions),records=score(validation,f,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',people),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    save_json(out/'initialization.json',dict(records=initializations,interpretation='IMU-only nativeacquisitionfirst5seconds,precachecrop;actualeligibilitynotfromopticalpose'));write_csv(out/'initialization.csv',[{k:v for k,v in r.items() if k not in ('gravity','gyro_bias')} for r in initializations]);save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=len(validation),test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-started,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),source/'artifact_manifest.json',ROOT/'outputs_observed_ridge_v8/artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json']}))
    lines=['# Initial stationary gravity features v14','','CPU paired baseline; no GPU used. Initialization uses the original IMU acquisition first five seconds before optical overlap cropping. Fixed IMU stationarity gate and date-calibration fallback. One optical initial pose and existing clocks/masks are preserved. Gravity alignment leaves yaw unobserved.','',f'Selected on conditional training participant fold: {selected}','','| Model | Overall RMSE(mm) |','|---|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for k,v in summaries.items()]+['','CPU baseline can differ minutely from frozen GPU results; report paired CPU gains. All candidates are preserved; repeated validation exploratory. No inferred factory units or complete mounting rotation claim. Per-record initialization candidates are not independently verified actual stationarity.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)
if __name__=='__main__':main()
