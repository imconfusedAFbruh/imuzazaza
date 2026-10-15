"""Nonlinear recurrent motion residual, exact full-path TRAIN-only fitting."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import csv,json,time
from collections import Counter
import numpy as np
import pipeline as p
from participant_folds_experiment_v24 import FOLDS
from nonlinear_endpoint_experiment_v21 import nonlinear_features,adapted
from dynamic_tilt_experiment_v33 import dynamic_features,expanded
from dynamic_tilt_blend_v34 import corrected_entry
from trajectory_calibration_v10 import integrate
from combined_physics_folds_v58 import verified_json
from metric_contract_v74 import metrics
from joint_robust_motion_v119 import balanced

OUT=p.ROOT/'outputs_reservoir_path_v121'
LAMBDAS=(.1,1.,10.)
CAP=np.array([.05,.02])


def reservoir(x,valid,model):
    x=np.clip((x-np.array(model['mean']))/model['std'],-5,5)
    wi,wr=np.array(model['input']),np.array(model['recurrent'])
    state=np.zeros(16);states=np.zeros((len(x),16));drive=.2*(x@wi)
    for i in range(len(x)):
        if valid[i]:state=.8*state+.2*np.tanh(drive[i]+state@wr)
        else:state=np.zeros(16)
        states[i]=state
    return np.c_[states,np.ones(len(x))]


def prediction(e,weights,jacobian=False):
    d=e['data'];z=e['z'];raw=z@weights;motion=e['base'].copy()
    motion[:,[0,2]]+=np.clip(raw,-1,1)*CAP
    xy,h=integrate(d,motion)
    if not jacobian:return motion,xy,h
    active=(np.abs(raw)<1)&d['imu_valid'][:,None]
    sf=z*active[:,0,None]*CAP[0];sy=z*active[:,1,None]*CAP[1]
    dt=np.diff(d['t']);v=(motion[:-1]+motion[1:])/2
    fm=(sf[:-1]+sf[1:])/2;ym=(sy[:-1]+sy[1:])/2
    dh=np.vstack((np.zeros(17),np.cumsum(dt[:,None]*ym,axis=0)))
    mid=(h[:-1]+h[1:])/2;hm=(dh[:-1]+dh[1:])/2;c=np.cos(mid);s=np.sin(mid)
    jx=np.vstack((np.zeros(34),np.cumsum(dt[:,None]*np.c_[c[:,None]*fm,(-s*v[:,0]-c*v[:,1])[:,None]*hm],axis=0)))
    jy=np.vstack((np.zeros(34),np.cumsum(dt[:,None]*np.c_[s[:,None]*fm,(c*v[:,0]-s*v[:,1])[:,None]*hm],axis=0)))
    jh=np.c_[np.zeros_like(dh),dh]
    return motion,xy,h,np.stack((jx,jy,jh),axis=1)


def objective(es,weights,lam,normal=False):
    counts=Counter(e['row']['participant'] for e in es);loss=lam*np.sum(weights**2)
    cov=lam*np.eye(34);rhs=-lam*weights.T.ravel();scales=np.array([10.,10.,np.sqrt(.1)*10])
    for e in es:
        result=prediction(e,weights,normal);_,xy,h=result[:3];d=e['data'];ix=e['ix']
        err=np.c_[xy[ix]-d['gt_xy'][ix],np.angle(np.exp(1j*(h[ix]-d['gt_heading'][ix])))]*scales
        w=1/(len(counts)*counts[e['row']['participant']]*len(ix))
        loss+=w*np.sum(err**2)
        if normal:
            j=(result[3][ix]*scales[None,:,None]).reshape(-1,34)
            cov+=w*j.T@j;rhs-=w*j.T@err.ravel()
    return (loss,cov,rhs) if normal else float(loss)


def fit(es,lam):
    weights=np.zeros((17,2));history=[]
    for iteration in range(8):
        old,cov,rhs=objective(es,weights,lam,True)
        step=np.linalg.solve(cov,rhs).reshape(2,17).T
        chosen=0;value=old
        for gain in (1.,.5,.25):
            proposed=weights+gain*step;candidate=objective(es,proposed,lam)
            if candidate<value:chosen=gain;value=candidate;break
        weights+=chosen*step;history.append(dict(iteration=iteration,objective=value,step=chosen))
    assert np.isfinite(weights).all()
    return dict(weights=weights.tolist(),history=history)


def self_check():
    rng=np.random.default_rng(121);n=101;t=np.arange(n)*.01
    e=dict(data=dict(t=t,gt_heading=np.ones(n)*.4,gt_xy=np.zeros((n,2)),imu_valid=np.ones(n,bool)),
        z=rng.normal(size=(n,17)),base=np.tile([1,.1,.2],(n,1)))
    for scale in (.01,3.):
        w=rng.normal(size=(17,2))*scale;result=prediction(e,w,True)
        for column in (0,10,17,33):
            u=w.copy();u[column%17,column//17]+=1e-6;_,xy,h=prediction(e,u)
            numeric=np.c_[xy-result[1],h-result[2]]/1e-6
            assert np.max(np.abs(numeric-result[3][:,:,column]))<1e-6
    model=dict(mean=np.zeros(15),std=np.ones(15),input=rng.normal(size=(15,16)),recurrent=np.eye(16)*.9)
    x=rng.normal(size=(10,15));valid=np.ones(10,bool);valid[4]=False
    z=reservoir(x,valid,model);assert np.all(z[4,:16]==0)
    assert np.allclose(z[5:],reservoir(x[5:],valid[5:],model))
    assert np.array_equal(prediction(e,np.zeros((17,2)))[0],e['base'])


def main():
    start=time.perf_counter();self_check()
    if (p.ROOT/'research_state/STOP').exists():raise RuntimeError('STOP')
    OUT.mkdir(exist_ok=False);(OUT/'predictions').mkdir()
    parent=p.ROOT/'outputs_dynamic_blend_v34';pm=json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    assert p.digest(parent/'fold_trials.csv')==pm['fold_trials.csv']
    old={r['id']:r for r in csv.DictReader((parent/'fold_trials.csv').open(newline='')) if float(r['weight'])==.75}
    assert len(old)==207
    prep=p.ROOT/'outputs_motion_endpoint_v16';manifest=json.loads((prep/'artifact_manifest.json').read_text())['sha256']
    calibration_path=p.ROOT/'outputs_amended_v2/calibration.json'
    prepared_run=verified_json(prep,'run.json')
    provenance={k.replace(chr(92),'/'):v for k,v in prepared_run['provenance'].items()}
    assert p.digest(calibration_path)==provenance['outputs_amended_v2/calibration.json']
    cal=json.loads(calibration_path.read_text())
    cfg=verified_json(p.ROOT/'outputs_observed_reference_v7','run.json')['settings']
    sources=['reservoir_path_v121.py','research_docs/reservoir_path_v121.md','pipeline.py',
      'trajectory_calibration_v10.py','nonlinear_endpoint_experiment_v21.py','dynamic_tilt_experiment_v33.py',
      'dynamic_tilt_blend_v34.py','stationary_gravity_experiment_v14.py','metric_contract_v74.py',
      'participant_folds_experiment_v24.py','combined_physics_folds_v58.py','joint_robust_motion_v119.py',
      'research_metrics_v59.py','route_metrics_audit_v36.py']
    p.save_json(OUT/'protocol.json',dict(lambdas=LAMBDAS,seed=121,training_ids=sorted(old),validation_accessed=False,test_accessed=False,
        source_hashes={s:p.digest(p.ROOT/s) for s in sources},parent_manifest_sha256=p.digest(parent/'artifact_manifest.json'),prepared_manifest_sha256=p.digest(prep/'artifact_manifest.json')))
    entries=[]
    for ident in old:
        path=prep/'prepared_training'/(ident+'.npz');meta=path.with_suffix('.json')
        for f in (path,meta):assert p.digest(f)==manifest[str(f.relative_to(prep))]
        info=json.loads(meta.read_text());row=info['row'];assert row['partition']=='train' and row['participant'] in set.union(*FOLDS)
        with np.load(path) as z:d={k:z[k] for k in z.files}
        x=d.pop('features');motion=d.pop('ridge_motion');d.pop('residual_target');d.pop('residual_label_valid')
        e=dict(row=row,data=d,motion=motion,linear=x,nonlinear=nonlinear_features(x),setup=row['setup'])
        e['extra']=dynamic_features(d,motion,cal[row['setup']],info['initialization'],.3)
        entries.append(e)
    baselines={};checks=[]
    for fold,held in enumerate(FOLDS):
        q=verified_json(parent,f'fold_{fold}_models.json');assert not {e['row']['id'] for e in entries if e['row']['participant'] in held}&set(q['fit_ids'])
        aa=adapted(entries,'physical_products',q['feature_clip']);bb=expanded(entries,q['feature_clip'],q['extra_clip'])
        baselines[fold]=[.25*corrected_entry(a,q['original'])+.75*corrected_entry(b,q['tilt']) for a,b in zip(aa,bb)]
        for e,m in zip(entries,baselines[fold]):
            if e['row']['participant'] not in held:continue
            xy,h=integrate(e['data'],m);score=p.metrics(e['data'],xy,h,cfg);saved=old[e['row']['id']]
            assert score['scored_frames']==int(saved['scored_frames'])
            for k in ('position_rmse_m','heading_rmse_deg'):assert np.isclose(score[k],float(saved[k]),rtol=1e-10,atol=1e-12)
            checks.append(dict(id=e['row']['id'],**score))
    assert len(checks)==207;p.save_json(OUT/'baseline_reproduction.json',checks)
    print('Strong v34 all207 baseline scores reproduced',flush=True)
    rng=np.random.default_rng(121);wi=rng.normal(size=(15,16))/np.sqrt(15);wr=rng.normal(size=(16,16))/4
    wr*=.9/max(abs(np.linalg.eigvals(wr)));records=[]
    for fold,held in enumerate(FOLDS):
        if (p.ROOT/'research_state/STOP').exists():raise RuntimeError('STOP')
        fitting=[e for e in entries if e['row']['participant'] not in held];normalization={}
        for setup in sorted({e['setup'] for e in fitting}):
            x=np.concatenate([e['linear'][e['data']['imu_valid'],30:45][::10] for e in fitting if e['setup']==setup])
            normalization[setup]=dict(mean=x.mean(0).tolist(),std=np.maximum(x.std(0),1e-5).tolist(),input=wi.tolist(),recurrent=wr.tolist())
        es=[]
        for e,base in zip(entries,baselines[fold]):
            d=e['data'];xy,h=integrate(d,base);mask=d['gt_valid']&np.isfinite(xy).all(1)&np.isfinite(h)&np.isfinite(d['gt_heading'])
            ix=np.flatnonzero(mask)[::10];assert len(ix)>0
            es.append(dict(e,base=base,z=reservoir(e['linear'][:,30:45],d['imu_valid'],normalization[e['setup']]),ix=ix))
        models={}
        for lam in LAMBDAS:
            models[str(lam)]={setup:fit([e for e in es if e['setup']==setup and e['row']['participant'] not in held],lam) for setup in normalization}
            print('Fitted fold',fold,'lambda',lam,flush=True)
        p.save_json(OUT/f'fold_{fold}_models.json',dict(normalization=normalization,models=models,fitting_ids=[e['row']['id'] for e in fitting],held_people=sorted(held)))
        for e in es:
            row=e['row'];d=e['data']
            if row['participant'] not in held:continue
            arrays={k:d[k] for k in ('t','gt_xy','gt_heading','gt_valid','imu_valid')};support=None
            for lam in (0.,*LAMBDAS):
                weights=np.zeros((17,2)) if not lam else np.array(models[str(lam)][e['setup']]['weights'])
                m,xy,h=prediction(e,weights);mask=d['gt_valid']&np.isfinite(xy).all(1)
                if support is None:support=mask
                assert np.array_equal(mask,support)
                records.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],fold=fold,penalty=lam,**p.metrics(d,xy,h,cfg),**metrics(d,xy,h,m)))
                prefix=f'lambda_{lam:g}_';arrays.update({prefix+'motion':m,prefix+'xy':xy,prefix+'heading':h})
            np.savez_compressed(OUT/'predictions'/(row['id']+'.npz'),**arrays)
        p.write_csv(OUT/'trials.csv',records);p.save_json(OUT/'checkpoint.json',dict(completed_folds=fold+1,rows=len(records),status='running'))
        print('Completed fold',fold,flush=True)
    base=[r for r in records if r['penalty']==0];bs,bp,bm=p.summarize(base);assert np.isclose(bs['equal_participant_mean_position_rmse_m'],.13224020010362922)
    choices=[]
    for lam in (0.,*LAMBDAS):
        rr=[r for r in records if r['penalty']==lam];assert len(rr)==207
        s,pp,mm=p.summarize(rr)
        pr={r['participant']:r['mean_trial_position_rmse_m']/next(b['mean_trial_position_rmse_m'] for b in bp if b['participant']==r['participant']) for r in pp}
        mr={r['condition']:r['equal_participant_mean_position_rmse_m']/next(b['equal_participant_mean_position_rmse_m'] for b in bm if b['condition']==r['condition']) for r in mm}
        guards={k:balanced(rr,k)/balanced(base,k) for k in ('Position_P95_mm','Last_Supported_Endpoint_Error_mm','heading_rmse_deg')}
        eligible=lam==0 or (s['equal_participant_mean_position_rmse_m']<bs['equal_participant_mean_position_rmse_m'] and max(pr.values())<=1.05 and max(mr.values())<=1.05 and max(guards.values())<=1.05)
        choices.append(dict(penalty=lam,eligible=eligible,**s,participant_ratios=pr,maneuver_ratios=mr,guard_ratios=guards))
        p.write_csv(OUT/f'lambda_{lam:g}_participants.csv',pp);p.write_csv(OUT/f'lambda_{lam:g}_maneuvers.csv',mm)
    selected=min((c for c in choices if c['eligible']),key=lambda c:c['equal_participant_mean_position_rmse_m'])
    p.save_json(OUT/'run.json',dict(candidates=choices,selected=selected,validation_accessed=False,test_accessed=False,runtime_s=time.perf_counter()-start))
    p.save_json(OUT/'checkpoint.json',dict(completed_folds=3,rows=len(records),status='complete'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps(choices,indent=2),flush=True)


if __name__=='__main__':main()
