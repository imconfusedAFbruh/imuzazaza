"""Three predeclared participant folds for conditional endpoint correction selection."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,summarize
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted,nonlinear_features
from motion_endpoint_experiment_v16 import normal_system,fit,score
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix

FOLDS=[{'No.3','No.8','No.15','No.20'},{'No.1','No.4','No.13','No.16'},{'No.6','No.7','No.17','No.19'}]
GRID=[dict(name='zero',basis='zero',alpha=0.,endpoint_weight=0.,gain=0.),
      dict(name='linear_v16',basis='linear',alpha=.1,endpoint_weight=1.,gain=.5),
      dict(name='nonlinear_v21',basis='physical_products',alpha=.1,endpoint_weight=1.,gain=.5),
      dict(name='conservative',basis='physical_products',alpha=.3,endpoint_weight=1.,gain=.25),
      dict(name='endpoint3',basis='physical_products',alpha=.1,endpoint_weight=3.,gain=.5),
      dict(name='aggressive_v22',basis='physical_products',alpha=.01,endpoint_weight=10.,gain=.75)]

def main():
    started=time.perf_counter();torch.set_num_threads(4);out=ROOT/'outputs_participant_folds_v24'
    if out.exists():raise RuntimeError('Preserve prior run')
    out.mkdir();save_json(out/'predeclared_grid.json',dict(folds=[sorted(f) for f in FOLDS],candidates=GRID,selection='Pooled12equalparticipantmean with <=5%worstperson regression vsridge',caveat='Inherited calibration/base conditional; earlier rows always fit'))
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];train=load_train(ROOT/'outputs_motion_endpoint_v16');records=[]
    for i,fold in enumerate(FOLDS):
        held=[e for e in train if e['row']['participant'] in fold];fitting=[e for e in train if e['row']['participant'] not in fold];clips=bounds(fitting)
        for basis in ('zero','linear','physical_products'):
            systems=normal_system(adapted(fitting,basis,clips)) if basis!='zero' else None;evaluation=adapted(held,basis,clips)
            for c in [c for c in GRID if c['basis']==basis]:
                fits=fit(systems,c['alpha'],c['endpoint_weight']) if c['gain'] else {};(_,_,_),trials=score(evaluation,fits,c,cfg)
                records.extend([dict(candidate=c['name'],fold=i,**r) for r in trials]);print('Fold',i,c['name'],summarize(trials)[0]['equal_participant_mean_position_rmse_m'],flush=True)
        del systems,evaluation,fitting,held
    baseline={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in records if r['candidate']=='zero'])[1]};candidates=[]
    for c in GRID:
        summary,people,_=summarize([r for r in records if r['candidate']==c['name']]);candidates.append(dict(c,score=summary['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/baseline[p['participant']] for p in people)))
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,folds=[sorted(f) for f in FOLDS],caveat='Conditional inherited calibration/base; validation reused exploratory'));write_csv(out/'inner_trials.csv',records);print('SELECTED',selected,flush=True)
    clips=bounds(train) if selected['basis']=='physical_products' else {};fits=fit(normal_system(adapted(train,selected['basis'],clips)),selected['alpha'],selected['endpoint_weight']) if selected['gain'] else {}
    save_json(out/'model.json',dict(candidate=selected,fits=fits,feature_clip=clips,training_ids=[e['row']['id'] for e in train]));del train,records
    parent14=ROOT/'outputs_stationary_gravity_v14';manifest=json.loads((source/'artifact_manifest.json').read_text());pm=json.loads((parent14/'artifact_manifest.json').read_text())['sha256']
    if digest(parent14/'initialization.json')!=pm['initialization.json']:raise RuntimeError('Changed startup initialization')
    states={r['id']:r for r in json.loads((parent14/'initialization.json').read_text())['records']};cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge();validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(sensor);state=states[row['id']]
        if state['partition']!='validation' or state['setup']!=row['setup']:raise RuntimeError('Startup identity differs')
        x=feature_matrix(sensor,m,cal[row['setup']],state,'gravity_rotation');validation.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']))
    summaries={}
    for name,f,c in [('cpu_ridge',{},GRID[0]),('selected',fits,selected)]:
        (s,p,conditions),trials=score(adapted(validation,c['basis'],clips),f,c,cfg);summaries[name]=s
        for suffix,rows in [('trials',trials),('participants',p),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=len(validation),test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-started,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',ROOT/'nonlinear_endpoint_experiment_v21.py',ROOT/'motion_endpoint_experiment_v16.py',ROOT/'stationary_gravity_experiment_v14.py',parent14/'artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json',ROOT/'observed_ridge_inference.py']}))
    (out/'report.md').write_text('# Three participant folds v24\n\nSelected before validation: '+json.dumps(selected)+'\n\n'+json.dumps(summaries,indent=2)+'\n\nNew correction preprocessing and coefficients exclude each held participant. Inherited calibration/base previously saw these training people: conditional selection. Reused validation exploratory; no test data. Earlier training rows always remain fit.\n',encoding='utf-8')
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
