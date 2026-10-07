"""Small training-only motion calibration and endpoint fusion comparator."""
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from learning import training_group
from planar_experiment import lateral_labels
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from long_horizon_inference import load_endpoint_ensemble

FOLD={'No.3','No.8','No.15','No.20'}
PARAM_SCALE=np.array([.1]*3+[.02]*3+[.5]*3)
RATE_SCALE=np.array([.3,.1,.4])

def design(m,e):
    f=np.zeros((len(m),3,9))
    for j in range(3):
        f[:,j,j]=m[:,j];f[:,j,j+3]=1;f[:,j,j+6]=e[:,j]-m[:,j]
    return f*PARAM_SCALE

def integrate(data,m):
    t=data['t'];dt=np.diff(t);v=(m[1:]+m[:-1])/2
    h=np.r_[0,np.cumsum(dt*v[:,2])]+data['gt_heading'][0]
    mid=(h[:-1]+h[1:])/2;c,s=np.cos(mid),np.sin(mid)
    steps=dt[:,None]*np.c_[v[:,0]*c-v[:,1]*s,v[:,0]*s+v[:,1]*c]
    xy=np.vstack((np.zeros(2),np.cumsum(steps,axis=0)))+data['gt_xy'][0]
    bad=np.flatnonzero(~data['imu_valid'])
    if len(bad):xy[bad[0]:]=np.nan;h[bad[0]:]=np.nan
    return xy,h

def endpoint_equations(d,m,f):
    aa,yy=[],[]
    for a in range(0,len(m),100):
        if not d['gt_valid'][a]:continue
        for horizon in (100,300,500,1000):
            b=a+horizon
            if b>=len(m) or not d['gt_valid'][b] or not d['imu_valid'][a:b+1].all():continue
            dt=np.diff(d['t'][a:b+1]);v=(m[a:b]+m[a+1:b+1])/2
            ff=(f[a:b]+f[a+1:b+1])/2
            h=np.r_[0,np.cumsum(dt*v[:,2])];hj=np.vstack((np.zeros(9),np.cumsum(dt[:,None]*ff[:,2],axis=0)))
            mid=(h[:-1]+h[1:])/2;jmid=(hj[:-1]+hj[1:])/2;c,s=np.cos(mid),np.sin(mid)
            pred=np.array([np.sum(dt*(v[:,0]*c-v[:,1]*s)),np.sum(dt*(v[:,0]*s+v[:,1]*c)),h[-1]])
            jac=np.array([np.sum(dt[:,None]*(c[:,None]*ff[:,0]-s[:,None]*ff[:,1]+(-s*v[:,0]-c*v[:,1])[:,None]*jmid),axis=0),
                          np.sum(dt[:,None]*(s[:,None]*ff[:,0]+c[:,None]*ff[:,1]+(c*v[:,0]-s*v[:,1])[:,None]*jmid),axis=0),hj[-1]])
            h0=d['gt_heading'][a];delta=d['gt_xy'][b]-d['gt_xy'][a]
            target=np.r_[np.array([[np.cos(h0),np.sin(h0)],[-np.sin(h0),np.cos(h0)]])@delta,d['gt_heading'][b]-h0]
            err=target-pred;err[2]=np.arctan2(np.sin(err[2]),np.cos(err[2]))
            scale=(d['t'][b]-d['t'][a])*RATE_SCALE
            aa.append(jac/scale[:,None]);yy.append(err/scale)
    return np.array(aa).reshape(-1,3,9),np.array(yy).reshape(-1,3)

def equations(d,m,e):
    f=design(m,e);side,valid=lateral_labels(d)
    truth=np.c_[d['gt_v'],side,d['gt_yaw']]
    mask=valid&d['label_valid']&d['imu_valid']&np.isfinite(truth).all(axis=1)
    a=f[mask][::10]/RATE_SCALE[None,:,None];y=(truth-m)[mask][::10]/RATE_SCALE
    ae,ye=endpoint_equations(d,m,f)
    def normal(a,y):
        if not len(a):return np.zeros((9,9)),np.zeros(9)
        return np.einsum('nci,ncj->ij',a,a)/len(a),np.einsum('nci,nc->i',a,y)/len(a)
    return normal(a,y),normal(ae,ye),int(mask.sum()),len(ae)

def fit(entries,alpha,endpoint):
    counts=Counter((x['setup'],x['group']) for x in entries);result={}
    for setup in sorted({x['setup'] for x in entries}):
        members=[x for x in entries if x['setup']==setup];groups={x['group'] for x in members}
        cov=np.zeros((9,9));rhs=np.zeros(9)
        for x in members:
            weight=1/(len(groups)*counts[(setup,x['group'])])
            (c,r),(ce,re)=x['equations'][:2];cov+=weight*(c+endpoint*ce);rhs+=weight*(r+endpoint*re)
        result[setup]=np.linalg.solve(cov+alpha*np.eye(9),rhs)
    return result

