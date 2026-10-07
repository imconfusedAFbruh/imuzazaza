"""Matched component ablation using sealed v25 fitting artifacts, no refitting."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,summarize
from controlled_motion_experiment_v25 import load_train,FOLDS,prepare_features,evaluate
GRID=[dict(name='control',slip_gain=0.,yaw_gain=0.,smooth=0.),dict(name='braking',slip_gain=.5,yaw_gain=0.,smooth=0.),dict(name='braking_yaw',slip_gain=.5,yaw_gain=.25,smooth=0.)]
GRID += [dict(name=f'combined_{lam}',slip_gain=.5,yaw_gain=.25,smooth=lam) for lam in (.0001,.001,.01)]
def main():
    torch.set_num_threads(4);out=ROOT/'outputs_matched_motion_v27';parent=ROOT/'outputs_controlled_motion_v25'
    if out.exists():raise RuntimeError('Preserve matched comparison')
    manifest=json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    for name,sha in manifest.items():
        if digest(parent/name)!=sha:raise RuntimeError('Changed v25 artifact '+name)
    out.mkdir();save_json(out/'predeclared_grid.json',dict(candidates=GRID,scope='Matched braking strength .5, shared train confidence fitted at .25 correction; confidence is heuristic not predictive covariance. v25 observed validation preceded this new ablation, so validation remains exploratory. No refitting/test access.'))
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];train=load_train(ROOT/'outputs_motion_endpoint_v16');rr=[]
    for i,fold in enumerate(FOLDS):
        q=json.loads((parent/f'fold_{i}_model.json').read_text());held=[e for e in train if e['row']['participant'] in fold];entries=prepare_features(held,q['calibration'],q['base'],False)
        for c in GRID:
            (s,_,_),records=evaluate(entries,q['correction'],c,cfg);rr.extend([dict(candidate=c['name'],fold=i,**r) for r in records]);print(i,c['name'],s['equal_participant_mean_position_rmse_m'],flush=True)
    write_csv(out/'fold_trials.csv',rr);base={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in rr if r['candidate']=='control'])[1]};candidates=[]
    for c in GRID:
        s,p,_=summarize([r for r in rr if r['candidate']==c['name']]);candidates.append(dict(c,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(x['mean_trial_position_rmse_m']/base[x['participant']] for x in p)))
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'selection.json',dict(selected=selected,candidates=candidates,selected_before_own_validation=True))
    q=json.loads((parent/'model.json').read_text());entries=[];inventory={r['id']:r for r in json.loads((ROOT/'outputs_amended_v2/inventory.json').read_text())}
    # Reconstruct only IMU-derived entry inputs; scores use the immutable v7 reference.
    from observed_training_experiment import observed_rows
    from observed_ridge_inference import load_observed_ridge
    from stationary_gravity_experiment_v14 import feature_matrix
    from nonlinear_endpoint_experiment_v21 import nonlinear_features
    from controlled_motion_experiment_v25 import sensor
    ridge=load_observed_ridge();states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};sm=json.loads((source/'artifact_manifest.json').read_text())
    for row,d,_ in observed_rows(source,cfg,'validation',sm):
        m=ridge(sensor(d));x=feature_matrix(sensor(d),m,q['calibration'][row['setup']],states[row['id']],'gravity_rotation');entries.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    entries=prepare_features(entries,q['calibration'],q['base'],False);summary={}
    # Report every predeclared matched comparator, not only the favorable one.
    for c in GRID:
        cache=out/c['name']/'trajectories';cache.mkdir(parents=True);(s,p,m),records=evaluate(entries,q['correction'],c,cfg,cache);summary[c['name']]=s
        for suffix,values in [('trials',records),('participants',p),('maneuvers',m)]:write_csv(out/f"{c['name']}_{suffix}.csv",values)
    save_json(out/'run.json',dict(summary=summary,selected=selected,test_evaluated=False,parent_manifest_sha256=digest(parent/'artifact_manifest.json'),source_sha256=digest(Path(__file__))))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
