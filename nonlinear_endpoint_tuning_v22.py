"""Fixed training-fold extension of the v21 physical-product comparator."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from motion_endpoint_experiment_v16 import normal_system,fit,score
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted,nonlinear_features,PRODUCTS,FOLD

ZERO=dict(basis='zero',alpha=0.,endpoint_weight=0.,gain=0.)
ORIGINAL=dict(basis='physical_products',alpha=.1,endpoint_weight=1.,gain=.5)
GRID=[ZERO]+[dict(basis='physical_products',alpha=a,endpoint_weight=w,gain=g) for a in (.01,.03,.1,.3,1.) for w in (1.,3.,10.) for g in (.25,.5,.75,1.)]

def save_systems(out,name,systems,clips,ids):
    arrays={};meta=[]
    for i,(setup,q) in enumerate(systems.items()):
        for key,value in q.items():arrays[f's{i}_{key}']=np.asarray(value)
        meta.append(dict(index=i,setup=setup))
    np.savez_compressed(out/(name+'.npz'),**arrays)
    save_json(out/(name+'.json'),dict(setups=meta,feature_clip=clips,training_ids=ids,source='v16 normal_system using v21 physical-products and training-only clipping; no heldout target enters fit'))

def objective(systems,fits):
    point=[];endpoint=[]
    for setup,q in systems.items():
        w=np.asarray(fits[setup]['weights']);beta=np.r_[w[:,0],w[:,1]]
        point.append(float(beta@q['point']@beta-2*q['rhs']@beta));endpoint.append(float(beta@q['endpoint']@beta-2*q['endpoint_rhs']@beta))
    return dict(point_quadratic_without_target_constant=float(np.mean(point)),endpoint_quadratic_without_target_constant=float(np.mean(endpoint)))

def main():
    started=time.perf_counter();torch.set_num_threads(4);out=ROOT/'outputs_nonlinear_endpoint_tuning_v22';parent=ROOT/'outputs_nonlinear_endpoint_v21'
    if out.exists():raise RuntimeError('Preserve prior v22 attempt')
    out.mkdir();save_json(out/'predeclared_grid.json',dict(candidates=GRID,fold=sorted(FOLD),hypothesis='v21 selected alpha/gain at grid boundary on trainingfold; finite extension based on trainingselection, not validation trial errors',selection='Minimum fold equal-participant path RMSE subject to <=5%worstparticipant regression against ridge',products=PRODUCTS,test_evaluated=False))
    pm=json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    for name in ('model.json','run.json','inner_selection.json'):
        if digest(parent/name)!=pm[name]:raise RuntimeError('Changed v21 artifact '+name)
    for name,sha in json.loads((parent/'run.json').read_text())['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed v21 dependency '+name)
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];train=load_train(ROOT/'outputs_motion_endpoint_v16');inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD];clips=bounds(fitrows);systems=normal_system(adapted(fitrows,'physical_products',clips));save_systems(out,'fold_normal_systems',systems,clips,[e['row']['id'] for e in fitrows]);evaluation=adapted(inner,'physical_products',clips)
    (baseline,people,_),_=score(evaluation,{},ZERO,cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates=[dict(ZERO,score=baseline['equal_participant_mean_position_rmse_m'],heading=baseline['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=1.)];alltrials=[];allpeople=[]
    for a in (.01,.03,.1,.3,1.):
        for w in (1.,3.,10.):
            fits=fit(systems,a,w);obj=objective(systems,fits)
            for g in (.25,.5,.75,1.):
                c=dict(basis='physical_products',alpha=a,endpoint_weight=w,gain=g);(summary,ppl,_),records=score(evaluation,fits,c,cfg);result=dict(c,score=summary['equal_participant_mean_position_rmse_m'],heading=summary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in ppl),**obj);candidates.append(result);alltrials.extend([dict(alpha=a,endpoint_weight=w,gain=g,**r) for r in records]);allpeople.extend([dict(alpha=a,endpoint_weight=w,gain=g,**p) for p in ppl]);print('Inner',result,flush=True)
    original=next(c for c in candidates if all(c[k]==v for k,v in ORIGINAL.items()));prior=json.loads((parent/'inner_selection.json').read_text())['selected']
    if abs(original['score']-prior['score'])>1e-8:raise RuntimeError('Original v21 fold reproduction differs')
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),caveat='Inherited base/calibration saw innerparticipants; conditional correction selection only'));write_csv(out/'inner_trials.csv',alltrials);write_csv(out/'inner_participants.csv',allpeople)
    clips=bounds(train);systems=normal_system(adapted(train,'physical_products',clips));save_systems(out,'full_normal_systems',systems,clips,[e['row']['id'] for e in train]);selectedfits=fit(systems,selected['alpha'],selected['endpoint_weight']) if selected['gain'] else {};originalfits=fit(systems,.1,1.);old=json.loads((parent/'model.json').read_text())['fits'];delta=max(float(np.max(np.abs(np.asarray(originalfits[k]['weights'])-old[k]['weights']))) for k in old)
    if delta>1e-6:raise RuntimeError('Original v21 full fit differs')
    save_json(out/'model.json',dict(candidate=selected,fits=selectedfits,feature_clip=clips,products=PRODUCTS,training_ids=[e['row']['id'] for e in train],feature_count=115,v21_original_max_weight_difference=delta))
    del train,inner,fitrows,evaluation,systems
    p14=ROOT/'outputs_stationary_gravity_v14';im=json.loads((p14/'artifact_manifest.json').read_text())['sha256']
    if digest(p14/'initialization.json')!=im['initialization.json']:raise RuntimeError('Changed startup source')
    states={s['id']:s for s in json.loads((p14/'initialization.json').read_text())['records']};cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());manifest=json.loads((source/'artifact_manifest.json').read_text());ridge=load_observed_ridge();validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(sensor);state=states[row['id']]
        if state['partition']!='validation' or state['setup']!=row['setup']:raise RuntimeError('Initialization partition differs')
        x=feature_matrix(sensor,m,cal[row['setup']],state,'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    summaries={};evaluation=adapted(validation,'physical_products',clips)
    for name,f,c in [('cpu_ridge',{},ZERO),('v21_original',originalfits,ORIGINAL),('selected',selectedfits,selected)]:
        (summary,ppl,conditions),records=score(evaluation,f,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',ppl),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    expected=json.loads((parent/'run.json').read_text())['summary']['selected']['equal_participant_mean_position_rmse_m']
    if abs(summaries['v21_original']['equal_participant_mean_position_rmse_m']-expected)>1e-8:raise RuntimeError('Original v21 validation differs')
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=len(validation),test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-started,v21_original_max_weight_difference=delta,normal_system_sha256={name:digest(out/name) for name in ('fold_normal_systems.npz','fold_normal_systems.json','full_normal_systems.npz','full_normal_systems.json')},provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),parent/'artifact_manifest.json',ROOT/'nonlinear_endpoint_experiment_v21.py',ROOT/'motion_endpoint_experiment_v16.py',ROOT/'stationary_gravity_experiment_v14.py',p14/'artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json',ROOT/'observed_ridge_inference.py']}))
    lines=['# Finite physical-product endpoint tuning v22','','Same115feature basis as v21; fixed60candidate extension from boundary choice on trainingfold. Alpha(.01,.03,.1,.3,1), endpointweight(1,3,10), gain(.25,.5,.75,1). Zero and originalv21 eligible. Masked derivative plus observedSE2 endpoint equations, no gap filling.','',f'Selected: {selected}','','| Model | Overall RMSE(mm) | Heading(deg) |','|---|---:|---:|']+[f'| {k} | {s["equal_participant_mean_position_rmse_m"]*1000:.3f} | {s["equal_participant_mean_heading_rmse_deg"]:.3f} |' for k,s in summaries.items()]+['','Fold and full normal systems, bounds, normalization and fit hashes saved for reuse. Originalv21 fold score, full coefficients and validation score reproduced. All473refit before71validationonce. Selected gains may exceedv21damping, but no optical feedback enters inference. Lateral frozenridge. Quoted quadratic fit objectives omit target constant and exclude outputclip/gain; they are not actual trajectory RMSE. Physical products do not prove SI calibration or identifiable slip. Repeated validation remains exploratory; conditionalfold inheritedbase; no test signals.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
