"""CPU forward-only temporal ridge, fixed training-fold context comparison."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from pipeline import ROOT,save_json,write_csv,digest,metrics,summarize
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from trajectory_calibration_v10 import integrate
from learning import training_group

FOLD={'No.3','No.8','No.15','No.20'}
GRID=[dict(context=0.,alpha=0.,gain=0.)]+[dict(context=context,alpha=alpha,gain=gain) for context in (.25,.5,1.) for alpha in (.1,1.,10.) for gain in (.25,.5)]

def features(sensor,m,c,state,context):
    # v14's exact central raw feature block; startup gravity/gyro handling fixed.
    central=feature_matrix(sensor,m,c,state,'gravity_rotation')[:,30:45]
    t=sensor['t'];offsets=(-context,-context/2,0.,context/2,context)
    return np.c_[*[np.c_[*[np.interp(t+o,t,central[:,j]) for j in range(central.shape[1])]] for o in offsets]].astype(np.float32)

def fit(entries,context,alpha):
    result={}
    for setup in sorted({e['setup'] for e in entries}):
        es=[e for e in entries if e['setup']==setup];xs=[];ys=[];groups=[]
        for e in es:
            ids=np.flatnonzero(e['label'])[::10];xs.append(e['x'][context][ids]);ys.append(e['target'][ids]);groups.extend([e['group']]*len(ids))
        x=np.concatenate(xs).astype(float);y=np.concatenate(ys);counts=Counter(groups);w=np.array([1/counts[g] for g in groups]);w/=w.sum();mean=(x*w[:,None]).sum(0);std=np.maximum(np.sqrt(((x-mean)**2*w[:,None]).sum(0)),1e-5);z=np.c_[(x-mean)/std,np.ones(len(x))];penalty=alpha*np.eye(z.shape[1]);penalty[-1,-1]=0;coeff=np.linalg.solve(z.T@(z*w[:,None])+penalty,z.T@(y*w));result[setup]=dict(mean=mean.tolist(),std=std.tolist(),weights=coeff.tolist(),cap=max(float(np.quantile(np.abs(y),.995)),.02))
    return result

def corrected(e,fits,c):
    m=e['motion'].copy()
    if not c['gain']:return m
    model=fits[e['setup']];z=np.c_[(e['x'][c['context']]-model['mean'])/model['std'],np.ones(len(m))];r=np.clip(z@model['weights'],-model['cap'],model['cap']);m[:,0]+=c['gain']*r;return m

def score(entries,fits,c,cfg):
    records=[]
    for e in entries:
        xy,h=integrate(e['data'],corrected(e,fits,c));records.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(e['data'],xy,h,cfg)))
    return summarize(records),records

def prepare(source,cfg,partition,manifest,cal,states,predict,out):
    entries=[]
    for row,d,_ in observed_rows(source,cfg,partition,manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};m=predict(imu);state=states[row['id']];x={c:features(imu,m,cal[row['setup']],state,c) for c in (.25,.5,1.)};label=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v']);target=d['gt_v']-m[:,0];entries.append(dict(row=row,data=d,motion=m,x=x,label=label,target=target,setup=row['setup'],group=training_group(row)))
        if partition=='train':
            # Empirical training cache separates supervision fields from features.
            np.savez_compressed(out/'training_features'/(row['id']+'.npz'),base_motion=m,t=d['t'],imu_valid=d['imu_valid'],x025=x[.25],x05=x[.5],x1=x[1.],target_forward_residual=target,observed_label_valid=label)
        if len(entries)%50==0:print(partition,'prepared',len(entries),flush=True)
    return entries

def main():
    started=time.perf_counter();out=ROOT/'outputs_braking_context_v17'
    if out.exists():raise RuntimeError('Preserve prior experiment')
    out.mkdir();(out/'training_features').mkdir();torch.set_num_threads(4)
    if torch.cuda.is_available():raise RuntimeError('CPU-only comparator')
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());parent=ROOT/'outputs_stationary_gravity_v14';pm=json.loads((parent/'artifact_manifest.json').read_text())
    if digest(parent/'initialization.json')!=pm['sha256']['initialization.json']:raise RuntimeError('Changed startup audit')
    states={r['id']:r for r in json.loads((parent/'initialization.json').read_text())['records']};predict=load_observed_ridge();save_json(out/'predeclared_grid.json',dict(candidates=GRID,fold=sorted(FOLD),rule='Minimum equalparticipant trajectory RMSE with <=5%worstparticipant regression;zeroeligible',forward_only=True,context_hypothesis='Temporal phase relationship, not clock correction; no GT-selected lags',test_evaluated=False));train=prepare(source,cfg,'train',manifest,cal,states,predict,out);inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD];(_,people,_),_=score(inner,{},GRID[0],cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates=[];records=[]
    for c in GRID:
        fits=fit(fitrows,c['context'],c['alpha']) if c['gain'] else {}; (summary,people,conditions),trial=score(inner,fits,c,cfg);ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in people);result=dict(c,score=summary['equal_participant_mean_position_rmse_m'],worst_person_ratio=ratio);candidates.append(result);records.extend([dict(context=c['context'],alpha=c['alpha'],gain=c['gain'],**r) for r in trial]);print('inner',result,flush=True)
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),caveat='Conditionalfold: inheritedridge/calibration sawthesepeople'));write_csv(out/'inner_trials.csv',records);fits=fit(train,selected['context'],selected['alpha']) if selected['gain'] else {};save_json(out/'model.json',dict(selected=selected,fits=fits,training_ids=[e['row']['id'] for e in train],feature_count=75,feature_schema='v14initialgravityrotationrawsensorphysical15channels,fivefixedcontextoffsets;forwardonly'))
    del train,inner,fitrows
    validation=prepare(source,cfg,'validation',manifest,cal,states,predict,out);summaries={}
    for name,f,c in [('cpu_ridge',{},GRID[0]),('forward_context',fits,selected)]:
        (summary,people,conditions),trial=score(validation,f,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',trial),('participants',people),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=len(validation),test_evaluated=False,cpu_only=True,forward_only=True,runtime_seconds=time.perf_counter()-started,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'stationary_gravity_experiment_v14.py',parent/'initialization.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json',ROOT/'outputs_observed_ridge_v8/artifact_manifest.json']}));lines=['# Forward-only context experiment v17','','Fixed conditionaltrainingparticipantfold selectscontext/penalty/gain before finalvalidation. Unchangedridgeyaw/lateral;startupIMUgravityaudit fromv14 unchanged. Context offsets ±0.25/±0.5/±1 seconds are compared; no shift oftimestamps oropticalposes. Trainingfeaturescachedwithsupervisionfields explicitlyseparated.','',f'Selected: {selected}','','| Model | Overall RMSE(mm) |','|---|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for k,v in summaries.items()]+['','PairedCPUbaseline;repeatedvalidationexploratory. This comparison doesnotestablishsensorlatency norverifiedspecificforceconversion. No test recordings opened.'];(out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)
if __name__=='__main__':main()
