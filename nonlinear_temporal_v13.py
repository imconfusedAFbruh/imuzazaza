"""Participant-fold selected nonlinear temporal ridge residual; CPU comparator."""
import json,time
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from learning import load_predictor,training_group
from observed_reference_experiment import load_planar
from observed_ridge_experiment import imu_features
from observed_training_experiment import observed_rows
from planar_experiment import lateral_labels
from trajectory_calibration_v10 import integrate

FOLD={'No.3','No.8','No.15','No.20'}
OUT=ROOT/'outputs_nonlinear_temporal_v13'

def expand(x,m):
    # Future IMU smoothing only, no optical features; finite record-edge extension.
    z=np.c_[x,m]
    return np.c_[z,uniform_filter1d(z,25,axis=0,mode='nearest'),
                 uniform_filter1d(z,101,axis=0,mode='nearest')]

def normalization(entries):
    counts=Counter(e['group'] for e in entries)
    sx=[];sw=[]
    for e in entries:
        a=e['x'][::10];sx.append(a);sw.extend([1/(counts[e['group']]*len(a))]*len(a))
    x=np.concatenate(sx);w=np.array(sw);w/=w.sum()
    mean=np.sum(x*w[:,None],axis=0)
    std=np.maximum(np.sqrt(np.sum((x-mean)**2*w[:,None],axis=0)),1e-5)
    return mean,std

def design(x,mean,std):
    z=np.clip((x-mean)/std,-6,6)
    # Fixed nonlinear basis allows sign and intensity-dependent IMU relationships.
    return np.c_[z,np.tanh(z),z*np.abs(z),np.ones(len(z))]

def fit(entries,alpha):
    mean,std=normalization(entries);counts=Counter(e['group'] for e in entries)
    n=len(mean)*3+1;cov=np.zeros((n,n));rhs=np.zeros((n,3));targets=[]
    for e in entries:
        ids=np.flatnonzero(e['valid'])[::10]
        if not len(ids):continue
        a=design(e['x'][ids],mean,std);y=e['target'][ids]
        weight=1/(counts[e['group']]*len(ids))
        cov+=weight*a.T@a;rhs+=weight*a.T@y;targets.append(y)
    # Every feature, including offset, is regularized toward unchanged ridge.
    w=np.linalg.solve(cov+alpha*np.eye(n),rhs)
    cap=np.maximum(np.quantile(np.abs(np.concatenate(targets)),.995,axis=0),.01)
    return dict(mean=mean,std=std,weights=w,cap=cap)

def correct(e,model,gain,channels):
    m=e['motion'].copy()
    if gain:
        delta=np.clip(design(e['x'],model['mean'],model['std'])@model['weights'],-model['cap'],model['cap'])
        # Gate no channels using validation; candidate channel subsets are predeclared.
        for c in channels:m[:,c]+=gain*delta[:,c]
    return m

def score(entries,model,gain,channels,cfg):
    rows=[]
    for e in entries:
        xy,h=integrate(e['data'],correct(e,model,gain,channels))
        rows.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],setup=e['row']['setup'],**metrics(e['data'],xy,h,cfg)))
    return summarize(rows),rows

def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve existing execution')
    OUT.mkdir();torch.set_num_threads(4)
    src=ROOT/'outputs_observed_reference_v7';cfg=json.loads((src/'run.json').read_text())['settings'];manifest=json.loads((src/'artifact_manifest.json').read_text())
    parent=ROOT/'outputs_amended_v2';cal=json.loads((parent/'calibration.json').read_text());tcn=load_predictor(parent,'tcn32');champ=load_planar()
    selected=json.loads((ROOT/'outputs_observed_ridge_v8/selection.json').read_text())['best']
    # Loading the sealed loader first verifies all inherited dependency hashes.
    from observed_ridge_inference import load_observed_ridge
    load_observed_ridge()
    with np.load(ROOT/'outputs_observed_ridge_v8/linear_artifacts.npz') as a:
        rmean,rstd,rcap,rw=[a[k].copy() for k in ('mean','std','cap',f'weights_{selected["alpha"]}')]
    def prepare(row,d):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')}
        x,m=imu_features(imu,cal,tcn,champ)
        m=m+selected['gain']*np.clip(np.c_[(x-rmean)/rstd,np.ones(len(x))]@rw,-rcap,rcap)
        side,mask=lateral_labels(d);truth=np.c_[d['gt_v'],side,d['gt_yaw']]
        valid=mask&d['label_valid']&d['imu_valid']&np.isfinite(truth).all(axis=1)
        return dict(row=row,data=d,x=expand(x,m).astype(np.float32),motion=m,target=truth-m,valid=valid,group=training_group(row))
    train=[]
    for row,d,_ in observed_rows(src,cfg,'train',manifest):
        train.append(prepare(row,d))
        if len(train)%50==0:print('Prepared',len(train),flush=True)
    inner=[e for e in train if e['row']['participant'] in FOLD];fitting=[e for e in train if e['row']['participant'] not in FOLD]
    (baseline,people,_),_=score(inner,{},0,[],cfg);bp={p['participant']:p['mean_trial_position_rmse_m'] for p in people}
    candidates=[dict(alpha=0,gain=0,channels=[],score=baseline['equal_participant_mean_position_rmse_m'],worst_person_ratio=1)]
    for alpha in (.1,1.,10.):
        model=fit(fitting,alpha)
        for gain in (.25,.5,1.):
            for channels in ([0],[2],[0,1,2]):
                (s,p,_),_=score(inner,model,gain,channels,cfg)
                c=dict(alpha=alpha,gain=gain,channels=channels,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(x['mean_trial_position_rmse_m']/bp[x['participant']] for x in p))
                candidates.append(c);print('Fold',c,flush=True)
    chosen=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score'])
    save_json(OUT/'selection.json',dict(selected=chosen,candidates=candidates,fold=sorted(FOLD),caveat='Conditional inherited base saw fold participants; all new coefficients and normalization exclude fold until final refit.',rule='Min mean path RMSE with <=5% worst-person regression, zero candidate included.'))
    model=fit(train,chosen['alpha']) if chosen['gain'] else {}
    np.savez(OUT/'model.npz',**model)
    val=[prepare(row,d) for row,d,_ in observed_rows(src,cfg,'validation',manifest)]
    summaries={}
    for name,mod,gain,ch in [('ridge',{},0,[]),('nonlinear',model,chosen['gain'],chosen['channels'])]:
        (s,p,c),rows=score(val,mod,gain,ch,cfg);summaries[name]=s
        for suffix,data in [('trials',rows),('participants',p),('maneuvers',c)]:write_csv(OUT/f'{name}_{suffix}.csv',data)
    save_json(OUT/'run.json',dict(summary=summaries,selected=chosen,training_ids=[e['row']['id'] for e in train],validation_trials=len(val),runtime_seconds=time.perf_counter()-start,test_evaluated=False,provenance={str(p.relative_to(ROOT)):digest(p) for p in (Path(__file__),src/'artifact_manifest.json',ROOT/'outputs_observed_ridge_v8/artifact_manifest.json')}))
    (OUT/'report.md').write_text('# Nonlinear temporal ridge residual v13\n\nFixed original/25-frame/101-frame IMU-feature averages, tanh and signed-quadratic basis. Training-group balanced fit; trainfold alpha/gain/channel selection before full-training refit and single validation evaluation. Unknown hardware encoding remains unresolved. Future IMU only, no later optical pose feedback or test acquisitions.\n\n'+json.dumps(summaries,indent=2)+'\n',encoding='utf-8')
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}))
    print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
