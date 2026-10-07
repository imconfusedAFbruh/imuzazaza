"""Empirical dynamic acceleration-direction features over v21. No SI attitude claim."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import torch
from scipy import signal
from pipeline import ROOT,save_json,write_csv,digest,metrics,summarize,runs
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted,nonlinear_features
from motion_endpoint_experiment_v16 import normal_system,fit,score
from participant_folds_experiment_v24 import FOLDS
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix

OUT=ROOT/'outputs_dynamic_tilt_v33';C=dict(basis='physical_products',alpha=.1,endpoint_weight=1.,gain=.5)
CUTOFFS=(.3,.75);OFFSETS=(-.5,0.,.5)

def dynamic_features(d,m,c,state,cutoff):
    t=d['t'];a=d['raw'][:,12:15]/c['accel_counts_per_g'][2];hz=1/np.median(np.diff(t));sos=signal.butter(2,cutoff,fs=hz,output='sos');low=a.copy()
    for start,end in runs(d['imu_valid']):
        if end-start>15:low[start:end]=signal.sosfiltfilt(sos,a[start:end],axis=0)
    u=low/np.maximum(np.linalg.norm(low,axis=1)[:,None],1e-5);g=np.array(state['gravity']);g=g/max(np.linalg.norm(g),1e-5)
    gyro=(d['raw'][:,15:18]-np.array(state['gyro_bias']))*abs(c['terms'][2]['scale'])
    projected=np.sum(gyro*u,axis=1);fixed=gyro@g;cos=np.clip(u@g,-1,1);tilt=np.linalg.norm(u-g,axis=1)
    norm=np.linalg.norm(a,axis=1);consistent=np.clip(1-np.abs(norm-1)/.15,0,1)
    wheel=np.c_[*[d['raw'][:,q['column']]*q['scale']+q['intercept'] for q in c['terms'][:2]]].mean(1)
    f=np.c_[u-g,projected-fixed,projected,cos-1,wheel*(cos-1),m[:,0]*(cos-1),tilt,consistent]
    return np.c_[*[np.c_[*[np.interp(t+o,t,f[:,j]) for j in range(f.shape[1])]] for o in OFFSETS]].astype(np.float32)

def clips_extra(entries):
    return {s:dict(low=np.quantile(np.concatenate([e['extra'][np.flatnonzero(e['label'])[::10]] for e in entries if e['setup']==s]),.001,axis=0).tolist(),high=np.quantile(np.concatenate([e['extra'][np.flatnonzero(e['label'])[::10]] for e in entries if e['setup']==s]),.999,axis=0).tolist()) for s in sorted({e['setup'] for e in entries})}

def expanded(entries,clips,extra_clip):
    base=adapted(entries,C['basis'],clips);return [dict(e,x=np.c_[e['x'],np.clip(e['extra'],extra_clip[e['setup']]['low'],extra_clip[e['setup']]['high'])].astype(np.float32)) for e in base]

def main():
    start=time.perf_counter();torch.set_num_threads(4)
    if OUT.exists():raise RuntimeError('Preserve experiment')
    OUT.mkdir();source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());states={q['id']:q for q in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
    save_json(OUT/'protocol.json',dict(cutoffs_hz=CUTOFFS,context_seconds=OFFSETS,candidate=C,folds=[sorted(f) for f in FOLDS],selection='Pooled12participant minimum observed trajectory RMSE with <=5% worstperson regression relative to same-fold originalv21; zero eligible',inference='IMU-only empirical dynamic acceleration-direction proxy. Full-record offline filtering, not verified gravity/attitude; acceleration contamination possible.',test_accessed=False))
    train=load_train(ROOT/'outputs_motion_endpoint_v16');foldrecords=[]
    for i,fold in enumerate(FOLDS):
        fitting=[e for e in train if e['row']['participant'] not in fold];held=[e for e in train if e['row']['participant'] in fold];clips=bounds(fitting);original=fit(normal_system(adapted(fitting,C['basis'],clips)),C['alpha'],C['endpoint_weight']);(_,_,_),rr=score(adapted(held,C['basis'],clips),original,C,cfg);foldrecords.extend([dict(candidate='original_v21',fold=i,**r) for r in rr])
        for cutoff in CUTOFFS:
            for e in fitting+held:e['extra']=dynamic_features(e['data'],e['motion'],cal[e['setup']],states[e['row']['id']],cutoff)
            extra=clips_extra(fitting);fits=fit(normal_system(expanded(fitting,clips,extra)),C['alpha'],C['endpoint_weight']);(s,_,_),rr=score(expanded(held,clips,extra),fits,C,cfg);foldrecords.extend([dict(candidate=f'tilt_{cutoff}',fold=i,**r) for r in rr]);print('fold',i,cutoff,s['equal_participant_mean_position_rmse_m'],flush=True)
    write_csv(OUT/'fold_trials.csv',foldrecords);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in foldrecords if r['candidate']=='original_v21'])[1]};selection=[]
    for name in ['original_v21',*[f'tilt_{cutoff}' for cutoff in CUTOFFS]]:
        s,p,_=summarize([r for r in foldrecords if r['candidate']==name]);selection.append(dict(name=name,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(q['mean_trial_position_rmse_m']/basepeople[q['participant']] for q in p)))
    selected=min([q for q in selection if q['worst_person_ratio']<=1.05],key=lambda q:q['score']);save_json(OUT/'selection.json',dict(selected=selected,candidates=selection,selected_before_validation=True,caveat='Base/calibration inherited; conditional12participant correction folds, not independent whole-pipeline folds'))
    models={};clips=bounds(train)
    for cutoff in CUTOFFS:
        for e in train:e['extra']=dynamic_features(e['data'],e['motion'],cal[e['setup']],states[e['row']['id']],cutoff)
        extra=clips_extra(train);fits=fit(normal_system(expanded(train,clips,extra)),C['alpha'],C['endpoint_weight']);models[f'tilt_{cutoff}']=dict(fits=fits,feature_clip=clips,extra_clip=extra,cutoff=cutoff,candidate=C,training_ids=[e['row']['id'] for e in train]);save_json(OUT/f'tilt_{cutoff}_model.json',models[f'tilt_{cutoff}'])
    del train,fitting,held
    old=json.loads((ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text());sm=json.loads((source/'artifact_manifest.json').read_text());ridge=load_observed_ridge();records={n:[] for n in ['original_v21',*models]};cache=OUT/'trajectories';cache.mkdir()
    for row,d,_ in observed_rows(source,cfg,'validation',sm):
        sensor={k:d[k] for k in ['setup','t','raw','imu_valid']};m=ridge(sensor);x=feature_matrix(sensor,m,cal[row['setup']],states[row['id']],'gravity_rotation');e=dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup'])
        arrays=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'])
        for name,q in [('original_v21',old),*models.items()]:
            if name=='original_v21':es=adapted([e],C['basis'],q['feature_clip'])
            else:e['extra']=dynamic_features(d,m,cal[row['setup']],states[row['id']],q['cutoff']);es=expanded([e],q['feature_clip'],q['extra_clip'])
            from stationary_gravity_experiment_v14 import correction
            from trajectory_calibration_v10 import integrate
            z=es[0];mm=correction(dict(z,x={'gravity_rotation':z['x']}),q['fits'],dict(C,mode='gravity_rotation'));xy,h=integrate(d,mm);records[name].append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,cfg)));arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h;arrays[name+'_motion']=mm
        np.savez_compressed(cache/(row['id']+'.npz'),**arrays)
    summary={}
    for name,rr in records.items():
        summary[name],p,cond=summarize(rr)
        for suffix,values in [('trials',rr),('participants',p),('maneuvers',cond)]:write_csv(OUT/f'{name}_{suffix}.csv',values)
    assert abs(summary['original_v21']['equal_participant_mean_position_rmse_m']-.10258517940337743)<1e-8
    save_json(OUT/'run.json',dict(summary=summary,selected=selected,training_trials=473,validation_trials=71,test_accessed=False,base_refit=False,runtime_seconds=time.perf_counter()-start,source_sha256=digest(Path(__file__))));save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