def score(entries,weights,gain,cfg,control=None):
    records=[]
    for x in entries:
        d=x['data'];m=x['ridge'].copy()
        if control=='endpoint':m=x['endpoint']
        elif gain:m+=gain*np.einsum('nci,i->nc',design(m,x['endpoint']),weights.get(x['setup'],np.zeros(9)))
        xy,h=integrate(d,m)
        records.append(dict(id=x['row']['id'],participant=x['row']['participant'],condition=x['row']['condition'],setup=x['setup'],**metrics(d,xy,h,cfg)))
    return summarize(records),records

def main():
    started=time.perf_counter();out=ROOT/'outputs_trajectory_calibration_v10'
    if out.exists():raise RuntimeError('Preserve prior run')
    out.mkdir();torch.set_num_threads(4)
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text())
    ridge,endpoint=load_observed_ridge(),load_endpoint_ensemble();train=[]
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};m,e=ridge(imu),endpoint(imu)
        train.append(dict(row=row,data=d,ridge=m,endpoint=e,setup=str(d['setup']),group=training_group(row),equations=equations(d,m,e)))
        if len(train)%50==0:print('Training motions/equations',len(train),flush=True)
    inner=[x for x in train if x['row']['participant'] in FOLD];fitrows=[x for x in train if x['row']['participant'] not in FOLD]
    if len({x['row']['participant'] for x in inner})!=4:raise RuntimeError('Training fold participant coverage differs')
    (baseline,people,_),_=score(inner,{},0,cfg);basepeople={x['participant']:x['mean_trial_position_rmse_m'] for x in people}
    candidates=[dict(alpha=0,endpoint_weight=0,gain=0,score=baseline['equal_participant_mean_position_rmse_m'],worst_person_ratio=1.)]
    for alpha in (.01,.1,1.):
        for ew in (0.,1.):
            w=fit(fitrows,alpha,ew)
            for gain in (.25,.5,1.):
                (summary,ppl,_),_=score(inner,w,gain,cfg)
                ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in ppl)
                c=dict(alpha=alpha,endpoint_weight=ew,gain=gain,score=summary['equal_participant_mean_position_rmse_m'],worst_person_ratio=ratio);candidates.append(c)
                print('Inner',c,flush=True)
    eligible=[c for c in candidates if c['worst_person_ratio']<=1.05];selected=min(eligible,key=lambda c:c['score'])
    save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),rule='Minimum equal-participant trajectory RMSE subject to <=5% worst-person regression; unchanged ridge eligible',caveat='Inherited base models previously trained on these fold participants; conditional correction selection only.'))
    weights=fit(train,selected['alpha'],selected['endpoint_weight']) if selected['gain'] else {}
    save_json(out/'weights.json',dict(weights={k:v.tolist() for k,v in weights.items()},gain=selected['gain'],parameter_scale=PARAM_SCALE.tolist(),columns=['forward_scale','lateral_scale','yaw_scale','forward_offset','lateral_offset','yaw_offset','forward_endpoint_blend','lateral_endpoint_blend','yaw_endpoint_blend'],training_ids=[x['row']['id'] for x in train]))
    validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')}
        validation.append(dict(row=row,data=d,ridge=ridge(imu),endpoint=endpoint(imu),setup=str(d['setup'])))
    summaries={}
    for name,w,g,control in [('ridge',{},0,None),('endpoint',{},0,'endpoint'),('calibrated',weights,selected['gain'],None)]:
        (summary,people,conditions),records=score(validation,w,g,cfg,control)
        summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',people),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    save_json(out/'run.json',dict(selected=selected,summary=summaries,training_trials=len(train),validation_trials=len(validation),test_evaluated=False,runtime_seconds=time.perf_counter()-started,endpoint_supervision='Observed start/end only at 1/3/5/10 s; uninterrupted IMU; first-order sensitivity of integrated motion; no optical gap filling',provenance={str(f.relative_to(ROOT)):digest(f) for f in [Path(__file__),source/'artifact_manifest.json',ROOT/'observed_ridge_inference.py',ROOT/'long_horizon_inference.py']}))
    report=['# Training-only per-setup trajectory calibration v10','','Nine interpretable coefficients per acquisition setup: scale, constant offset and endpoint-ensemble difference for each motion channel. Shared candidate hyperparameters are selected on a fixed training participant fold before final validation. No hand-selected date weights.','',f'Selected: {selected}','','| Model | Overall RMSE (mm) |','|---|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for k,v in summaries.items()]+['','Endpoint constraints use real observed poses only; intermediate optical gaps are never filled. The linearized endpoint fit is an approximation, damped with fold-selected gain. Initial pose only at inference. The fixed inner fold is conditional because inherited predictors previously saw its training data. Repeated validation remains exploratory. Unknown hardware integer encoding is not resolved by these empirical coefficients. No test signals were read.']
    (out/'report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    save_json(out/'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()}))
    print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
