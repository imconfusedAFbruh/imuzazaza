"""Controlled IMU-only braking, quiet-yaw-state and dynamics-smoothing comparisons.

Two branches: conditional frozen neural base; independently refitted empirical
calibration and motion model. Both retain the fixed benchmark clocks/QC/reference.
No test acquisition is read. No factory SI, full attitude or tire-slip claim.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import argparse,json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from scipy.ndimage import uniform_filter1d
from scipy.linalg import solve_banded
from pipeline import ROOT,save_json,write_csv,digest,metrics,summarize,calibrate,velocities,runs
from learning import training_group
from nonlinear_endpoint_experiment_v21 import load_train,nonlinear_features,bounds,adapted
from motion_endpoint_experiment_v16 import normal_system,fit
from participant_folds_experiment_v24 import FOLDS
from stationary_gravity_experiment_v14 import feature_matrix
from planar_experiment import lateral_labels
from trajectory_calibration_v10 import integrate
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge

BASE=dict(basis='physical_products',alpha=.3,endpoint_weight=1.,gain=.25)
GRID=[dict(name='control',slip_gain=0.,yaw_gain=0.,smooth=0.)]
GRID += [dict(name=f'braking_{g}',slip_gain=g,yaw_gain=0.,smooth=0.) for g in (.25,.5)]
GRID += [dict(name=f'yaw_state_{g}',slip_gain=0.,yaw_gain=g,smooth=0.) for g in (.25,.5)]
GRID += [dict(name=f'combined_{lam}',slip_gain=.25,yaw_gain=.25,smooth=lam) for lam in (.0001,.001,.01)]

def sensor(d):return {k:d[k] for k in ('setup','t','raw','imu_valid')}

def predict_affine(e,model,gain=.25):
    m=e['motion'].copy();s=e['setup'];q=model['fits'][s];clips=model['feature_clip'][s]
    x=np.c_[e['linear'],np.clip(e['nonlinear'][:,75:],clips['low'],clips['high'])]
    z=np.c_[(x-q['mean'])/q['std'],np.ones(len(x))]
    m[:,[0,2]]+=gain*np.clip(z@q['weights'],-np.array(q['cap']),np.array(q['cap']))
    return m

def basic_features(d,m,c):
    t=d['t'];raw=d['raw'];acc=raw[:,12:15]/c['accel_counts_per_g'][2]-np.array(c['center_gravity_direction'])
    gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale'])
    wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]]
    wheel_v=wheel.mean(1);dv=np.gradient(wheel_v,t);conflict=(wheel[:,1]-wheel[:,0])/c['track_width_m']-m[:,2]
    # Gate is continuous, IMU-only and identical across maneuvers/participants.
    brake=np.clip(-dv/.5,0,1);stopped=np.clip(1-np.abs(wheel_v)/.15,0,1)
    f=np.c_[acc,gyro,wheel_v,dv,conflict,m[:,0],m[:,2],brake,stopped,brake[:,None]*acc,stopped[:,None]*acc,brake*dv]
    x=np.c_[*[np.c_[*[np.interp(t+o,t,f[:,j]) for j in range(f.shape[1])]] for o in (-.5,0.,.5)]]
    return x.astype(np.float32),np.c_[acc,gyro,wheel_v,dv,m[:,0],m[:,2]],(brake>.25).astype(int),wheel

def quiet_yaw_state(d,m,c,wheel):
    t=d['t'];raw=d['raw'];acc=raw[:,12:15]/c['accel_counts_per_g'][2]
    gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale'])
    state=np.zeros(len(t));quiet=np.zeros(len(t),bool)
    for a,b in runs(d['imu_valid']):
        if b-a<200:continue
        spread=np.sqrt(np.maximum(uniform_filter1d(acc[a:b]**2,101,axis=0)-uniform_filter1d(acc[a:b],101,axis=0)**2,0))
        norm=np.linalg.norm(acc[a:b],axis=1)
        gate=(np.max(np.abs(wheel[a:b]),axis=1)<.03)&(np.linalg.norm(gyro[a:b],axis=1)<.08)&(np.max(spread,axis=1)<.015)&(norm>.9)&(norm<1.1)
        gate[:50]=False;gate[-50:]=False;knots=[];vals=[]
        for qa,qb in runs(gate):
            if qb-qa<150:continue
            quiet[a+qa:a+qb]=True
            knots.append(float(np.median(t[a+qa:a+qb])))
            # Correct model-output zero-rate offset, not refit sensor calibration.
            vals.append(float(np.clip(np.median(m[a+qa:a+qb,2]),-.02,.02)))
        if knots:
            dt=np.min(np.abs(t[a:b,None]-np.array(knots)[None,:]),axis=1)
            state[a:b]=np.interp(t[a:b],knots,vals)*np.exp(-dt/10.)
    return state,dict(quiet_seconds=float(quiet.sum()/100),eligible=bool(quiet.any()))

def constrained_slip_fit(entries):
    systems=normal_system(entries);models={}
    for s,q in systems.items():
        p=len(q['mean'])+1;reg=.3*np.eye(p);reg[-1,-1]=0
        weight=np.linalg.solve(q['point'][:p,:p]+q['endpoint'][:p,:p]+reg,q['rhs'][:p]+q['endpoint_rhs'][:p])
        models[s]=dict(mean=q['mean'].tolist(),std=q['std'].tolist(),weights=weight.tolist(),cap=float(q['cap'][0]))
    return models

def slip_prediction(e,model):
    q=model[e['setup']];z=np.c_[(e['x']-q['mean'])/q['std'],np.ones(len(e['x']))]
    return np.clip(z@q['weights'],-q['cap'],q['cap'])

def auxiliary_fit(entries,slip):
    result={}
    for s in sorted({e['setup'] for e in entries}):
        es=[e for e in entries if e['setup']==s];xx=[];yy=[];groups=[]
        for e in es:
            d=e['data'];accel=np.full(len(d['t']),np.nan)
            for a,b in runs(e['label']):
                if b-a<10:continue
                accel[a+2:b-2]=np.gradient(d['gt_v'][a:b],d['t'][a:b])[2:-2]
            ids=np.flatnonzero(np.isfinite(accel))[::10]
            xx.append(e['ax'][ids]);yy.append(accel[ids]);groups.extend([e['group']]*len(ids))
        x=np.concatenate(xx);y=np.concatenate(yy);counts=Counter(groups);w=np.array([1/counts[g] for g in groups]);w/=w.sum()
        mean=np.sum(x*w[:,None],axis=0);std=np.maximum(np.sqrt(np.sum((x-mean)**2*w[:,None],axis=0)),1e-5);z=np.c_[(x-mean)/std,np.ones(len(x))];reg=.3*np.eye(z.shape[1]);reg[-1,-1]=0
        coef=np.linalg.solve(z.T@(z*w[:,None])+reg,z.T@(y*w));cap=max(float(np.quantile(np.abs(y),.995)),.1)
        errors=[[],[]];aerrors=[[],[]]
        for e in es:
            d=e['data'];accel=np.full(len(d['t']),np.nan)
            for a,b in runs(e['label']):
                if b-a>=10:accel[a+2:b-2]=np.gradient(d['gt_v'][a:b],d['t'][a:b])[2:-2]
            pred=np.clip(np.c_[(e['ax']-mean)/std,np.ones(len(e['ax']))]@coef,-cap,cap)
            ve=d['gt_v']-(e['motion'][:,0]+.25*slip_prediction(e,slip))
            for k in (0,1):
                mask=e['label']&(e['regime']==k)&np.isfinite(ve)&np.isfinite(accel)
                errors[k].extend(ve[mask][::10].tolist());aerrors[k].extend((accel-pred)[mask][::10].tolist())
        vvar=[max(float(np.mean(np.square(v))),.0025) if v else .04 for v in errors]
        avar=[max(float(np.mean(np.square(v))),.04) if v else 1. for v in aerrors]
        result[s]=dict(mean=mean.tolist(),std=std.tolist(),coef=coef.tolist(),cap=cap,vvar=vvar,avar=avar,variance_scope='In-fit residual second moments; heuristic confidence, not held-out calibrated covariance')
    return result

def smoothing(d,m,e,q,lam):
    n=len(m);a=np.clip(np.c_[(e['ax']-q['mean'])/q['std'],np.ones(n)]@q['coef'],-q['cap'],q['cap']);out=m.copy()
    for start,end in runs(d['imu_valid']):
        if end-start<3:continue
        v=m[start:end,0];dt=np.diff(d['t'][start:end]);r=e['regime'][start:end]
        precision=1/np.array(q['vvar'])[r];av=(np.array(q['avar'])[r[:-1]]+np.array(q['avar'])[r[1:]])/2
        edge=lam/(dt**2*av);diff_target=dt*(a[start:end-1]+a[start+1:end])/2
        diag=precision.copy();diag[:-1]+=edge;diag[1:]+=edge
        rhs=precision*v;rhs[:-1]-=edge*diff_target;rhs[1:]+=edge*diff_target
        band=np.zeros((3,len(v)));band[1]=diag;band[0,1:]=-edge;band[2,:-1]=-edge
        out[start:end,0]=solve_banded((1,1),band,rhs)
    return out

def corrected(e,model,c):
    m=e['motion'].copy()
    if c['slip_gain']:m[:,0]+=c['slip_gain']*slip_prediction(e,model['slip'])
    if c['yaw_gain']:m[:,2]-=c['yaw_gain']*e['yaw_state']
    if c['smooth']:m=smoothing(e['data'],m,e,model['aux'][e['setup']],c['smooth'])
    return m

def evaluate(entries,model,c,cfg,cache=None):
    rr=[]
    for e in entries:
        m=corrected(e,model,c);xy,h=integrate(e['data'],m);d=e['data']
        rr.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(d,xy,h,cfg)))
        if cache is not None:
            np.savez_compressed(cache/(e['row']['id']+'.npz'),t=d['t'],reference_xy=d['gt_xy'],reference_heading=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'],xy=xy,heading=h,motion=m)
    return summarize(rr),rr

def prepare_features(entries,cal,basemodel=None,independent=False):
    es=[]
    for old in entries:
        d=old['data'];row=old['row'];setup=row['setup'];c=cal[setup]
        if independent:
            rate=velocities(sensor(d),c);motion=np.c_[rate[:,0],np.zeros(len(rate)),rate[:,1]]
            state=dict(gravity=c['center_gravity_direction'],gyro_bias=c['gyro_bias_counts'][2],eligible=False)
            linear=feature_matrix(sensor(d),motion,c,state,'gravity_rotation')
            temp=dict(old,motion=motion,linear=linear,nonlinear=nonlinear_features(linear))
        else:temp=old
        if basemodel:
            motion=predict_affine(temp,basemodel)
            if independent:
                q=basemodel['lateral'][setup];z=np.c_[(temp['linear']-q['mean'])/q['std'],np.ones(len(temp['linear']))];motion[:,1]=np.clip(z@q['weights'],-q['cap'],q['cap'])
        else:motion=temp['motion']
        x,ax,regime,wheel=basic_features(d,motion,c);ys,stats=quiet_yaw_state(d,motion,c,wheel)
        label=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])
        es.append(dict(old,motion=motion,x=x,ax=ax,regime=regime,yaw_state=ys,yaw_stats=stats,label=label,target=np.c_[d['gt_v'],d['gt_yaw']]-motion[:,[0,2]],group=training_group(row)))
    return es

def fit_base(entries,cal,independent):
    es=[];lateral={}
    for e in entries:
        if independent:
            c=cal[e['setup']];d=e['data'];rate=velocities(sensor(d),c);m=np.c_[rate[:,0],np.zeros(len(rate)),rate[:,1]]
            state=dict(gravity=c['center_gravity_direction'],gyro_bias=c['gyro_bias_counts'][2],eligible=False)
            x=feature_matrix(sensor(d),m,c,state,'gravity_rotation');target=np.c_[d['gt_v'],d['gt_yaw']]-m[:,[0,2]]
            es.append(dict(e,motion=m,linear=x,nonlinear=nonlinear_features(x),target=target))
        else:es.append(e)
    if independent:
        for s in sorted({e['setup'] for e in es}):
            xx=[];yy=[];gg=[]
            for e in es:
                if e['setup']!=s:continue
                y,mask=lateral_labels(e['data']);ids=np.flatnonzero(mask)[::10];xx.append(e['linear'][ids]);yy.append(y[ids]);gg.extend([e['group']]*len(ids))
            x=np.concatenate(xx);y=np.concatenate(yy);count=Counter(gg);w=np.array([1/count[g] for g in gg]);w/=w.sum()
            mean=np.sum(x*w[:,None],0);std=np.maximum(np.sqrt(np.sum((x-mean)**2*w[:,None],0)),1e-5);z=np.c_[(x-mean)/std,np.ones(len(x))];reg=.3*np.eye(z.shape[1]);reg[-1,-1]=0
            weights=np.linalg.solve(z.T@(z*w[:,None])+reg,z.T@(y*w));cap=max(float(np.quantile(np.abs(y),.995)),.03)
            lateral[s]=dict(mean=mean.tolist(),std=std.tolist(),weights=weights.tolist(),cap=cap)
    clips=bounds(es);fits=fit(normal_system(adapted(es,'physical_products',clips)),.3,1.)
    return dict(fits=fits,feature_clip=clips,lateral=lateral,candidate=BASE)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--branch',choices=['conditional','independent'],required=True);args=parser.parse_args();ind=args.branch=='independent'
    start=time.perf_counter();torch.set_num_threads(4);out=ROOT/('outputs_controlled_refit_v26' if ind else 'outputs_controlled_motion_v25')
    if out.exists():raise RuntimeError('Preserve previous run')
    out.mkdir();save_json(out/'predeclared_grid.json',dict(branch=args.branch,candidates=GRID,folds=[sorted(f) for f in FOLDS],selection='Minimum pooled equal-person path RMSE, <=5% worst-person regression vs branch control; zero eligible',scope='Fixed clocks/reference/QC. Independent branch refits calibration and every motion-model parameter; conditional branch retains inherited neural base. No test access.'))
    train=load_train(ROOT/'outputs_motion_endpoint_v16');source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];fixedcal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());records=[]
    for i,fold in enumerate(FOLDS):
        fitting=[e for e in train if e['row']['participant'] not in fold];held=[e for e in train if e['row']['participant'] in fold]
        cal=calibrate([(e['row'],e['data'],{}) for e in fitting],cfg) if ind else fixedcal
        base=fit_base(fitting,cal,ind);fitentries=prepare_features(fitting,cal,base,ind);heldentries=prepare_features(held,cal,base,ind)
        model=dict(slip=constrained_slip_fit(fitentries));model['aux']=auxiliary_fit(fitentries,model['slip'])
        save_json(out/f'fold_{i}_model.json',dict(calibration=cal,base=base,correction=model,fit_ids=[e['row']['id'] for e in fitting],held_participants=sorted(fold)))
        for c in GRID:
            (_,_,_),rr=evaluate(heldentries,model,c,cfg);records.extend([dict(candidate=c['name'],fold=i,**r) for r in rr]);print(args.branch,'fold',i,c['name'],summarize(rr)[0]['equal_participant_mean_position_rmse_m'],flush=True)
        del fitting,held,fitentries,heldentries,base,model
    write_csv(out/'fold_trials.csv',records);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in records if r['candidate']=='control'])[1]};candidates=[]
    for c in GRID:
        s,p,cond=summarize([r for r in records if r['candidate']==c['name']]);candidates.append(dict(c,score=s['equal_participant_mean_position_rmse_m'],heading=s['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(x['mean_trial_position_rmse_m']/basepeople[x['participant']] for x in p)))
    eligible=[c for c in candidates if c['worst_person_ratio']<=1.05];selected=min(eligible,key=lambda c:c['score'])
    representatives={'control':GRID[0]}
    for category,prefix in [('braking','braking_'),('yaw_state','yaw_state_'),('combined','combined_')]:
        cc=[c for c in candidates if c['name'].startswith(prefix) and c['worst_person_ratio']<=1.05];representatives[category]=min(cc,key=lambda c:c['score']) if cc else GRID[0]
    representatives['selected']=selected;save_json(out/'selection.json',dict(selected=selected,candidates=candidates,representatives=representatives,selected_before_validation=True,test_evaluated=False))
    cal=calibrate([(e['row'],e['data'],{}) for e in train],cfg) if ind else fixedcal;base=fit_base(train,cal,ind);fitting=prepare_features(train,cal,base,ind);model=dict(slip=constrained_slip_fit(fitting));model['aux']=auxiliary_fit(fitting,model['slip'])
    save_json(out/'model.json',dict(branch=args.branch,calibration=cal,base=base,correction=model,selected=selected,training_ids=[e['row']['id'] for e in train]));del fitting,train
    manifest=json.loads((source/'artifact_manifest.json').read_text());validation=[]
    if not ind:
        ridge=load_observed_ridge();states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        if not ind:
            m=ridge(sensor(d));x=feature_matrix(sensor(d),m,cal[row['setup']],states[row['id']],'gravity_rotation')
        else:m=np.zeros((len(d['t']),3));x=np.zeros((len(d['t']),75),np.float32)
        validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup'],group=training_group(row)))
    evaluation=prepare_features(validation,cal,base,ind);summaries={};quiet=[dict(id=e['row']['id'],**e['yaw_stats']) for e in evaluation];save_json(out/'validation_quiet_states.json',quiet)
    for name,c in representatives.items():
        cache=out/name/'trajectories';cache.mkdir(parents=True);(s,p,conds),rr=evaluate(evaluation,model,c,cfg,cache);summaries[name]=s
        for suffix,values in [('trials',rr),('participants',p),('maneuvers',conds)]:write_csv(out/f'{name}_{suffix}.csv',values)
    save_json(out/'run.json',dict(branch=args.branch,summary=summaries,selected=selected,training_trials=473,validation_trials=71,test_evaluated=False,runtime_seconds=time.perf_counter()-start,scope='Fixed benchmark synchronization/reference/QC; no refit of these. Independent branch: newly fitted calibration and motion predictor, no inherited pretrained predictor. Conditional: new corrections over fold-refit v24 residual on inherited predictor.',limitations=['Unknown CSV encoding and full mounting remain unverified','Quiet yaw correction is IMU-derived zero-rate model-output state, not full attitude INS','Variance is in-fit residual confidence; not independently calibrated covariance','Validation reused; no new blind accuracy claim'],provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'pipeline.py',ROOT/'learning.py',source/'artifact_manifest.json',ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json']}))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
