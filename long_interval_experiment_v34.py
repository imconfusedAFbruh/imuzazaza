"""Add15/30second observed-only endpoint constraints to frozen v21 systems."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','3')
import json,time,sys
from pathlib import Path
from collections import Counter
import numpy as np
import torch
import motion_endpoint_experiment_v16 as endpoint
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from nonlinear_endpoint_experiment_v21 import load_train,adapted,nonlinear_features,FOLD
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix,correction
from trajectory_calibration_v10 import integrate

OUT=ROOT/'outputs_long_interval_v34';WEIGHTS=(0.,.1,.3);C=dict(basis='physical_products',alpha=.1,endpoint_weight=1.,gain=.5)

def read_system(name):
    parent=ROOT/'outputs_nonlinear_endpoint_tuning_v22';manifest=json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    for suffix in ['.npz','.json']:
        path=parent/(name+suffix)
        if digest(path)!=manifest[name+suffix]:raise RuntimeError('Changed normal system')
    meta=json.loads((parent/(name+'.json')).read_text());ss={}
    with np.load(parent/(name+'.npz')) as z:
        for s in meta['setups']:ss[s['setup']]={key[len(f"s{s['index']}_"):]:z[key].item() if z[key].ndim==0 else z[key] for key in z.files if key.startswith(f"s{s['index']}_")}
    return ss,meta

def long_system(entries,ss):
    endpoint.HORIZONS=(1500,3000);result={}
    for setup,q in ss.items():
        pieces=[];counts=Counter()
        for e in [e for e in entries if e['setup']==setup]:
            cov,rhs,n=endpoint.endpoint_normal(e,q['mean'],q['std']);pieces.append((e['group'],cov,rhs,n));counts[e['group']]+=n
        groups=sum(v>0 for v in counts.values());ce=np.zeros_like(q['endpoint']);re=np.zeros_like(q['endpoint_rhs'])
        for group,c,r,n in pieces:
            if n:ce+=c/(groups*counts[group]);re+=r/(groups*counts[group])
        result[setup]=dict(cov=ce,rhs=re,pairs=sum(counts.values()));print('Long pairs',setup,sum(counts.values()),flush=True)
    return result

def fitted(ss,long,weight):
    system={s:dict(q,endpoint=q['endpoint']+weight*long[s]['cov'],endpoint_rhs=q['endpoint_rhs']+weight*long[s]['rhs']) for s,q in ss.items()}
    return endpoint.fit(system,.1,1.)

def main():
    started=time.perf_counter();torch.set_num_threads(3)
    if OUT.exists() and ('--resume' not in sys.argv or (OUT/'run.json').exists()):raise RuntimeError('Preserve run')
    OUT.mkdir(exist_ok='--resume' in sys.argv);save_json(OUT/'protocol.json',dict(horizons_s=[15,30],weights=WEIGHTS,candidate=C,normalization='Inherited original observed-only training normals reproduced exactly atweight0',selection='Fixedconditional4participantfold;minimumRMSEwith<=5%worstpersonregressionvsoriginalv21;selectionbeforevalidation',test_accessed=False))
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];train=load_train(ROOT/'outputs_motion_endpoint_v16');held=[e for e in train if e['row']['participant'] in FOLD];fitting=[e for e in train if e['row']['participant'] not in FOLD]
    ss,meta=read_system('fold_normal_systems');assert set(meta['training_ids'])=={e['row']['id'] for e in fitting};fitrows=adapted(fitting,C['basis'],meta['feature_clip']);long=long_system(fitrows,ss);evalrows=adapted(held,C['basis'],meta['feature_clip']);choices=[];foldrecords=[];baseline={}
    for w in WEIGHTS:
        fits=fitted(ss,long,w);(s,p,_),rr=endpoint.score(evalrows,fits,C,cfg)
        if w==0:baseline={q['participant']:q['mean_trial_position_rmse_m'] for q in p}
        q=dict(weight=w,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(v['mean_trial_position_rmse_m']/baseline[v['participant']] for v in p));choices.append(q);foldrecords.extend([dict(weight=w,**r) for r in rr]);print('Trainingfold',q,flush=True)
    selected=min([q for q in choices if q['worst_person_ratio']<=1.05],key=lambda q:q['score']);save_json(OUT/'selection.json',dict(selected=selected,candidates=choices,selected_before_validation=True));write_csv(OUT/'fold_trials.csv',foldrecords)
    ss,meta=read_system('full_normal_systems');assert set(meta['training_ids'])=={e['row']['id'] for e in train};fitrows=adapted(train,C['basis'],meta['feature_clip']);long=long_system(fitrows,ss);models={w:fitted(ss,long,w) for w in WEIGHTS};old=json.loads((ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text());difference=max(float(np.max(np.abs(np.asarray(models[0][s]['weights'])-np.asarray(old['fits'][s]['weights'])))) for s in old['fits']);assert difference<1e-8
    for w in WEIGHTS:save_json(OUT/f'weight_{w}_model.json',dict(fits=models[w],candidate=C,feature_clip=meta['feature_clip'],weight=w,training_ids=meta['training_ids']))
    del train,held,fitting,fitrows,evalrows
    manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());states={s['id']:s for s in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};ridge=load_observed_ridge();records={w:[] for w in WEIGHTS};cache=OUT/'trajectories';cache.mkdir()
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        sensor={k:d[k] for k in ['setup','t','raw','imu_valid']};m=ridge(sensor);x=feature_matrix(sensor,m,cal[row['setup']],states[row['id']],'gravity_rotation');e=dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']);e=adapted([e],C['basis'],meta['feature_clip'])[0];e['x']={'gravity_rotation':e['x']};arrays=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'])
        for w in WEIGHTS:
            mm=correction(e,models[w],dict(C,mode='gravity_rotation'));xy,h=integrate(d,mm);records[w].append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,cfg)));arrays[f'weight_{w}_xy_m']=xy;arrays[f'weight_{w}_heading_rad']=h;arrays[f'weight_{w}_motion']=mm
        np.savez_compressed(cache/(row['id']+'.npz'),**arrays)
    summary={}
    for w,rr in records.items():
        summary[str(w)],p,cond=summarize(rr)
        for suffix,values in [('trials',rr),('participants',p),('maneuvers',cond)]:write_csv(OUT/f'weight_{w}_{suffix}.csv',values)
    save_json(OUT/'run.json',dict(summary=summary,selected=selected,base_refit=False,training_trials=473,validation_trials=71,test_accessed=False,control_weight_difference=difference,runtime_seconds=time.perf_counter()-started,source_sha256=digest(Path(__file__))));save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
