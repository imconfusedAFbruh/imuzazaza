"""CPU gravity-initialized affine residual with coupled endpoint pose loss."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from learning import training_group
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix,correction,score as oldscore
from trajectory_calibration_v10 import integrate

FOLD={'No.3','No.8','No.15','No.20'};MODE='gravity_rotation';HORIZONS=(100,300,500,1000)

def endpoint_normal(e,mean,std):
    d=e['data'];m=e['motion'];z=np.c_[(e['x']-mean)/std,np.ones(len(m))];p=z.shape[1];t=d['t'];dt=np.diff(t);v=(m[1:]+m[:-1])/2;zm=(z[1:]+z[:-1])/2
    h=np.r_[0,np.cumsum(dt*v[:,2])];middle=(h[1:]+h[:-1])/2;c,s=np.cos(middle),np.sin(middle)
    qh=np.vstack((np.zeros(p),np.cumsum(dt[:,None]*zm,axis=0)));qm=(qh[1:]+qh[:-1])/2
    xy=np.vstack((np.zeros(2),np.cumsum(dt[:,None]*np.c_[v[:,0]*c-v[:,1]*s,v[:,0]*s+v[:,1]*c],axis=0)))
    px=np.vstack((np.zeros(2*p),np.cumsum(dt[:,None]*np.c_[c[:,None]*zm,(-s*v[:,0]-c*v[:,1])[:,None]*qm],axis=0)))
    py=np.vstack((np.zeros(2*p),np.cumsum(dt[:,None]*np.c_[s[:,None]*zm,(c*v[:,0]-s*v[:,1])[:,None]*qm],axis=0)))
    aa=[];yy=[];invalid=np.r_[0,np.cumsum(~d['imu_valid'])]
    for a in range(0,len(m),100):
        if not d['gt_valid'][a]:continue
        for horizon in HORIZONS:
            b=a+horizon
            if b>=len(m) or not d['gt_valid'][b] or invalid[b+1]!=invalid[a]:continue
            delta=xy[b]-xy[a];ca,sa=np.cos(h[a]),np.sin(h[a]);rot=np.array([[ca,sa],[-sa,ca]]);pred=np.r_[rot@delta,h[b]-h[a]]
            js=np.zeros((3,2*p));js[:2]=rot@np.vstack((px[b]-px[a],py[b]-py[a]));dh=np.r_[np.zeros(p),qh[a]]
            js[:2]+=np.array([pred[1],-pred[0]])[:,None]*dh[None,:];js[2,p:]=qh[b]-qh[a]
            h0=d['gt_heading'][a];delta_gt=d['gt_xy'][b]-d['gt_xy'][a];target=np.r_[np.array([[np.cos(h0),np.sin(h0)],[-np.sin(h0),np.cos(h0)]])@delta_gt,d['gt_heading'][b]-h0]
            err=target-pred;err[2]=np.arctan2(np.sin(err[2]),np.cos(err[2]));duration=t[b]-t[a];aa.append(js/duration);yy.append(err/duration)
    if not aa:return np.zeros((2*p,2*p)),np.zeros(2*p),0
    a=np.array(aa).reshape(-1,2*p);y=np.array(yy).reshape(-1);return a.T@a,a.T@y,len(aa)

def normal_system(entries):
    systems={}
    for setup in sorted({e['setup'] for e in entries}):
        es=[e for e in entries if e['setup']==setup];xs=[];ys=[];groups=[]
        for e in es:
            ids=np.flatnonzero(e['label'])[::10];xs.append(e['x'][ids]);ys.append(e['target'][ids]);groups.extend([e['group']]*len(ids))
        x=np.concatenate(xs).astype(float);y=np.concatenate(ys);counts=Counter(groups);w=np.array([1/counts[g] for g in groups]);w/=w.sum();mean=np.sum(x*w[:,None],axis=0);std=np.maximum(np.sqrt(np.sum((x-mean)**2*w[:,None],axis=0)),1e-5);z=np.c_[(x-mean)/std,np.ones(len(x))];p=z.shape[1];cov=z.T@(z*w[:,None]);rhs=z.T@(y*w[:,None]);point=np.zeros((2*p,2*p));point[:p,:p]=cov;point[p:,p:]=cov;right=np.r_[rhs[:,0],rhs[:,1]]
        endpoint=[];groupcounts=Counter()
        for e in es:
            ec,er,n=endpoint_normal(e,mean,std);endpoint.append((e['group'],ec,er,n));groupcounts[e['group']]+=n
        ce=np.zeros_like(point);re=np.zeros(2*p);goodgroups=sum(n>0 for n in groupcounts.values())
        for group,c,r,n in endpoint:
            if n:ce+=c/(goodgroups*groupcounts[group]);re+=r/(goodgroups*groupcounts[group])
        systems[setup]=dict(mean=mean,std=std,point=point,rhs=right,endpoint=ce,endpoint_rhs=re,cap=np.maximum(np.quantile(np.abs(y),.995,axis=0),[.02,.01]),endpoint_pairs=sum(groupcounts.values()),samples=len(x))
        print('Built normal system',setup,'pairs',sum(groupcounts.values()),flush=True)
    return systems

def fit(systems,alpha,endpoint_weight):
    fits={}
    for setup,q in systems.items():
        p=len(q['mean'])+1;reg=alpha*np.eye(2*p);reg[p-1,p-1]=0;reg[-1,-1]=0
        coef=np.linalg.solve(q['point']+endpoint_weight*q['endpoint']+reg,q['rhs']+endpoint_weight*q['endpoint_rhs']);weights=np.c_[coef[:p],coef[p:]]
        fits[setup]=dict(mean=q['mean'].tolist(),std=q['std'].tolist(),weights=weights.tolist(),cap=q['cap'].tolist(),endpoint_pairs=q['endpoint_pairs'],samples=q['samples'])
    return fits

def score(entries,fits,candidate,cfg):
    adapted=[dict(e,x={MODE:e['x']}) for e in entries]
    return oldscore(adapted,fits,dict(candidate,mode=MODE),cfg)

def prepare(source,cfg,partition,manifest,cal,ridge,states,out):
    entries=[]
    for row,d,_ in observed_rows(source,cfg,partition,manifest):
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(sensor);state=states[row['id']]
        if state['partition']!=partition or state['setup']!=row['setup']:raise RuntimeError('Initialization partition differs')
        x=feature_matrix(sensor,m,cal[row['setup']],state,MODE);label=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw']);target=np.c_[d['gt_v'],d['gt_yaw']]-m[:,[0,2]]
        entries.append(dict(row=row,data=d,motion=m,target=target,label=label,x=x,setup=row['setup'],group=training_group(row)))
        if partition=='train':
            path=out/'prepared_training'/(row['id']+'.npz');np.savez_compressed(path,**d,features=x,ridge_motion=m,residual_target=target,residual_label_valid=label)
            save_json(path.with_suffix('.json'),dict(row=row,initialization=state,source_cache_sha256=digest(source/'cache'/(row['id']+'.npz')),initialization_manifest_sha256=digest(ROOT/'outputs_stationary_gravity_v14/artifact_manifest.json'),feature_source_sha256=digest(ROOT/'stationary_gravity_experiment_v14.py'),feature_mode=MODE,note='Prepared training data includes masked reference targets. Features and ridge motion derive only from IMU/startup initialization. No validation records cached here.'))
        if len(entries)%50==0:print('Prepared',partition,len(entries),flush=True)
    return entries

def main():
    started=time.perf_counter();out=ROOT/'outputs_motion_endpoint_v16';parent=ROOT/'outputs_stationary_gravity_v14'
    if out.exists():raise RuntimeError('Preserve endpoint experiment')
    out.mkdir();(out/'prepared_training').mkdir();torch.set_num_threads(4)
    if torch.cuda.is_available():raise RuntimeError('Paired CPU required')
    for name,sha in json.loads((parent/'artifact_manifest.json').read_text())['sha256'].items():
        if digest(parent/name)!=sha:raise RuntimeError('Changed v14 artifact '+name)
    parentrun=json.loads((parent/'run.json').read_text())
    for name,sha in parentrun['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed v14 source '+name)
    states={r['id']:r for r in json.loads((parent/'initialization.json').read_text())['records']};source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge();train=prepare(source,cfg,'train',manifest,cal,ridge,states,out);inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD]
    zero=dict(alpha=0.,endpoint_weight=0.,gain=0.);(baseline,people,_),_=score(inner,{},zero,cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates=[dict(zero,score=baseline['equal_participant_mean_position_rmse_m'],worst_person_ratio=1.)];systems=normal_system(fitrows)
    for alpha in (.1,1.,10.):
        for ew in (0.,.3,1.):
            fits=fit(systems,alpha,ew)
            for gain in (.25,.5):
                c=dict(alpha=alpha,endpoint_weight=ew,gain=gain);(summary,ppl,_),_=score(inner,fits,c,cfg);c.update(score=summary['equal_participant_mean_position_rmse_m'],heading=summary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in ppl));candidates.append(c);print('Fold',c,flush=True)
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),rule='Minimum equal-participant path RMSE with <=5% worst-person regression; unchanged ridge eligible',caveat='Inherited base/calibration previously saw these training participants; conditional correction selection.'))
    systems=normal_system(train);fits=fit(systems,selected['alpha'],selected['endpoint_weight']) if selected['gain'] else {};pointfits=fit(systems,.1,0.)
    # Reproduce v14 derivative-only coefficient and normalization fit before validation.
    old=json.loads((parent/'model.json').read_text());maxweight=max(np.max(np.abs(np.array(pointfits[k]['weights'])-old['fits'][k]['weights'])) for k in pointfits)
    if maxweight>1e-6:raise RuntimeError('Derivative-only v14 weights differ')
    save_json(out/'model.json',dict(fits=fits,candidate=dict(selected,mode=MODE),training_ids=[e['row']['id'] for e in train],feature_schema='Exactly v14 gravity_rotation features; forward/yaw residual channels coupled by linearized observed-endpoint SE2 equations; lateral fixed ridge',point_control_max_weight_difference=float(maxweight)))
    del train,inner,fitrows,systems
    validation=prepare(source,cfg,'validation',manifest,cal,ridge,states,out);summaries={};pointcandidate=dict(alpha=.1,endpoint_weight=0.,gain=.25)
    for name,f,c in [('cpu_ridge',{},zero),('v14_point',pointfits,pointcandidate),('endpoint',fits,selected)]:
        (summary,ppl,conditions),records=score(validation,f,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',ppl),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    if abs(summaries['v14_point']['equal_participant_mean_position_rmse_m']-parentrun['summary']['stationary_gravity']['equal_participant_mean_position_rmse_m'])>1e-8:raise RuntimeError('v14 paired reproduction differs')
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=len(validation),test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-started,point_control_max_weight_difference=float(maxweight),provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'stationary_gravity_experiment_v14.py',parent/'artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json',ROOT/'observed_ridge_inference.py']}))
    lines=['# Observed-endpoint gravity-initialized motion fit v16','','Exactly the v14 per-record initial gravity/bias feature family. Coupled affine forward/yaw correction fits masked derivative point labels plus first-order relative SE2 endpoint residuals at1/3/5/10seconds. Intermediate optical gaps are not filled; endpoint pair inputs require uninterrupted IMUs. Circular heading residuals do not determine hidden full-turn counts.','',f'Fixed-fold selection: {selected}','','| Model | Overall RMSE(mm) | Heading RMSE(degrees) |','|---|---:|---:|---:|']+[f'| {k} | {s["equal_participant_mean_position_rmse_m"]*1000:.3f} | {s["equal_participant_mean_heading_rmse_deg"]:.3f} |' for k,s in summaries.items()]+['','Derivative-only coefficient/normalization fit and v14 scores were reproduced before comparison. All473 prepared training feature/target records are cached with source and initialization hashes. Per-record startup state is IMU-only; inference never looks up participant IDs or optical labels. Lateral channel remains exactly ridge. Full mounting rotation is not established: gravity only determines tilt, leaves mounting yaw unknown, and the stationarity candidates are empirical. An all-maneuver aggregate gain does not independently validate sensor encoding, lever arms or optical reference accuracy. Reused validation remains exploratory; no test acquisitions read. First-order endpoint linearization and clipping/damped gain are approximations, not trajectory fitting at inference.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
