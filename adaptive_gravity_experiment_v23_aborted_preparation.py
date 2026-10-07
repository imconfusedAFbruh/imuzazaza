"""Offline gravity-direction state estimation; training sensor constants fixed."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import torch
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,digest,save_json,write_csv,runs,velocities
from learning import training_group
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix,CONTEXT
from nonlinear_endpoint_experiment_v21 import nonlinear_features,bounds,adapted,load_train
from motion_endpoint_experiment_v16 import normal_system,fit,score,FOLD

VARIANTS=('static_v21','quiet_direction','dynamic_1s','dynamic_5s')

def unit(x):return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-10)

def gravity_states(sensor,c):
    raw=sensor['raw'];t=sensor['t'];n=len(t);acc=raw[:,12:15]/c['accel_counts_per_g'][2];gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale']);wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]]
    sd=np.sqrt(np.maximum(uniform_filter1d(acc**2,101,axis=0)-uniform_filter1d(acc,101,axis=0)**2,0));norm=np.linalg.norm(acc,axis=1)
    gate=(np.max(np.abs(wheel),axis=1)<.05)&(np.linalg.norm(gyro,axis=1)<.1)&(np.max(sd,axis=1)<.02)&(norm>=.85)&(norm<=1.15)&sensor['imu_valid'];gate[:50]=False;gate[-50:]=False;quiet=np.zeros(n,bool)
    segments=[]
    for a,b in runs(gate):
        if b-a>=100:quiet[a:b]=True;segments.append((a,b))
    globalg=unit(np.array(c['center_gravity_direction'],float));result={};stats=dict(quiet_seconds=float(quiet.sum()/100),eligible=bool(quiet.any()),state_only='Unit gravity direction; training gyro bias/scale and accelerometer counts-per-g fixed')
    if not quiet.any():
        for variant in VARIANTS[1:]:result[variant]=np.tile(globalg,(n,1))
        return result,stats
    median=unit(np.median(acc[quiet],axis=0));result['quiet_direction']=np.tile(median,(n,1));first,last=segments[0],segments[-1];observations=unit(acc);midgyro=(gyro[1:]+gyro[:-1])/2;dt=np.diff(t)
    # Fixed first-order gyro transport gdot=-omega cross g; quiet data update direction only.
    for tau,name in [(1.,'dynamic_1s'),(5.,'dynamic_5s')]:
        forward=np.zeros((n,3));reverse=np.zeros((n,3));forward[0]=unit(np.median(acc[first[0]:first[1]],axis=0));reverse[-1]=unit(np.median(acc[last[0]:last[1]],axis=0));fconfidence=np.zeros(n);rconfidence=np.zeros(n);latest=None
        for i in range(1,n):
            g=forward[i-1]-dt[i-1]*np.cross(midgyro[i-1],forward[i-1]);g=unit(g)
            if quiet[i]:weight=1-np.exp(-dt[i-1]/tau);g=unit((1-weight)*g+weight*observations[i]);latest=t[i]
            forward[i]=g;fconfidence[i]=0. if latest is None else np.exp(-(t[i]-latest)/tau)
        latest=None
        for i in range(n-2,-1,-1):
            g=reverse[i+1]+dt[i]*np.cross(midgyro[i],reverse[i+1]);g=unit(g)
            if quiet[i]:weight=1-np.exp(-dt[i]/tau);g=unit((1-weight)*g+weight*observations[i]);latest=t[i]
            reverse[i]=g;rconfidence[i]=0. if latest is None else np.exp(-(latest-t[i])/tau)
        combined=forward*fconfidence[:,None]+reverse*rconfidence[:,None];missing=np.linalg.norm(combined,axis=1)<1e-10;combined[missing]=median;result[name]=unit(combined)
    stats['quiet_gravity_angle_from_date_deg']=float(np.rad2deg(np.arccos(np.clip(median@globalg,-1,1))))
    return result,stats

def rotate_gravity(x,g,target):
    a=unit(g);b=unit(np.array(target));v=np.cross(a,b);cos=np.sum(a*b,axis=1);cross=np.cross(v,x);rot=x+cross+np.cross(v,cross)/np.maximum(1+cos[:,None],1e-6);bad=cos<-.999;rot[bad]=x[bad]
    return rot

def state_features(sensor,m,c,g,eligible):
    raw=sensor['raw'];t=sensor['t'];globalg=np.array(c['center_gravity_direction']);acc=rotate_gravity(raw[:,12:15]/c['accel_counts_per_g'][2]-g,g,globalg);gyro=rotate_gravity((raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale']),g,globalg)
    wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]];base=velocities(sensor,c);wy=(wheel[:,1]-wheel[:,0])/c['track_width_m'];vertical=gyro@unit(globalg);f=np.c_[acc,gyro,wheel,m[:,0],m[:,2],wy-base[:,1],np.gradient(base[:,0],t),vertical,vertical-m[:,2],np.full(len(t),float(eligible))]
    return np.c_[*[np.c_[*[np.interp(t+offset,t,f[:,j]) for j in range(f.shape[1])]] for offset in CONTEXT]].astype(np.float32)

def variant_entries(entries,variant,cal):
    result=[]
    for e in entries:
        linear=e['linear'] if variant=='static_v21' else state_features(e['data'],e['motion'],cal[e['setup']],e['gravity'][variant],e['gravity_stats']['eligible']);result.append(dict(e,linear=linear,nonlinear=nonlinear_features(linear)))
    return result

def main():
    started=time.perf_counter();out=ROOT/'outputs_adaptive_gravity_v23';parent=ROOT/'outputs_nonlinear_endpoint_v21'
    if out.exists():raise RuntimeError('Preserve gravity-state experiment')
    out.mkdir();torch.set_num_threads(4)
    for name,sha in json.loads((parent/'artifact_manifest.json').read_text())['sha256'].items():
        if digest(parent/name)!=sha:raise RuntimeError('Changed v21 artifact '+name)
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());train=load_train(ROOT/'outputs_motion_endpoint_v16');stateinfo=[]
    for i,e in enumerate(train):
        sensor={k:e['data'][k] for k in ('setup','t','raw','imu_valid')};e['gravity'],e['gravity_stats']=gravity_states(sensor,cal[e['setup']]);stateinfo.append(dict(id=e['row']['id'],partition='train',**e['gravity_stats']))
        if (i+1)%50==0:print('Training gravity states',i+1,flush=True)
    save_json(out/'predeclared_grid.json',dict(variants=VARIANTS,alpha=.1,endpoint_weight=1.,gain=.5,fold=sorted(FOLD),gate='Bothwheelabs<.05,gyro3norm<.1,axisSD<.02,norm.85–1.15,min1s,edge.5s excluded',constants='All gyro biases/scales and accelerometer counts-per-g fixed training; only gravity unit direction estimated; no magnitude or mounting-yaw calibration',offline=True))
    candidates=[];control=dict(basis='zero',gain=0,alpha=0,endpoint_weight=0);inner=[e for e in train if e['row']['participant'] in FOLD];(baseline,people,_),_=score(adapted(inner,'linear',{}),{},control,cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates.append(dict(variant='zero',score=baseline['equal_participant_mean_position_rmse_m'],worst_person_ratio=1.));models={}
    candidate=dict(basis='physical_products',alpha=.1,endpoint_weight=1.,gain=.5)
    for variant in VARIANTS:
        entries=variant_entries(train,variant,cal);fitting=[e for e in entries if e['row']['participant'] not in FOLD];evaluating=[e for e in entries if e['row']['participant'] in FOLD];clips=bounds(fitting);fits=fit(normal_system(adapted(fitting,'physical_products',clips)),.1,1.);(summary,ppl,_),_=score(adapted(evaluating,'physical_products',clips),fits,candidate,cfg);row=dict(variant=variant,score=summary['equal_participant_mean_position_rmse_m'],heading=summary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in ppl));candidates.append(row);print('Fold',row,flush=True)
        del entries,fitting,evaluating
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,rule='Minimum equal-participant path RMSE with<=5%worst-person regression; conditional inherited fold'))
    # Refit static control and selected gravity algorithm only after fixed-fold selection.
    for variant in set(['static_v21',selected['variant']]) - {'zero'}:
        entries=variant_entries(train,variant,cal);clips=bounds(entries);fits=fit(normal_system(adapted(entries,'physical_products',clips)),.1,1.);models[variant]=dict(fits=fits,feature_clip=clips)
    old=json.loads((parent/'model.json').read_text());delta=max(float(np.max(np.abs(np.array(models['static_v21']['fits'][k]['weights'])-old['fits'][k]['weights']))) for k in old['fits'])
    if delta>1e-6:raise RuntimeError('Static v21 fit reproduction differs')
    save_json(out/'model.json',dict(variant=selected['variant'],candidate=candidate if selected['variant']!='zero' else control,**(models.get(selected['variant'],dict(fits={},feature_clip={}))),training_ids=[e['row']['id'] for e in train],static_v21_max_weight_difference=delta,state_algorithm='Fixed-bias empirical gyro unit-gravity transport with fixed quiet-only direction updates; no calibration constants refit'))
    del train,inner,entries
    manifest=json.loads((source/'artifact_manifest.json').read_text());states={q['id']:q for q in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};ridge=load_observed_ridge();validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(sensor);x=feature_matrix(sensor,m,cal[row['setup']],states[row['id']],'gravity_rotation');gravity,stats=gravity_states(sensor,cal[row['setup']]);validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),gravity=gravity,gravity_stats=stats,setup=row['setup']));stateinfo.append(dict(id=row['id'],partition='validation',**stats))
    summaries={}
    for name,variant in [('cpu_ridge','zero'),('static_v21','static_v21'),('selected',selected['variant'])]:
        entries=variant_entries(validation,variant if variant!='zero' else 'static_v21',cal);q=models.get(variant,dict(fits={},feature_clip={}));(summary,ppl,conditions),records=score(adapted(entries,'physical_products' if variant!='zero' else 'linear',q['feature_clip']),q['fits'],candidate if variant!='zero' else control,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',ppl),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    expected=json.loads((parent/'run.json').read_text())['summary']['selected']['equal_participant_mean_position_rmse_m']
    if abs(summaries['static_v21']['equal_participant_mean_position_rmse_m']-expected)>1e-8:raise RuntimeError('Paired v21 score changed')
    save_json(out/'gravity_state_diagnostics.json',dict(records=stateinfo,no_quiet_fallback='Fixed training-date gravity direction; no gyro bias updates',scope='Available full retained IMU recording; future quiet data informs earlier direction. Actual stationarity remains empirically gated.'))
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=71,test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-started,static_v21_max_weight_difference=delta,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),parent/'artifact_manifest.json',ROOT/'nonlinear_endpoint_experiment_v21.py',ROOT/'stationary_gravity_experiment_v14.py',ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json']}))
    lines=['# Offline gravity-direction state experiment v23','','Variants: exact staticv21 control; full-record robust quiet gravity direction; bidirectional fixed-bias gyro gravity transport with quiet-only updates at1/5s strength. All sensor biases, scales and gravity magnitude remain fixed training constants. Only a unit direction STATE is estimated from IMU; no calibration or held-out reference fit.','',f'Fixed-fold selection: {selected}','','| Model | Overall RMSE(mm) | Heading(deg) |','|---|---:|---:|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} | {v["equal_participant_mean_heading_rmse_deg"]:.3f} |' for k,v in summaries.items()]+['','The gyro transport uses empirical isotropic date scale and first-order integration; it is a mechanism comparator, not a verified full attitude INS. Gravity leaves mounting yaw unobserved. Conservative quiet validation does not establish ground-truth stationarity. Fixed gyro-bias constants are never replaced by held-out quiet median. Future retained IMU data makes the new estimator offline. If no accepted quiet segment exists, it returns the training global gravity direction. Products/normalization/caps/models fitted on training only. Same observed endpoints and initial pose protocol; lateral remains ridge. Static v21 coefficients and score reproduced. Reused validation exploratory; no test acquisitions read.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
