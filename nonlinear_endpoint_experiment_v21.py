"""Finite CPU physical-product residual comparator with observed endpoints."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv
from learning import training_group
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from motion_endpoint_experiment_v16 import normal_system,fit,score

FOLD={'No.3','No.8','No.15','No.20'}
GRID=[dict(basis='zero',alpha=0.,endpoint_weight=0.,gain=0.),dict(basis='linear',alpha=.1,endpoint_weight=1.,gain=.5)]+[dict(basis='physical_products',alpha=a,endpoint_weight=1.,gain=g) for a in (.1,1.,10.) for g in (.25,.5)]
PRODUCTS=['ridge_forward_times_yaw','ridge_forward_squared','ridge_yaw_squared','wheel_mean_squared','wheel_difference_times_mean','center_acc_norm_squared','center_gyro_norm_squared','vertical_yaw_times_ridge_yaw']

def nonlinear_features(x):
    if x.shape[1]!=75:raise RuntimeError('Unexpected v14 feature schema')
    products=[]
    for start in range(0,75,15):
        f=x[:,start:start+15].astype(float);mean=(f[:,6]+f[:,7])/2;diff=f[:,7]-f[:,6]
        products.append(np.c_[f[:,8]*f[:,9],f[:,8]**2,f[:,9]**2,mean**2,diff*mean,np.sum(f[:,:3]**2,axis=1),np.sum(f[:,3:6]**2,axis=1),f[:,12]*f[:,9]])
    return np.c_[x,*products].astype(np.float32)

def bounds(entries):
    result={}
    for setup in sorted({e['setup'] for e in entries}):
        xs=np.concatenate([e['nonlinear'][np.flatnonzero(e['label'])[::10],75:] for e in entries if e['setup']==setup])
        result[setup]=dict(low=np.quantile(xs,.001,axis=0).tolist(),high=np.quantile(xs,.999,axis=0).tolist())
    return result

def adapted(entries,basis,clips):
    rows=[]
    for e in entries:
        x=e['linear']
        if basis=='physical_products':
            q=clips[e['setup']];x=np.c_[x,np.clip(e['nonlinear'][:,75:],q['low'],q['high'])].astype(np.float32)
        rows.append(dict(e,x=x))
    return rows

def load_train(parent):
    manifest=json.loads((parent/'artifact_manifest.json').read_text())['sha256'];run=json.loads((parent/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed v16 dependency '+name)
    entries=[]
    for path in sorted((parent/'prepared_training').glob('*.npz')):
        meta=path.with_suffix('.json')
        for p in (path,meta):
            if digest(p)!=manifest[str(p.relative_to(parent))]:raise RuntimeError('Changed prepared training '+p.name)
        q=json.loads(meta.read_text());row=q['row']
        if row['partition']!='train' or q['feature_mode']!='gravity_rotation':raise RuntimeError('Invalid training preparation')
        with np.load(path,allow_pickle=False) as z:d={k:z[k] for k in z.files}
        x=d.pop('features');m=d.pop('ridge_motion');y=d.pop('residual_target');label=d.pop('residual_label_valid')
        entries.append(dict(row=row,data=d,motion=m,target=y,label=label,linear=x,nonlinear=nonlinear_features(x),setup=row['setup'],group=training_group(row)))
    if len(entries)!=473:raise RuntimeError('Training coverage changed')
    return entries

def main():
    started=time.perf_counter();torch.set_num_threads(4);out=ROOT/'outputs_nonlinear_endpoint_v21';parent=ROOT/'outputs_motion_endpoint_v16'
    if out.exists():raise RuntimeError('Preserve prior run')
    out.mkdir();save_json(out/'predeclared_grid.json',dict(candidates=GRID,fold=sorted(FOLD),products=PRODUCTS,contexts_seconds=[-.5,-.25,0.,.25,.5],endpoint_weight=1.,feature_clipping='Added40products clipped to .001/.999 quantiles of fitting training labels per setup; original75features unchanged',selection='Minimum fold equal-participant path RMSE subject to <=5%worstparticipant regression against unchanged ridge',test_evaluated=False))
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];train=load_train(parent);inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD];clips=bounds(fitrows)
    (_,people,_),_=score(adapted(inner,'linear',{}),{},GRID[0],cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates=[];innerrecords=[]
    for basis in ('zero','linear','physical_products'):
        systems=normal_system(adapted(fitrows,basis,clips)) if basis!='zero' else None
        evaluation=adapted(inner,basis,clips)
        for c in [q for q in GRID if q['basis']==basis]:
            fits=fit(systems,c['alpha'],c['endpoint_weight']) if c['gain'] else {}; (summary,ppl,_),records=score(evaluation,fits,c,cfg);result=dict(c,score=summary['equal_participant_mean_position_rmse_m'],heading=summary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in ppl));candidates.append(result);innerrecords.extend([dict(basis=basis,alpha=c['alpha'],gain=c['gain'],**r) for r in records]);print('Inner',result,flush=True)
    selected=min([q for q in candidates if q['worst_person_ratio']<=1.05],key=lambda q:q['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),caveat='Inherited base/calibration saw these participants previously; conditional residual selection, not whole-pipeline independent fold'));write_csv(out/'inner_trials.csv',innerrecords)
    clips=bounds(train);linearsystems=normal_system(adapted(train,'linear',{}));linearfit=fit(linearsystems,.1,1.);old=json.loads((parent/'model.json').read_text())['fits'];delta=max(float(np.max(np.abs(np.array(linearfit[k]['weights'])-old[k]['weights']))) for k in old)
    if delta>1e-6:raise RuntimeError('Linear v16 coefficient reproduction changed')
    if selected['basis']=='physical_products':selectedfits=fit(normal_system(adapted(train,'physical_products',clips)),selected['alpha'],1.)
    elif selected['gain']:selectedfits=linearfit
    else:selectedfits={}
    save_json(out/'model.json',dict(candidate=selected,fits=selectedfits,feature_clip=clips if selected['basis']=='physical_products' else {},products=PRODUCTS,training_ids=[e['row']['id'] for e in train],feature_count=115 if selected['basis']=='physical_products' else 75,v16_linear_max_weight_difference=delta))
    del train,inner,fitrows,linearsystems
    parent14=ROOT/'outputs_stationary_gravity_v14';pm=json.loads((parent14/'artifact_manifest.json').read_text())['sha256']
    if digest(parent14/'initialization.json')!=pm['initialization.json']:raise RuntimeError('Changed initialization')
    states={q['id']:q for q in json.loads((parent14/'initialization.json').read_text())['records']};cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());manifest=json.loads((source/'artifact_manifest.json').read_text());ridge=load_observed_ridge();validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(sensor);state=states[row['id']]
        if state['partition']!='validation' or state['setup']!=row['setup']:raise RuntimeError('Initialization differs')
        x=feature_matrix(sensor,m,cal[row['setup']],state,'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    summaries={}
    for name,f,c in [('cpu_ridge',{},GRID[0]),('v16_linear',linearfit,GRID[1]),('selected',selectedfits,selected)]:
        (summary,ppl,conditions),records=score(adapted(validation,c['basis'],clips),f,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',ppl),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    prior=json.loads((parent/'run.json').read_text())['summary']['endpoint']['equal_participant_mean_position_rmse_m']
    if abs(summaries['v16_linear']['equal_participant_mean_position_rmse_m']-prior)>1e-8:raise RuntimeError('Paired v16 score changed')
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=len(validation),test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-started,linear_reproduction_max_weight_difference=delta,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),parent/'artifact_manifest.json',ROOT/'motion_endpoint_experiment_v16.py',ROOT/'stationary_gravity_experiment_v14.py',parent14/'artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json',ROOT/'observed_ridge_inference.py']}))
    lines=['# Physical-product endpoint residual comparator v21','','Eight predeclared kinematic products at five contexts augment the exact75v14gravity-rotation features. Same masked point plus linearized observed-endpoint SE2 equations as v16; endpoint weight1 fixed. Products clipped and normalized using fitting training participants only. Output caps use fitting residual labels. Lateral remains ridge.','',f'Selected on fixed conditional training fold: {selected}','','| Model | Overall RMSE(mm) | Heading(deg) |','|---|---:|---:|']+[f'| {k} | {s["equal_participant_mean_position_rmse_m"]*1000:.3f} | {s["equal_participant_mean_heading_rmse_deg"]:.3f} |' for k,s in summaries.items()]+['','All473 training files verified against v16 prepared-cache hashes; v16linear coefficients and validation score reproduced. No sources/caches overwritten. Polynomial relationships are empirical feature hypotheses, not full SI calibration or identifiable physical tire slip. Reference gaps masked; observed endpoints only; initialpose only at inference. ±0.5s feature context plus inherited1.28s future base. Repeated71validation development remains exploratory; no test signal access.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
