"""Damp empirical dynamic-tilt correction using three training-participant folds."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','3')
import json,time
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted
from dynamic_tilt_experiment_v33 import dynamic_features,clips_extra,expanded,C
from participant_folds_experiment_v24 import FOLDS
from motion_endpoint_experiment_v16 import normal_system,fit
from stationary_gravity_experiment_v14 import correction
from trajectory_calibration_v10 import integrate
from observed_training_experiment import observed_rows

OUT=ROOT/'outputs_dynamic_blend_v34';WEIGHTS=(0.,.25,.5,.75)
def corrected_entry(e,fits):return correction(dict(e,x={'gravity_rotation':e['x']}),fits,dict(C,mode='gravity_rotation'))

def main():
    started=time.perf_counter();torch.set_num_threads(3)
    if OUT.exists():raise RuntimeError('Preserve experiment')
    OUT.mkdir();source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());states={q['id']:q for q in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
    save_json(OUT/'protocol.json',dict(cutoff_hz=.3,weights=WEIGHTS,selection='Minimum pooled12trainingparticipant trajectoryRMSE, <=5%worstpersonregressionagainstsamefoldv21. Zero eligible. Selectedbeforevalidation.',rationale='v33 dynamic0.3 cut chosen from lower TRAINfold mean131.460 vs132.444mm. Undampedcandidateviolatedtrainingguard;dampingisnewtrainingselectedhypothesis.',scope='Conditional inheritedbase/calibration; no opticalfeedback, no participant-specific inference',test_accessed=False))
    train=load_train(ROOT/'outputs_motion_endpoint_v16');records=[]
    for i,fold in enumerate(FOLDS):
        fitting=[e for e in train if e['row']['participant'] not in fold];held=[e for e in train if e['row']['participant'] in fold];clips=bounds(fitting)
        for e in fitting+held:e['extra']=dynamic_features(e['data'],e['motion'],cal[e['setup']],states[e['row']['id']],.3)
        extra=clips_extra(fitting);basefits=fit(normal_system(adapted(fitting,C['basis'],clips)),.1,1.);tiltfits=fit(normal_system(expanded(fitting,clips,extra)),.1,1.)
        save_json(OUT/f'fold_{i}_models.json',dict(original=basefits,tilt=tiltfits,feature_clip=clips,extra_clip=extra,fit_ids=[e['row']['id'] for e in fitting],held_people=sorted(fold)))
        original=adapted(held,C['basis'],clips);tilt=expanded(held,clips,extra)
        for e,new in zip(original,tilt):
            m0=corrected_entry(e,basefits);m1=corrected_entry(new,tiltfits)
            for w in WEIGHTS:
                m=(1-w)*m0+w*m1;xy,h=integrate(e['data'],m);records.append(dict(weight=w,fold=i,id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(e['data'],xy,h,cfg)))
        print('Completed trainingfold',i,flush=True)
    write_csv(OUT/'fold_trials.csv',records);baseline={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in records if r['weight']==0])[1]};choices=[]
    for w in WEIGHTS:
        s,p,_=summarize([r for r in records if r['weight']==w]);choices.append(dict(weight=w,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(q['mean_trial_position_rmse_m']/baseline[q['participant']] for q in p)))
    selected=min([q for q in choices if q['worst_person_ratio']<=1.05],key=lambda q:q['score']);save_json(OUT/'selection.json',dict(selected=selected,candidates=choices,selected_before_validation=True));print('SELECTED',selected,flush=True)
    del train,fitting,held,original,tilt
    parent=ROOT/'outputs_dynamic_tilt_v33';parentmanifest=json.loads((parent/'artifact_manifest.json').read_text())['sha256'];w=selected['weight'];save_json(OUT/'model.json',dict(weight=w,original_parent='outputs_nonlinear_endpoint_v21/model.json',dynamic_parent='outputs_dynamic_tilt_v33/tilt_0.3_model.json',original_sha256=digest(ROOT/'outputs_nonlinear_endpoint_v21/model.json'),dynamic_sha256=digest(parent/'tilt_0.3_model.json'),feature_source_sha256=digest(ROOT/'dynamic_tilt_experiment_v33.py'),training_ids=json.loads((parent/'tilt_0.3_model.json').read_text())['training_ids'],interpretation='Blend IMU-only predicted motion vectors then integrate, never blend positions to evaluated truth'))
    cache=OUT/'trajectories';cache.mkdir();sm=json.loads((source/'artifact_manifest.json').read_text());rr={'original_v21':[],'selected_blend':[]}
    for row,d,_ in observed_rows(source,cfg,'validation',sm):
        path=parent/'trajectories'/(row['id']+'.npz')
        if digest(path)!=parentmanifest[str(path.relative_to(parent))]:raise RuntimeError('Changed prediction')
        with np.load(path) as z:m0=z['original_v21_motion'];m1=z['tilt_0.3_motion']
        arrays=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'])
        for name,m in [('original_v21',m0),('selected_blend',(1-w)*m0+w*m1)]:
            xy,h=integrate(d,m);rr[name].append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,cfg)));arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h;arrays[name+'_motion']=m
        np.savez_compressed(cache/(row['id']+'.npz'),**arrays)
    summaries={}
    for name,records in rr.items():
        summaries[name],p,cond=summarize(records)
        for suffix,values in [('trials',records),('participants',p),('maneuvers',cond)]:write_csv(OUT/f'{name}_{suffix}.csv',values)
    save_json(OUT/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=71,test_accessed=False,base_refit=False,runtime_seconds=time.perf_counter()-started,source_sha256=digest(Path(__file__))));save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
