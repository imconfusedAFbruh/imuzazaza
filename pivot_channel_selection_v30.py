"""Separate pivot forward/lateral controls on conservative and stronger bases."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json,time
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from controlled_motion_experiment_v25 import load_train,FOLDS,prepare_features,corrected,sensor
from best_base_braking_experiment_v28 import entries_for
from rotation_motion_experiment_v29 import inputs
from trajectory_calibration_v10 import integrate
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from nonlinear_endpoint_experiment_v21 import nonlinear_features
GRID=[dict(name=f'{branch}_forward{fv}_lateral{lv}',branch=branch,forward=fv,lateral=lv) for branch in ('conservative','stronger') for fv in (0.,.25,.5,.75,1.) for lv in (0.,.25,.5)]

def make_entries(entries,q,cal,branch):
    if branch=='conservative':es=prepare_features(entries,cal,q['base'],False)
    else:es=entries_for(entries,cal,q['base'])
    result=[]
    c=dict(slip_gain=.5,yaw_gain=0.,smooth=0.)
    for e in es:
        m=corrected(e,q['correction'],c);f=inputs(sensor(e['data']),m,cal[e['setup']]);result.append(dict(e,motion=m,gate=f['gate'],wheel_v=f['wheel_v']))
    return result

def predict(e,c):
    m=e['motion'].copy();g=e['gate'];fg=g*c['forward'];lg=g*c['lateral']
    m[:,0]=(1-fg)*m[:,0]+fg*e['wheel_v'];m[:,1]*=1-lg
    return m

def evaluate(entries,c,cfg,cache=None):
    rr=[]
    for e in entries:
        d=e['data'];m=predict(e,c);xy,h=integrate(d,m);rr.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(d,xy,h,cfg)))
        if cache is not None:np.savez_compressed(cache/(e['row']['id']+'.npz'),t=d['t'],reference_xy=d['gt_xy'],reference_heading=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'],xy=xy,heading=h,motion=m,gate=e['gate'])
    return summarize(rr),rr

def main():
    started=time.perf_counter();torch.set_num_threads(4);out=ROOT/'outputs_pivot_channels_v30';p25=ROOT/'outputs_controlled_motion_v25';p28=ROOT/'outputs_best_base_braking_v28';source=ROOT/'outputs_observed_reference_v7'
    if out.exists():raise RuntimeError('Preserve version')
    for parent in (p25,p28):
        for name,sha in json.loads((parent/'artifact_manifest.json').read_text())['sha256'].items():
            if digest(parent/name)!=sha:raise RuntimeError('Changed parent '+name)
    out.mkdir();save_json(out/'predeclared_grid.json',dict(candidates=GRID,selection='Lowest pooled12personRMSE with <=5%worstpersonregression vs both v25 and originalridge; conservative no-change eligible',scope='Conditional inherited stack. Same fixed reference and initial heading, no trial/person/maneuver-specific rule; no heading flips; parameters chosen on training folds before own validation.'))
    cfg=json.loads((source/'run.json').read_text())['settings'];train=load_train(ROOT/'outputs_motion_endpoint_v16');records=[]
    for i,fold in enumerate(FOLDS):
        held=[e for e in train if e['row']['participant'] in fold];q25=json.loads((p25/f'fold_{i}_model.json').read_text());q28=json.loads((p28/f'fold_{i}_model.json').read_text())
        for branch,q in [('conservative',q25),('stronger',q28)]:
            es=make_entries(held,q,q25['calibration'],branch)
            for c in [c for c in GRID if c['branch']==branch]:
                (s,_,_),rr=evaluate(es,c,cfg);records.extend([dict(candidate=c['name'],fold=i,**r) for r in rr]);print('fold',i,c['name'],s['equal_participant_mean_position_rmse_m'],flush=True)
    write_csv(out/'fold_trials.csv',records)
    base={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in records if r['candidate']=='conservative_forward0.0_lateral0.0'])[1]}
    import csv
    old=[r for r in csv.DictReader((ROOT/'outputs_participant_folds_v24/inner_trials.csv').open()) if r['candidate']=='zero']
    for r in old:
        for k in ('position_rmse_m','heading_rmse_deg'):r[k]=float(r[k])
    original={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize(old)[1]};candidates=[]
    for c in GRID:
        s,p,_=summarize([r for r in records if r['candidate']==c['name']]);candidates.append(dict(c,score=s['equal_participant_mean_position_rmse_m'],worst_vs_v25=max(v['mean_trial_position_rmse_m']/base[v['participant']] for v in p),worst_vs_ridge=max(v['mean_trial_position_rmse_m']/original[v['participant']] for v in p)))
    selected=min([c for c in candidates if c['worst_vs_v25']<=1.05 and c['worst_vs_ridge']<=1.05],key=lambda c:c['score']);save_json(out/'selection.json',dict(selected=selected,candidates=candidates,selected_before_validation=True,test_evaluated=False));print('SELECTED',selected,flush=True)
    q25=json.loads((p25/'model.json').read_text());q28=json.loads((p28/'model.json').read_text());save_json(out/'model.json',dict(candidate=selected,parent='outputs_controlled_motion_v25' if selected['branch']=='conservative' else 'outputs_best_base_braking_v28',parent_manifest_sha256=digest((p25 if selected['branch']=='conservative' else p28)/'artifact_manifest.json'),training_ids=q25['training_ids']));del train
    ridge=load_observed_ridge();states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};sm=json.loads((source/'artifact_manifest.json').read_text());validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',sm):
        m=ridge(sensor(d));x=feature_matrix(sensor(d),m,q25['calibration'][row['setup']],states[row['id']],'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    es=make_entries(validation,q25 if selected['branch']=='conservative' else q28,q25['calibration'],selected['branch']);cache=out/'selected/trajectories';cache.mkdir(parents=True);(s,p,cond),rr=evaluate(es,selected,cfg,cache)
    for suffix,values in [('trials',rr),('participants',p),('maneuvers',cond)]:write_csv(out/f'selected_{suffix}.csv',values)
    save_json(out/'run.json',dict(summary={'selected':s},selected=selected,test_evaluated=False,reference_amended=False,runtime_seconds=time.perf_counter()-started,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),p25/'artifact_manifest.json',p28/'artifact_manifest.json',source/'artifact_manifest.json']}));save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(s,indent=2),flush=True)
if __name__=='__main__':main()
