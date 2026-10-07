"""Observed-only coupled forward/lateral/yaw interval residual experiment.

Conditional training participant selection; inherited base and calibration remain
fixed. No processed supervision, reference-conditioned inference or test access.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted,nonlinear_features,FOLD
from motion_endpoint_experiment_v16 import normal_system as original_system,fit as original_fit,score as original_score
from stationary_gravity_experiment_v14 import feature_matrix,correction
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from planar_experiment import lateral_labels
from trajectory_calibration_v10 import integrate

OUT=ROOT/'outputs_joint_planar_v35'
GRID=[dict(name=f'joint_lreg{str(r).replace(".","p")}_lgain{str(g).replace(".","p")}',forward_yaw_alpha=.1,lateral_alpha=r,endpoint_weight=1.,gain=[.5,g,.5]) for r in (.3,1.) for g in (.25,.5)]
HORIZONS=(100,300,500,1000)

def lateral_entry(e):
    lateral,valid=lateral_labels(e['data'])
    valid&=e['data']['imu_valid']&np.isfinite(lateral)&np.isfinite(e['motion'][:,1])
    return dict(e,lateral_label=valid,lateral_target=lateral-e['motion'][:,1])

def endpoint_arrays(e,mean,std):
    d=e['data'];m=e['motion'];z=np.c_[(e['x']-mean)/std,np.ones(len(m))];p=z.shape[1];t=d['t'];dt=np.diff(t)
    vm=(m[1:]+m[:-1])/2;zm=(z[1:]+z[:-1])/2
    h=np.r_[0,np.cumsum(dt*vm[:,2])];middle=(h[1:]+h[:-1])/2;c,s=np.cos(middle),np.sin(middle)
    qh=np.vstack((np.zeros(p),np.cumsum(dt[:,None]*zm,axis=0)));qm=(qh[1:]+qh[:-1])/2
    xy=np.vstack((np.zeros(2),np.cumsum(dt[:,None]*np.c_[vm[:,0]*c-vm[:,1]*s,vm[:,0]*s+vm[:,1]*c],axis=0)))
    # Parameter order is forward[p], lateral[p], yaw[p]. Body lateral motion is
    # included in yaw sensitivity; omitting it biases the turn equations.
    px=np.vstack((np.zeros(3*p),np.cumsum(dt[:,None]*np.c_[c[:,None]*zm,-s[:,None]*zm,(-s*vm[:,0]-c*vm[:,1])[:,None]*qm],axis=0)))
    py=np.vstack((np.zeros(3*p),np.cumsum(dt[:,None]*np.c_[s[:,None]*zm,c[:,None]*zm,(c*vm[:,0]-s*vm[:,1])[:,None]*qm],axis=0)))
    aa=[];yy=[];pairs=[];invalid=np.r_[0,np.cumsum(~d['imu_valid'])]
    for a in range(0,len(m),100):
        if not d['gt_valid'][a]:continue
        for horizon in HORIZONS:
            b=a+horizon
            if b>=len(m) or not d['gt_valid'][b] or invalid[b+1]!=invalid[a]:continue
            delta=xy[b]-xy[a];ca,sa=np.cos(h[a]),np.sin(h[a]);rot=np.array([[ca,sa],[-sa,ca]])
            pred=np.r_[rot@delta,h[b]-h[a]]
            js=np.zeros((3,3*p));js[:2]=rot@np.vstack((px[b]-px[a],py[b]-py[a]))
            # Relative-start-frame rotation depends on yaw correction before a.
            js[:2,2*p:]+=np.array([pred[1],-pred[0]])[:,None]*qh[a][None,:]
            js[2,2*p:]=qh[b]-qh[a]
            h0=d['gt_heading'][a];delta_gt=d['gt_xy'][b]-d['gt_xy'][a]
            target=np.r_[np.array([[np.cos(h0),np.sin(h0)],[-np.sin(h0),np.cos(h0)]])@delta_gt,d['gt_heading'][b]-h0]
            err=target-pred;err[2]=np.arctan2(np.sin(err[2]),np.cos(err[2]));duration=t[b]-t[a]
            aa.append(js/duration);yy.append(err/duration);pairs.append((a,b))
    return np.array(aa).reshape(-1,3,3*p),np.array(yy).reshape(-1,3),pairs,z

def joint_system(entries):
    systems={}
    for setup in sorted({e['setup'] for e in entries}):
        es=[e for e in entries if e['setup']==setup];xs=[];ys=[];groups=[]
        for e in es:
            ids=np.flatnonzero(e['label'])[::10];xs.append(e['x'][ids]);ys.append(e['target'][ids]);groups.extend([e['group']]*len(ids))
        x=np.concatenate(xs).astype(float);y=np.concatenate(ys);counts=Counter(groups);w=np.array([1/counts[g] for g in groups]);w/=w.sum()
        # Exact original v21 forward/yaw normalization and point equations.
        mean=np.sum(x*w[:,None],axis=0);std=np.maximum(np.sqrt(np.sum((x-mean)**2*w[:,None],axis=0)),1e-5)
        z=np.c_[(x-mean)/std,np.ones(len(x))];p=z.shape[1];cov=z.T@(z*w[:,None]);rhs=z.T@(y*w[:,None])
        point=np.zeros((3*p,3*p));right=np.zeros(3*p);point[:p,:p]=cov;point[2*p:,2*p:]=cov;right[:p]=rhs[:,0];right[2*p:]=rhs[:,1]
        lx=[];ly=[];lg=[]
        for e in es:
            ids=np.flatnonzero(e['lateral_label'])[::10];lx.append(e['x'][ids]);ly.append(e['lateral_target'][ids]);lg.extend([e['group']]*len(ids))
        lx=np.concatenate(lx).astype(float);ly=np.concatenate(ly);lc=Counter(lg);lw=np.array([1/lc[g] for g in lg]);lw/=lw.sum()
        lz=np.c_[(lx-mean)/std,np.ones(len(lx))];point[p:2*p,p:2*p]=lz.T@(lz*lw[:,None]);right[p:2*p]=lz.T@(ly*lw)
        endpoints=[];gc=Counter()
        for e in es:
            ae,ye,pairs,_=endpoint_arrays(e,mean,std);a=ae.reshape(-1,3*p);yy=ye.reshape(-1);n=len(pairs)
            endpoints.append((e['group'],a.T@a,a.T@yy,n));gc[e['group']]+=n
        ce=np.zeros_like(point);re=np.zeros_like(right);good=sum(n>0 for n in gc.values())
        for group,c,r,n in endpoints:
            if n:ce+=c/(good*gc[group]);re+=r/(good*gc[group])
        oldcap=np.maximum(np.quantile(np.abs(y),.995,axis=0),[.02,.01]);latcap=max(float(np.quantile(np.abs(ly),.995)),.01)
        systems[setup]=dict(mean=mean,std=std,point=point,rhs=right,endpoint=ce,endpoint_rhs=re,cap=np.array([oldcap[0],latcap,oldcap[1]]),endpoint_pairs=sum(gc.values()),point_samples=len(x),lateral_samples=len(lx))
        print('Joint normal system',setup,'endpoints',sum(gc.values()),'lateral samples',len(lx),flush=True)
    return systems

def joint_fit(systems,candidate):
    fits={}
    for setup,q in systems.items():
        p=len(q['mean'])+1;reg=np.diag(np.repeat([candidate['forward_yaw_alpha'],candidate['lateral_alpha'],candidate['forward_yaw_alpha']],p))
        for j in range(3):reg[(j+1)*p-1,(j+1)*p-1]=0
        coef=np.linalg.solve(q['point']+candidate['endpoint_weight']*q['endpoint']+reg,q['rhs']+candidate['endpoint_weight']*q['endpoint_rhs'])
        fits[setup]=dict(mean=q['mean'].tolist(),std=q['std'].tolist(),weights=np.c_[coef[:p],coef[p:2*p],coef[2*p:]].tolist(),cap=q['cap'].tolist(),endpoint_pairs=q['endpoint_pairs'],point_samples=q['point_samples'],lateral_samples=q['lateral_samples'])
    return fits

def predict_motion(e,model):
    m=e['motion'].copy();fit=model['fits'][e['setup']];x=e['x'];z=np.c_[(x-fit['mean'])/fit['std'],np.ones(len(x))]
    residual=np.clip(z@np.array(fit['weights']),-np.array(fit['cap']),np.array(fit['cap']))
    return m+residual*np.array(model['candidate']['gain'])

def evaluate(entries,model,cfg,save=False):
    records=[];predictions={}
    for e in entries:
        m=predict_motion(e,model);xy,h=integrate(e['data'],m)
        records.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(e['data'],xy,h,cfg)))
        if save:predictions[e['row']['id']]=dict(xy_m=xy,heading_rad=h,motion=m)
    return summarize(records),records,predictions

def original_model(e,model):
    return correction(dict(e,x={'gravity_rotation':e['x']}),model['fits'],dict(model['candidate'],mode='gravity_rotation'))

def main():
    started=time.perf_counter();torch.set_num_threads(4)
    if OUT.exists():raise RuntimeError('Preserve previous joint run')
    OUT.mkdir();(OUT/'trajectories').mkdir()
    oldmodel=json.loads((ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text());oldcandidate={k:oldmodel['candidate'][k] for k in ('basis','alpha','endpoint_weight','gain')}
    save_json(OUT/'predeclared_grid.json',dict(candidates=GRID,control='original_v21',fold=sorted(FOLD),selection='Lowest conditional training fold equal-participant RMSE, <=5% worst-person regression versus original v21 fitted on the same subset; control eligible.',features=115,normalization='Exact v21 point-label-weighted fitting-subset mean/std; original physical-product clipping.',labels='Original observed derivatives/endpoints only, lateral own observed gap-boundary mask.',channels=['forward','lateral','yaw'],base_refitted=False,calibration_refitted=False,test_accessed=False))
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings']
    train=[lateral_entry(e) for e in load_train(ROOT/'outputs_motion_endpoint_v16')]
    inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD]
    clips=bounds(fitrows);fitting=adapted(fitrows,'physical_products',clips);held=adapted(inner,'physical_products',clips)
    ofit=original_fit(original_system(fitting),.1,1.)
    (osummary,oppl,_),orecords=original_score(held,ofit,oldcandidate,cfg);obase={q['participant']:q['mean_trial_position_rmse_m'] for q in oppl}
    candidates=[dict(name='original_v21',score=osummary['equal_participant_mean_position_rmse_m'],heading=osummary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=1.)]
    foldrows=[dict(model='original_v21',**r) for r in orecords];systems=joint_system(fitting)
    for c in GRID:
        model=dict(candidate=c,fits=joint_fit(systems,c));(summary,ppl,_),records,_=evaluate(held,model,cfg)
        result=dict(c,score=summary['equal_participant_mean_position_rmse_m'],heading=summary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(q['mean_trial_position_rmse_m']/obase[q['participant']] for q in ppl));candidates.append(result);foldrows.extend([dict(model=c['name'],**r) for r in records]);print('Fold',result,flush=True)
    selected=min([q for q in candidates if q['worst_person_ratio']<=1.05],key=lambda q:q['score'])
    save_json(OUT/'selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),caveat='Inherited base/calibration saw these inner participants; conditional correction comparison, not independent full-pipeline participant evaluation.'));write_csv(OUT/'fold_trials.csv',foldrows)
    clips=bounds(train);fitting=adapted(train,'physical_products',clips);systems=joint_system(fitting);models={}
    for c in GRID:
        models[c['name']]=dict(candidate=c,fits=joint_fit(systems,c),feature_clip=clips,feature_count=115,training_ids=[e['row']['id'] for e in train]);save_json(OUT/(c['name']+'_model.json'),models[c['name']])
    training_people={e['row']['participant'] for e in train};del train,inner,fitrows,fitting,held,systems
    states={q['id']:q for q in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());manifest=json.loads((source/'artifact_manifest.json').read_text());ridge=load_observed_ridge();validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        if row['participant'] in training_people:raise RuntimeError('Participant leakage')
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(sensor);state=states[row['id']]
        if state['partition']!='validation' or state['setup']!=row['setup']:raise RuntimeError('Startup partition differs')
        x=feature_matrix(sensor,m,cal[row['setup']],state,'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    oldentries=adapted(validation,'physical_products',oldmodel['feature_clip']);control=[];caches={};max_delta=0.
    for e in oldentries:
        d=e['data'];m=original_model(e,oldmodel);xy,h=integrate(d,m);rid=e['row']['id'];control.append(dict(id=rid,participant=e['row']['participant'],condition=e['row']['condition'],**metrics(d,xy,h,cfg)))
        with np.load(ROOT/'outputs_recovered_training_v32/trajectories'/(rid+'.npz')) as prior:
            max_delta=max(max_delta,float(np.nanmax(np.abs(xy-prior['original_v21_xy_m']))))
            if not np.array_equal(d['gt_valid'],prior['reference_valid']):raise RuntimeError('Observed validation mask differs')
        caches[rid]=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'],original_v21_xy_m=xy,original_v21_heading_rad=h,original_v21_motion=m)
    if max_delta>1e-10:raise RuntimeError('Original v21 prediction reproduction differs')
    summaries={};summaries['original_v21'],ppl,conditions=summarize(control)
    for suffix,records in [('trials',control),('participants',ppl),('maneuvers',conditions)]:write_csv(OUT/('original_v21_'+suffix+'.csv'),records)
    entries=adapted(validation,'physical_products',clips)
    for name,model in models.items():
        (summary,ppl,conditions),records,predictions=evaluate(entries,model,cfg,save=True);summaries[name]=summary
        for suffix,rs in [('trials',records),('participants',ppl),('maneuvers',conditions)]:write_csv(OUT/(name+'_'+suffix+'.csv'),rs)
        for rid,pred in predictions.items():caches[rid].update({name+'_'+k:v for k,v in pred.items()})
    for rid,arrays in caches.items():np.savez_compressed(OUT/'trajectories'/(rid+'.npz'),**arrays)
    run=dict(summary=summaries,selected=selected,training_trials=473,validation_trials=71,validation_participants=4,base_refitted=False,calibration_refitted=False,processed_labels_used=False,test_accessed=False,original_v21_max_position_difference_m=max_delta,runtime_seconds=time.perf_counter()-started,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'outputs_nonlinear_endpoint_v21/model.json',ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/split.json']})
    save_json(OUT/'run.json',run)
    lines=['# Joint planar interval correction v35','','All473 accepted training recordings; observed labels only. Exact original115features, clipping and forward/yaw point normalization. Lateral point labels have their own observed-boundary mask. Full3-channel interval Jacobian includes body-lateral terms in yaw sensitivity and the derivative of interval-start yaw.','',f'Training-fold selected: {selected}','','| Model | Validation RMSE(mm) | Heading(deg) |','|---|---:|---:|']+[f'| {n} | {q["equal_participant_mean_position_rmse_m"]*1000:.3f} | {q["equal_participant_mean_heading_rmse_deg"]:.3f} |' for n,q in summaries.items()]+['','Selection uses No.3/8/15/20 training participants and <=5% worst-person regression against the same-subset original control. The inherited base/calibration saw these inner participants: conditional comparison only. The71validation trajectories were previously exposed; no new independent test claim. First-order endpoint linearization and channel gains are approximations. AlloriginalC3Ds, masks, models and previous outputs remain unchanged; no optical position or heading updates occur at inference.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(run,indent=2),flush=True)

if __name__=='__main__':main()
