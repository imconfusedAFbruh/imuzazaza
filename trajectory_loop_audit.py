"""Independent CPU numerical and structural audit of sealed trajectory models."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json,csv
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted,FOLD
from motion_endpoint_iterative_v19 import audit as jacobian_audit
from nonlinear_endpoint_inference_v21 import load_nonlinear_endpoint
from motion_endpoint_inference_v16 import load_motion_endpoint
from observed_training_experiment import observed_rows
from trajectory_calibration_v10 import integrate

class ReferenceSentinel:
    def __array__(self,*args,**kwargs):raise RuntimeError('Inference touched poisoned reference')

def main():
    out=ROOT/'outputs_trajectory_loop_audit'
    if out.exists():raise RuntimeError('Preserve audit')
    out.mkdir();torch.set_num_threads(4);p16=ROOT/'outputs_motion_endpoint_v16';p21=ROOT/'outputs_nonlinear_endpoint_v21';training=load_train(p16);fitrows=[e for e in training if e['row']['participant'] not in FOLD];inner=[e for e in training if e['row']['participant'] in FOLD];clipped=bounds(training);fold_clips=bounds(fitrows);model21=json.loads((p21/'model.json').read_text());clipdiff=max(float(np.max(np.abs(np.array(clipped[k][v])-model21['feature_clip'][k][v]))) for k in clipped for v in ('low','high'));fold_full_clip_difference=max(float(np.max(np.abs(np.array(fold_clips[k][v])-clipped[k][v]))) for k in clipped for v in ('low','high'));idsfit={e['row']['participant'] for e in fitrows};idsinner={e['row']['participant'] for e in inner}
    if idsfit&idsinner or idsinner!=FOLD:raise RuntimeError('Participantfold overlap')
    if clipdiff>1e-8:raise RuntimeError('Trainingclip boundsnotreproduced')
    numeric_entries=adapted(training,'physical_products',clipped);models={k:dict(mean=np.array(v['mean']),std=np.array(v['std']),weights=.5*np.array(v['weights']),cap=.5*np.array(v['cap'])) for k,v in model21['fits'].items()};jacobian=jacobian_audit(numeric_entries,models)
    pair_stats=[]
    for e in training:
        d=e['data'];m=e['motion'];t=d['t'];h=np.r_[0,np.cumsum(np.diff(t)*(m[:-1,2]+m[1:,2])/2)];bad=np.r_[0,np.cumsum(~d['imu_valid'])];pairs=0;gaps=0;wraps=0;max_raw=0.
        for a in range(0,len(t),100):
            if not d['gt_valid'][a]:continue
            for horizon in (100,300,500,1000):
                b=a+horizon
                if b>=len(t) or not d['gt_valid'][b] or bad[b+1]!=bad[a]:continue
                pairs+=1;gaps+=int(not d['gt_valid'][a:b+1].all());err=d['gt_heading'][b]-d['gt_heading'][a]-(h[b]-h[a]);wraps+=int(abs(err)>np.pi);max_raw=max(max_raw,abs(err))
        pair_stats.append(dict(id=e['row']['id'],participant=e['row']['participant'],endpoint_pairs=pairs,optical_gap_bridging_pairs=gaps,raw_yaw_residual_beyond_pi_pairs=wraps,max_abs_raw_yaw_residual_rad=max_raw))
    del training,fitrows,inner,numeric_entries
    states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());predictors={'v16':load_motion_endpoint(),'v21':load_nonlinear_endpoint()};expected={};records=[];maxdiff={k:0. for k in predictors};poison_diff={k:0. for k in predictors}
    for name,folder,file in [('v16',p16,'endpoint_trials.csv'),('v21',p21,'selected_trials.csv')]:expected[name]={r['id']:r for r in csv.DictReader((folder/file).open())}
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};sensor['initialization']=states[row['id']]
        for name,predict in predictors.items():
            motion=predict(sensor);poison=dict(sensor,gt_xy=ReferenceSentinel(),gt_heading=ReferenceSentinel(),gt_v=ReferenceSentinel(),gt_yaw=ReferenceSentinel(),gt_valid=ReferenceSentinel(),label_valid=ReferenceSentinel());m2=predict(poison);poison_diff[name]=max(poison_diff[name],float(np.max(np.abs(m2-motion))));xy,h=integrate(d,motion);score=metrics(d,xy,h,cfg);maxdiff[name]=max(maxdiff[name],abs(score['position_rmse_m']-float(expected[name][row['id']]['position_rmse_m'])));records.append(dict(model=name,id=row['id'],participant=row['participant'],condition=row['condition'],**score))
    if max(maxdiff.values())>1e-8 or max(poison_diff.values())>0:raise RuntimeError('Inferenceintegrityfailed')
    summary={name:summarize([r for r in records if r['model']==name])[0] for name in predictors};write_csv(out/'reproduced_trials.csv',records);write_csv(out/'training_endpoint_support.csv',pair_stats);save_json(out/'audit.json',dict(summary=summary,training_files=473,fold_fit_people=sorted(idsfit),fold_holdout_people=sorted(idsinner),participant_overlap=False,train_full_clip_reproduction_max_difference=clipdiff,fit_vs_full_clip_max_difference=fold_full_clip_difference,jacobian=jacobian,validation_trials_per_model=71,inference_poison_max_difference=poison_diff,sealed_trial_score_max_difference_m=maxdiff,endpoint_pairs=sum(r['endpoint_pairs'] for r in pair_stats),optical_gap_bridging_pairs=sum(r['optical_gap_bridging_pairs'] for r in pair_stats),raw_yaw_residual_beyond_pi_pairs=sum(r['raw_yaw_residual_beyond_pi_pairs'] for r in pair_stats),test_evaluated=False,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'motion_endpoint_experiment_v16.py',ROOT/'nonlinear_endpoint_experiment_v21.py',ROOT/'motion_endpoint_iterative_v19.py',ROOT/'motion_endpoint_inference_v16.py',ROOT/'nonlinear_endpoint_inference_v21.py',ROOT/'motion_endpoint_iterative_inference_v19.py',p16/'artifact_manifest.json',p21/'artifact_manifest.json']}));save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(dict(summary=summary,maxdiff=maxdiff,poison_diff=poison_diff,jacobian=jacobian),indent=2))
if __name__=='__main__':main()
