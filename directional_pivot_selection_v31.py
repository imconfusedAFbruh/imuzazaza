"""Directional pivot ablation with a stricter participant/maneuver guard."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json,time,csv
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from controlled_motion_experiment_v25 import load_train,FOLDS,sensor
from pivot_channel_selection_v30 import make_entries
from trajectory_calibration_v10 import integrate
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from nonlinear_endpoint_experiment_v21 import nonlinear_features
GRID=[dict(name=f'positive{p}_negative{n}',positive=p,negative=n) for p in (0.,.25,.5,.75,1.) for n in (0.,.25,.5,.75,1.)]
def predict(e,c):
    m=e['motion'].copy();g=e['gate']*np.where(m[:,2]>=0,c['positive'],c['negative']);m[:,0]=(1-g)*m[:,0]+g*e['wheel_v'];return m
def evaluate(entries,c,cfg,cache=None):
    rr=[]
    for e in entries:
        d=e['data'];m=predict(e,c);xy,h=integrate(d,m);rr.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(d,xy,h,cfg)))
        if cache is not None:np.savez_compressed(cache/(e['row']['id']+'.npz'),t=d['t'],reference_xy=d['gt_xy'],reference_heading=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'],xy=xy,heading=h,motion=m,gate=e['gate'])
    return summarize(rr),rr
def cells(rr):
    result={}
    for r in rr:result.setdefault((r['participant'],r['condition']),[]).append(float(r['position_rmse_m']))
    return {k:float(np.mean(v)) for k,v in result.items()}
def main():
    started=time.perf_counter();torch.set_num_threads(4);out=ROOT/'outputs_directional_pivot_v31';parent=ROOT/'outputs_controlled_motion_v25';source=ROOT/'outputs_observed_reference_v7'
    if out.exists():raise RuntimeError('Preserve run')
    out.mkdir();save_json(out/'predeclared_grid.json',dict(candidates=GRID,scope='IMU yaw sign distinguishes directions. No maneuver/person/date ID for gating. Lateral/yaw preserved. No reference flips.',selection='Lowest pooled12personRMSE subject <=5%worstpersonand<=5%worstparticipant-maneuver-cell regression versus v25, and <=5%worstpersonvs originalridge; control eligible. Conditional inherited stack.'))
    cfg=json.loads((source/'run.json').read_text())['settings'];train=load_train(ROOT/'outputs_motion_endpoint_v16');rr=[]
    for i,fold in enumerate(FOLDS):
        q=json.loads((parent/f'fold_{i}_model.json').read_text());held=[e for e in train if e['row']['participant'] in fold];es=make_entries(held,q,q['calibration'],'conservative')
        for c in GRID:
            (s,_,_),r=evaluate(es,c,cfg);rr.extend([dict(candidate=c['name'],fold=i,**x) for x in r]);print('fold',i,c['name'],s['equal_participant_mean_position_rmse_m'],flush=True)
    write_csv(out/'fold_trials.csv',rr);control=[r for r in rr if r['candidate']=='positive0.0_negative0.0'];people={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize(control)[1]};cell=cells(control)
    original=[r for r in csv.DictReader((ROOT/'outputs_participant_folds_v24/inner_trials.csv').open()) if r['candidate']=='zero']
    for r in original:
        for k in ('position_rmse_m','heading_rmse_deg'):r[k]=float(r[k])
    ridge={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize(original)[1]};candidates=[]
    for c in GRID:
        records=[r for r in rr if r['candidate']==c['name']];s,p,_=summarize(records);cc=cells(records);candidates.append(dict(c,score=s['equal_participant_mean_position_rmse_m'],worst_person=max(x['mean_trial_position_rmse_m']/people[x['participant']] for x in p),worst_cell=max(cc[k]/cell[k] for k in cc),worst_vs_ridge=max(x['mean_trial_position_rmse_m']/ridge[x['participant']] for x in p)))
    selected=min([c for c in candidates if max(c['worst_person'],c['worst_cell'],c['worst_vs_ridge'])<=1.05],key=lambda c:c['score']);save_json(out/'selection.json',dict(selected=selected,candidates=candidates,selected_before_validation=True,test_evaluated=False));print('SELECTED',selected,flush=True);del train
    q=json.loads((parent/'model.json').read_text());save_json(out/'model.json',dict(candidate=selected,training_ids=q['training_ids'],parent_manifest_sha256=digest(parent/'artifact_manifest.json')))
    ridge=load_observed_ridge();states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};sm=json.loads((source/'artifact_manifest.json').read_text());validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',sm):
        m=ridge(sensor(d));x=feature_matrix(sensor(d),m,q['calibration'][row['setup']],states[row['id']],'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    es=make_entries(validation,q,q['calibration'],'conservative');cache=out/'selected/trajectories';cache.mkdir(parents=True);(s,p,cond),records=evaluate(es,selected,cfg,cache)
    for suffix,values in [('trials',records),('participants',p),('maneuvers',cond)]:write_csv(out/f'selected_{suffix}.csv',values)
    save_json(out/'run.json',dict(summary={'selected':s},selected=selected,test_evaluated=False,reference_amended=False,runtime_seconds=time.perf_counter()-started,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),parent/'artifact_manifest.json',ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',source/'artifact_manifest.json']}));save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(s,indent=2),flush=True)
if __name__=='__main__':main()
