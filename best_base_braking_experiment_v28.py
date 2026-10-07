"""Finite braking-only extension of v21, with guard against original ridge."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json,time
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,save_json,write_csv,digest,summarize
from controlled_motion_experiment_v25 import load_train,FOLDS,prepare_features,predict_affine,constrained_slip_fit,evaluate,sensor
from nonlinear_endpoint_experiment_v21 import bounds,adapted,nonlinear_features
from motion_endpoint_experiment_v16 import normal_system,fit
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
GRID=[dict(name=f'braking_{g}',slip_gain=g,yaw_gain=0.,smooth=0.) for g in (0.,.25,.5)]
def entries_for(entries,cal,base):
    moved=[dict(e,motion=predict_affine(e,base,gain=.5)) for e in entries]
    return prepare_features(moved,cal,None,False)
def main():
    torch.set_num_threads(4);out=ROOT/'outputs_best_base_braking_v28'
    if out.exists():raise RuntimeError('Preserve run')
    out.mkdir();save_json(out/'predeclared_grid.json',dict(candidates=GRID,base='v21 alpha .1 / endpoint1 / gain.5 refitted within correction folds; inherited neural/calibration conditional',selection='Lowest pooled12participantRMSE with <=5% worstperson regression vs originalridge. v24 fallback if none pass. No validation-based parameter selection.'))
    start=time.perf_counter();source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());train=load_train(ROOT/'outputs_motion_endpoint_v16');rr=[];ridge=[]
    for i,fold in enumerate(FOLDS):
        fitting=[e for e in train if e['row']['participant'] not in fold];held=[e for e in train if e['row']['participant'] in fold];clips=bounds(fitting);base=dict(fits=fit(normal_system(adapted(fitting,'physical_products',clips)),.1,1.),feature_clip=clips)
        f=entries_for(fitting,cal,base);h=entries_for(held,cal,base);model=dict(slip=constrained_slip_fit(f));save_json(out/f'fold_{i}_model.json',dict(base=base,correction=model,held_participants=sorted(fold),fit_ids=[e['row']['id'] for e in fitting]))
        (_,_,_),r=evaluate(held,{},dict(slip_gain=0,yaw_gain=0,smooth=0),cfg);ridge.extend(r)
        for c in GRID:
            (s,_,_),r=evaluate(h,model,c,cfg);rr.extend([dict(candidate=c['name'],fold=i,**x) for x in r]);print('v28 fold',i,c['name'],s['equal_participant_mean_position_rmse_m'],flush=True)
    write_csv(out/'fold_trials.csv',rr);basep={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize(ridge)[1]};candidates=[]
    for c in GRID:
        s,p,_=summarize([r for r in rr if r['candidate']==c['name']]);candidates.append(dict(c,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(x['mean_trial_position_rmse_m']/basep[x['participant']] for x in p)))
    fallback=json.loads((ROOT/'outputs_participant_folds_v24/inner_selection.json').read_text())['selected'];eligible=[c for c in candidates if c['worst_person_ratio']<=1.05];selected=min(eligible,key=lambda c:c['score']) if eligible else None
    promote=selected is not None and selected['score']<fallback['score'];save_json(out/'selection.json',dict(candidates=candidates,selected=selected,passes_original_ridge_guard=bool(eligible),preferred_over_v24_on_training_folds=promote,fallback=fallback,selected_before_validation=True))
    clips=bounds(train);base=dict(fits=fit(normal_system(adapted(train,'physical_products',clips)),.1,1.),feature_clip=clips);entries=entries_for(train,cal,base);model=dict(slip=constrained_slip_fit(entries));save_json(out/'model.json',dict(base=base,correction=model,calibration=cal,selected=selected,training_ids=[e['row']['id'] for e in train]));del train,entries
    sm=json.loads((source/'artifact_manifest.json').read_text());ridge=load_observed_ridge();states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',sm):
        m=ridge(sensor(d));x=feature_matrix(sensor(d),m,cal[row['setup']],states[row['id']],'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    entries=entries_for(validation,cal,base);summary={}
    for c in GRID:
        cache=out/c['name']/'trajectories';cache.mkdir(parents=True);(s,p,conds),r=evaluate(entries,model,c,cfg,cache);summary[c['name']]=s
        for suffix,values in [('trials',r),('participants',p),('maneuvers',conds)]:write_csv(out/f"{c['name']}_{suffix}.csv",values)
    save_json(out/'run.json',dict(summary=summary,selection=json.loads((out/'selection.json').read_text()),test_evaluated=False,runtime_seconds=time.perf_counter()-start,source_sha256=digest(Path(__file__)),scope='Conditional inherited base/calibration; finite trainingfold selection. Validation reused exploratory.'))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
