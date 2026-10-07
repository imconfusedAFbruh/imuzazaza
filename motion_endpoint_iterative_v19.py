"""Clipped GaussNewton endpoint refinement, with training-only line search."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from motion_endpoint_experiment_v16 import normal_system,fit,FOLD
from trajectory_calibration_v10 import integrate

HORIZONS=(100,300,500,1000)

def load_training():
    parent=ROOT/'outputs_motion_endpoint_v16';manifest=json.loads((parent/'artifact_manifest.json').read_text());entries=[]
    for metadata in sorted((parent/'prepared_training').glob('*.json')):
        path=metadata.with_suffix('.npz')
        for f in (path,metadata):
            if digest(f)!=manifest['sha256'][str(f.relative_to(parent))]:raise RuntimeError('Changed cached training '+str(f))
        meta=json.loads(metadata.read_text());row=meta['row']
        if row['partition']!='train':raise RuntimeError('Only training cache allowed')
        if digest(ROOT/'outputs_observed_reference_v7/cache'/(row['id']+'.npz'))!=meta['source_cache_sha256']:raise RuntimeError('Changed original cache')
        if digest(ROOT/'stationary_gravity_experiment_v14.py')!=meta['feature_source_sha256'] or digest(ROOT/'outputs_stationary_gravity_v14/artifact_manifest.json')!=meta['initialization_manifest_sha256']:raise RuntimeError('Changed feature/init dependency')
        z=dict(np.load(path));data={k:v for k,v in z.items() if k not in ('features','ridge_motion','residual_target','residual_label_valid')}
        entries.append(dict(row=row,data=data,motion=z['ridge_motion'],target=z['residual_target'],label=z['residual_label_valid'],x=z['features'],setup=row['setup'],group=row['participant'] if row['participant']!='earlier-unmapped' else row['date']+':unmapped'))
    if len(entries)!=473:raise RuntimeError('Training cache coverage changed')
    return entries

def motion(e,q):
    z=np.c_[(e['x']-q['mean'])/q['std'],np.ones(len(e['x']))];r=z@q['weights'];m=e['motion'].copy();m[:,[0,2]]+=np.clip(r,-q['cap'],q['cap']);return m,z,r

def endpoint_data(e,m,sf=None,sy=None):
    d=e['data'];t=d['t'];dt=np.diff(t);v=(m[1:]+m[:-1])/2;h=np.r_[0,np.cumsum(dt*v[:,2])];mid=(h[1:]+h[:-1])/2;c,s=np.cos(mid),np.sin(mid)
    xy=np.vstack((np.zeros(2),np.cumsum(dt[:,None]*np.c_[v[:,0]*c-v[:,1]*s,v[:,0]*s+v[:,1]*c],axis=0)))
    if sf is not None:
        p=sf.shape[1];fm=(sf[1:]+sf[:-1])/2;ym=(sy[1:]+sy[:-1])/2;qh=np.vstack((np.zeros(p),np.cumsum(dt[:,None]*ym,axis=0)));qm=(qh[1:]+qh[:-1])/2
        px=np.vstack((np.zeros(2*p),np.cumsum(dt[:,None]*np.c_[c[:,None]*fm,(-s*v[:,0]-c*v[:,1])[:,None]*qm],axis=0)))
        py=np.vstack((np.zeros(2*p),np.cumsum(dt[:,None]*np.c_[s[:,None]*fm,(c*v[:,0]-s*v[:,1])[:,None]*qm],axis=0)))
    errors=[];jacobians=[];invalid=np.r_[0,np.cumsum(~d['imu_valid'])]
    for a in range(0,len(m),100):
        if not d['gt_valid'][a]:continue
        for horizon in HORIZONS:
            b=a+horizon
            if b>=len(m) or not d['gt_valid'][b] or invalid[b+1]!=invalid[a]:continue
            delta=xy[b]-xy[a];ca,sa=np.cos(h[a]),np.sin(h[a]);rot=np.array([[ca,sa],[-sa,ca]]);pred=np.r_[rot@delta,h[b]-h[a]];h0=d['gt_heading'][a];dg=d['gt_xy'][b]-d['gt_xy'][a];target=np.r_[np.array([[np.cos(h0),np.sin(h0)],[-np.sin(h0),np.cos(h0)]])@dg,d['gt_heading'][b]-h0];err=target-pred;err[2]=np.arctan2(np.sin(err[2]),np.cos(err[2]));duration=t[b]-t[a];errors.append(err/duration)
            if sf is not None:
                js=np.zeros((3,2*p));js[:2]=rot@np.vstack((px[b]-px[a],py[b]-py[a]));js[:2]+=np.array([pred[1],-pred[0]])[:,None]*np.r_[np.zeros(p),qh[a]][None,:];js[2,p:]=qh[b]-qh[a];jacobians.append(js/duration)
    return np.array(errors).reshape(-1,3),np.array(jacobians).reshape(-1,3,2*p) if sf is not None else None

def group_weights(entries):
    counts=Counter();pairs=Counter()
    for e in entries:
        counts[e['group']]+=len(np.flatnonzero(e['label'])[::10]);err,_=endpoint_data(e,e['motion']);pairs[e['group']]+=len(err)
    return counts,pairs

def objective(entries,models):
    total=0.;parts={}
    for setup in models:
        es=[e for e in entries if e['setup']==setup];counts,pairs=group_weights(es);groups=len(counts);pgroups=sum(v>0 for v in pairs.values());point=end=0.
        for e in es:
            m,_,_=motion(e,models[setup]);ids=np.flatnonzero(e['label'])[::10];r=m[ids][:,[0,2]]-e['motion'][ids][:,[0,2]];point+=np.sum((r-e['target'][ids])**2)/(groups*counts[e['group']]);err,_=endpoint_data(e,m)
            if len(err):end+=np.sum(err**2)/(pgroups*pairs[e['group']])
        reg=.1*np.sum(models[setup]['weights'][:-1]**2);parts[setup]=dict(point=point,endpoint=end,regularization=reg,total=point+end+reg);total+=point+end+reg
    return total,parts

def gauss_newton(entries,models):
    nextmodels={}
    for setup,q in models.items():
        es=[e for e in entries if e['setup']==setup];counts,pairs=group_weights(es);groups=len(counts);pgroups=sum(v>0 for v in pairs.values());p=len(q['mean'])+1;cov=np.zeros((2*p,2*p));rhs=np.zeros(2*p);current=np.r_[q['weights'][:,0],q['weights'][:,1]]
        for e in es:
            m,z,r=motion(e,q);active=np.abs(r)<np.array(q['cap']);sf=z*active[:,0,None];sy=z*active[:,1,None];ids=np.flatnonzero(e['label'])[::10];weight=1/(groups*counts[e['group']]);residual=m[:,[0,2]]-e['motion'][:,[0,2]]
            for j,f in enumerate((sf,sy)):
                a=f[ids];offset=j*p;y=e['target'][ids,j]-residual[ids,j]+a@q['weights'][:,j];cov[offset:offset+p,offset:offset+p]+=weight*a.T@a;rhs[offset:offset+p]+=weight*a.T@y
            err,jac=endpoint_data(e,m,sf,sy)
            if len(err):
                a=jac.reshape(-1,2*p);y=err.reshape(-1)+a@current;w=1/(pgroups*pairs[e['group']]);cov+=w*a.T@a;rhs+=w*a.T@y
        reg=.1*np.eye(2*p);reg[p-1,p-1]=reg[-1,-1]=0;coef=np.linalg.solve(cov+reg,rhs);nextmodels[setup]=dict(q,weights=np.c_[coef[:p],coef[p:]])
    return nextmodels

def initialize(entries):
    systems=normal_system(entries);raw=fit(systems,.1,1.)
    return {k:dict(mean=np.array(v['mean']),std=np.array(v['std']),weights=.5*np.array(v['weights']),cap=.5*np.array(v['cap'])) for k,v in raw.items()}

def run_iterations(entries,damping,callback=None):
    models=initialize(entries);obj,parts=objective(entries,models);history=[dict(iteration=1,damping=damping,objective=obj,accepted_step=0.,parts=parts)]
    if callback:callback(models,1)
    for iteration in range(2,6):
        proposed=gauss_newton(entries,models);accepted=0.;best=models;bestobj=obj;bestparts=parts
        for step in (damping,damping/2,damping/4,damping/8):
            trial={k:dict(q,weights=q['weights']+step*(proposed[k]['weights']-q['weights'])) for k,q in models.items()};value,pieces=objective(entries,trial)
            if value<=obj+1e-12:accepted=step;best=trial;bestobj=value;bestparts=pieces;break
        models,obj,parts=best,bestobj,bestparts;row=dict(iteration=iteration,damping=damping,objective=obj,accepted_step=accepted,parts=parts);history.append(row);print('Refinement',iteration,damping,'objective',obj,'step',accepted,flush=True)
        if callback and iteration in (3,5):callback(models,iteration)
    return models,history

def score(entries,models,cfg):
    records=[]
    for e in entries:
        m=motion(e,models[e['setup']])[0] if models else e['motion'];xy,h=integrate(e['data'],m);records.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(e['data'],xy,h,cfg)))
    return summarize(records),records

def audit(entries,models):
    e=next(e for e in entries if len(e['motion'])>600);q=models[e['setup']];m,z,r=motion(e,q);active=np.abs(r)<q['cap'];errors,jac=endpoint_data(e,m,z*active[:,0,None],z*active[:,1,None]);p=len(q['mean'])+1;indices=(0,p-1,p,p*2-1);results=[]
    for col in indices:
        direction=np.zeros((p,2));direction[col%p,col//p]=1;eps=1e-6;plus=dict(q,weights=q['weights']+eps*direction);minus=dict(q,weights=q['weights']-eps*direction);ep,_=endpoint_data(e,motion(e,plus)[0]);em,_=endpoint_data(e,motion(e,minus)[0]);numeric=-(ep-em)/(2*eps);analytic=jac[:,:,col];error=float(np.max(np.abs(numeric-analytic)))
        results.append(dict(parameter_column=col,max_absolute_derivative_error=error))
    return dict(record=e['row']['id'],finite_difference_step=1e-6,results=results,caveat='Numerical sensitivity audit away from clipping/angle branch boundaries; not a full-turn observability test.')

def main():
    out=ROOT/'outputs_motion_endpoint_iterative_v19'
    if out.exists():raise RuntimeError('Preserve iterative experiment')
    out.mkdir();started=time.perf_counter();torch.set_num_threads(4);parent=ROOT/'outputs_motion_endpoint_v16';run=json.loads((parent/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed v16 dependency '+name)
    train=load_training();source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD];(baseline,people,_),_=score(inner,{},cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates=[dict(damping=0.,iteration=0,score=baseline['equal_participant_mean_position_rmse_m'],worst_person_ratio=1.)];histories={}
    def callback(damping):
        def evaluate(models,iteration):
            (s,p,_),_=score(inner,models,cfg);row=dict(damping=damping,iteration=iteration,score=s['equal_participant_mean_position_rmse_m'],heading=s['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(a['mean_trial_position_rmse_m']/basepeople[a['participant']] for a in p));candidates.append(row);print('Fold',row,flush=True)
        return evaluate
    for damping in (.25,.5):_,histories[str(damping)]=run_iterations(fitrows,damping,callback(damping))
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),histories=histories,rule='Minimum equal-participant path RMSE with<=5% worst-person regression; conditional inherited pipeline fold'))
    # Refit chosen checkpoint; retain iterations after it only as training objective audit.
    captured={}
    def capture(models,iteration):
        if iteration==selected['iteration']:captured.update({k:dict(v) for k,v in models.items()})
    models,history=run_iterations(train,selected['damping'] or .25,capture);models=captured if selected['iteration'] else {};save_json(out/'refit_history.json',history);save_json(out/'jacobian_audit.json',audit(train,models or initialize(train)))
    initial=initialize(train);old=json.loads((parent/'model.json').read_text());maxdifference=max(float(np.max(np.abs(initial[k]['weights']-.5*np.array(old['fits'][k]['weights'])))) for k in initial)
    if maxdifference>1e-8:raise RuntimeError('v16 step1 coefficient reproduction failed')
    save_json(out/'model.json',dict(fits={k:{n:v.tolist() for n,v in q.items()} for k,q in models.items()},candidate=selected,training_ids=[e['row']['id'] for e in train],point_control_max_weight_difference=maxdifference,interpretation='Weights are TOTAL applied coefficients; cap is half v16 raw residual envelope; zero clipping sensitivity at saturated outputs'))
    # Prepare validation with frozen v14 state and exactly the cached feature family.
    from motion_endpoint_experiment_v16 import prepare
    from observed_ridge_inference import load_observed_ridge
    states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());manifest=json.loads((source/'artifact_manifest.json').read_text());validation=prepare(source,cfg,'validation',manifest,cal,load_observed_ridge(),states,out);summaries={}
    for name,fits in [('cpu_ridge',{}),('v16_step1',initial),('iterative',models)]:
        (s,p,c),records=score(validation,fits,cfg);summaries[name]=s
        for suffix,rows in [('trials',records),('participants',p),('maneuvers',c)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    if abs(summaries['v16_step1']['equal_participant_mean_position_rmse_m']-run['summary']['endpoint']['equal_participant_mean_position_rmse_m'])>1e-8:raise RuntimeError('v16 step1 score reproduction failed')
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=71,test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-started,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),parent/'artifact_manifest.json',ROOT/'stationary_gravity_experiment_v14.py',ROOT/'outputs_stationary_gravity_v14/artifact_manifest.json',ROOT/'motion_endpoint_experiment_v16.py']}))
    lines=['# Clipped iterative endpoint fit v19','','The first checkpoint is exactly the v16 applied model. Refinements update total forward/yaw coefficients with GaussNewton endpoint and masked-rate Jacobians, regularize total coefficients toward zero, and use training-only monotonic objective line search. Features remain frozen ridge features; clipping derivatives are zero at saturated channels.','',f'Fixed training-fold selection: {selected}','','| Method | Overall RMSE(mm) | Heading RMSE(degrees) |','|---|---:|---:|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} | {v["equal_participant_mean_heading_rmse_deg"]:.3f} |' for k,v in summaries.items()]+['','Five objective checkpoints and line-search steps are preserved for both damping values. Circular endpoint heading remains ambiguous across optical gaps. Initialization is IMU-only; inference uses one optical initial pose separately. No trajectory fitting at inference; no validation objective line search. All473 training and71 validation records; no test acquisitions read. Repeated validation remains exploratory, and inherited predictors/calibration saw the fixed inner training participants.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
