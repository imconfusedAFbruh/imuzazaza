"""Train-selected pivot translation correction; no heading/reference flipping."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from planar_experiment import lateral_labels
from trajectory_calibration_v10 import integrate
from controlled_motion_experiment_v25 import load_train,FOLDS,prepare_features,corrected,sensor
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from nonlinear_endpoint_experiment_v21 import nonlinear_features

GRID=[dict(name='control',kind='control',gain=0.,alpha=0.)]
GRID += [dict(name=k+'_0.5',kind=k,gain=.5,alpha=0.) for k in ('wheel','zero')]
GRID += [dict(name=f'learned_a{a}_g{g}',kind='learned',gain=g,alpha=a) for a in (.03,.3) for g in (.25,.5,1.)]

def inputs(d,m,c):
    t=d['t'];raw=d['raw'];w=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]]
    v=w.mean(1);yaw=(w[:,1]-w[:,0])/c['track_width_m'];ratio=1-np.abs(w.sum(1))/np.maximum(np.abs(w).sum(1),.05)
    gate=np.clip((ratio-.5)/.4,0,1)*np.clip((np.abs(yaw)-.3)/.7,0,1)*d['imu_valid']
    acc=raw[:,12:15]/c['accel_counts_per_g'][2]-np.array(c['center_gravity_direction']);gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale'])
    f=np.c_[acc,gyro,w,m,v,yaw,np.gradient(v,t),m[:,0]*m[:,2],m[:,1]*m[:,2]]
    x=np.c_[*[np.c_[*[np.interp(t+o,t,f[:,j]) for j in range(f.shape[1])]] for o in (-.25,0,.25)]]
    return dict(x=x,gate=gate,wheel_v=v)

def prepare(entries,cal,q):
    base=prepare_features(entries,cal,q['base'],False);result=[]
    c=q['selected'] if 'selected' in q else dict(slip_gain=.5,yaw_gain=0.,smooth=0.)
    for e in base:
        m=corrected(e,q['correction'],c);features=inputs(sensor(e['data']),m,cal[e['setup']]);side,valid=lateral_labels(e['data'])
        y=np.c_[e['data']['gt_v'],side]-m[:,:2];label=valid&e['data']['label_valid']&e['data']['imu_valid']&np.isfinite(y).all(1)
        result.append(dict(e,motion=m,target=y,label=label,**features))
    return result

def design(e,mean,std):return e['gate'][:,None]*np.c_[(e['x']-mean)/std,np.ones(len(e['x']))]

def endpoint_normal(e,mean,std):
    d=e['data'];m=e['motion'];z=design(e,mean,std);p=z.shape[1];t=d['t'];dt=np.diff(t);mids=(m[:-1]+m[1:])/2
    h=np.r_[0,np.cumsum(dt*mids[:,2])];hm=(h[:-1]+h[1:])/2;cs=np.cos(hm);sn=np.sin(hm);zm=(z[:-1]+z[1:])/2
    xy=np.vstack((np.zeros(2),np.cumsum(dt[:,None]*np.c_[mids[:,0]*cs-mids[:,1]*sn,mids[:,0]*sn+mids[:,1]*cs],axis=0)))
    jx=np.vstack((np.zeros(2*p),np.cumsum(dt[:,None]*np.c_[cs[:,None]*zm,-sn[:,None]*zm],axis=0)))
    jy=np.vstack((np.zeros(2*p),np.cumsum(dt[:,None]*np.c_[sn[:,None]*zm,cs[:,None]*zm],axis=0)))
    cov=np.zeros((2*p,2*p));rhs=np.zeros(2*p);n=0;bad=np.r_[0,np.cumsum(~d['imu_valid'])]
    for a in range(0,len(t),100):
        if not d['gt_valid'][a]:continue
        for hop in (100,300,500,1000):
            b=a+hop
            if b>=len(t) or not d['gt_valid'][b] or bad[b+1]!=bad[a]:continue
            ca,sa=np.cos(h[a]),np.sin(h[a]);rot=np.array([[ca,sa],[-sa,ca]]);pred=rot@(xy[b]-xy[a]);jac=rot@np.vstack((jx[b]-jx[a],jy[b]-jy[a]));g=d['gt_heading'][a]
            truth=np.array([[np.cos(g),np.sin(g)],[-np.sin(g),np.cos(g)]])@(d['gt_xy'][b]-d['gt_xy'][a]);duration=t[b]-t[a]
            jac/=duration;err=(truth-pred)/duration;cov+=jac.T@jac;rhs+=jac.T@err;n+=1
    return cov,rhs,n

def systems(entries):
    result={}
    for s in sorted({e['setup'] for e in entries}):
        es=[e for e in entries if e['setup']==s];xx=[];yy=[];gg=[]
        for e in es:
            ii=np.flatnonzero(e['label'])[::10];xx.append(e['x'][ii]);yy.append(e['target'][ii]);gg.extend([e['group']]*len(ii))
        x=np.concatenate(xx);y=np.concatenate(yy);counts=Counter(gg);weights=np.array([1/counts[g] for g in gg]);weights/=weights.sum();mean=np.sum(x*weights[:,None],0);std=np.maximum(np.sqrt(np.sum((x-mean)**2*weights[:,None],0)),1e-5)
        zz=[]
        for e in es:zz.append(design(e,mean,std)[np.flatnonzero(e['label'])[::10]])
        z=np.concatenate(zz);p=z.shape[1];point=z.T@(z*weights[:,None]);r=z.T@(y*weights[:,None]);cov=np.zeros((2*p,2*p));cov[:p,:p]=point;cov[p:,p:]=point;rhs=np.r_[r[:,0],r[:,1]]
        endpoint=[];ng=Counter()
        for e in es:
            c,rr,n=endpoint_normal(e,mean,std);endpoint.append((e['group'],c,rr,n));ng[e['group']]+=n
        good=sum(v>0 for v in ng.values())
        for group,c,rr,n in endpoint:
            if n:cov+=c/(good*ng[group]);rhs+=rr/(good*ng[group])
        active=np.concatenate([e['target'][e['label']&(e['gate']>.2)] for e in es]);cap=np.maximum(np.quantile(np.abs(active),.995,axis=0),[.03,.03]) if len(active) else np.array([.1,.1])
        result[s]=dict(mean=mean,std=std,cov=cov,rhs=rhs,cap=cap,pairs=sum(ng.values()))
        print('Rotation system',s,flush=True)
    return result

def fit(ss,alpha):
    result={}
    for s,q in ss.items():
        p=len(q['mean'])+1;reg=alpha*np.eye(2*p);reg[p-1,p-1]=0;reg[-1,-1]=0
        weight=np.linalg.solve(q['cov']+reg,q['rhs']);result[s]=dict(mean=q['mean'].tolist(),std=q['std'].tolist(),weights=np.c_[weight[:p],weight[p:]].tolist(),cap=q['cap'].tolist())
    return result

def predict(e,model,c):
    m=e['motion'].copy();gate=e['gate']*c['gain']
    if c['kind']=='wheel':m[:,0]=(1-gate)*m[:,0]+gate*e['wheel_v'];m[:,1]*=1-gate
    elif c['kind']=='zero':m[:,:2]*=(1-gate[:,None])
    elif c['kind']=='learned':
        q=model[e['setup']];z=design(e,np.array(q['mean']),np.array(q['std']));correction=np.clip(z@q['weights'],-np.array(q['cap']),np.array(q['cap']));m[:,:2]+=c['gain']*correction
    return m

def evaluate(entries,model,c,cfg,cache=None):
    rr=[]
    for e in entries:
        d=e['data'];m=predict(e,model,c);xy,h=integrate(d,m);rr.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(d,xy,h,cfg)))
        if cache:np.savez_compressed(cache/(e['row']['id']+'.npz'),t=d['t'],reference_xy=d['gt_xy'],reference_heading=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'],xy=xy,heading=h,motion=m,gate=e['gate'])
    return summarize(rr),rr

def main():
    started=time.perf_counter();torch.set_num_threads(4);out=ROOT/'outputs_rotation_motion_v29';parent=ROOT/'outputs_controlled_motion_v25'
    if out.exists():raise RuntimeError('Preserve old run')
    pm=json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    for name,h in pm.items():
        if digest(parent/name)!=h:raise RuntimeError('Changed v25 artifact '+name)
    out.mkdir();save_json(out/'predeclared_grid.json',dict(candidates=GRID,folds=[sorted(f) for f in FOLDS],scope='IMU-only counterrotation gate; no condition/person ID; no reference/heading flips. New coefficients exclude held people. Inherited calibration/neural base conditional.',selection='Minimum pooled12person trajectory RMSE with <=5% worstperson regression vs v25; control eligible'))
    train=load_train(ROOT/'outputs_motion_endpoint_v16');source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];records=[]
    for i,fold in enumerate(FOLDS):
        q=json.loads((parent/f'fold_{i}_model.json').read_text());fitting=[e for e in train if e['row']['participant'] not in fold];held=[e for e in train if e['row']['participant'] in fold]
        f=prepare(fitting,q['calibration'],q);h=prepare(held,q['calibration'],q);ss=systems(f);models={a:fit(ss,a) for a in (.03,.3)}
        save_json(out/f'fold_{i}_models.json',dict(models=models,fit_ids=[e['row']['id'] for e in fitting],held_people=sorted(fold)))
        for c in GRID:
            (s,_,_),r=evaluate(h,models.get(c['alpha'],{}),c,cfg);records.extend([dict(candidate=c['name'],fold=i,**v) for v in r]);print('fold',i,c['name'],s['equal_participant_mean_position_rmse_m'],flush=True)
    write_csv(out/'fold_trials.csv',records);control={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in records if r['candidate']=='control'])[1]};candidates=[]
    for c in GRID:
        s,p,_=summarize([r for r in records if r['candidate']==c['name']]);candidates.append(dict(c,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(v['mean_trial_position_rmse_m']/control[v['participant']] for v in p)))
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'selection.json',dict(selected=selected,candidates=candidates,selected_before_validation=True,test_evaluated=False))
    q=json.loads((parent/'model.json').read_text());entries=prepare(train,q['calibration'],q);models=fit(systems(entries),selected['alpha']) if selected['kind']=='learned' else {};save_json(out/'model.json',dict(candidate=selected,fits=models,training_ids=[e['row']['id'] for e in train],parent_manifest_sha256=digest(parent/'artifact_manifest.json')));del train,entries
    ridge=load_observed_ridge();states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};manifest=json.loads((source/'artifact_manifest.json').read_text());validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        m=ridge(sensor(d));x=feature_matrix(sensor(d),m,q['calibration'][row['setup']],states[row['id']],'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    entries=prepare(validation,q['calibration'],q);summary={}
    for name,c in [('control',GRID[0]),('selected',selected)]:
        cache=out/name/'trajectories';cache.mkdir(parents=True);(s,p,cond),r=evaluate(entries,models,c,cfg,cache);summary[name]=s
        for suffix,values in [('trials',r),('participants',p),('maneuvers',cond)]:write_csv(out/f'{name}_{suffix}.csv',values)
    save_json(out/'run.json',dict(summary=summary,selected=selected,test_evaluated=False,reference_amended=False,runtime_seconds=time.perf_counter()-started,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),parent/'artifact_manifest.json',ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',source/'artifact_manifest.json']}));save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
