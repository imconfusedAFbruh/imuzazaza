"""Training-only fully refitted simple estimator; inherited clock/reference prep explicit."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import pipeline as p
from learning import training_group
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD,NEW,load_cache,C,predict
from stationary_gravity_experiment_v14 import initialization,feature_matrix
from nonlinear_endpoint_experiment_v21 import nonlinear_features,bounds,adapted
from motion_endpoint_experiment_v16 import normal_system,fit,score
OUT=p.ROOT/'outputs_simple_point_folds_v50'
GRID=[dict(name='physics',basis='linear',alpha=0.,endpoint_weight=0.,gain=0.),dict(name='linear_point',basis='linear',alpha=1.,endpoint_weight=0.,gain=1.),dict(name='products_point',basis='physical_products',alpha=1.,endpoint_weight=0.,gain=1.),dict(name='linear_endpoint',basis='linear',alpha=1.,endpoint_weight=1.,gain=.5)]
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve completed output')
    OUT.mkdir();protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text());cfg=protocol['old_clock_settings'];fallback=set(protocol['fallback_old_clock_ids'])
    inventory={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())};people=set.union(*FOLDS)
    ids=[id for id in protocol['training_ids'] if inventory[id]['participant'] in people];assert len(ids)==207
    p.save_json(OUT/'protocol.json',dict(hypothesis='Fold-refitted empirical physics plus endpoint ridge tests simpler estimation without inherited learned base or calibration',training_ids=ids,folds=[sorted(f) for f in FOLDS],scope='Only207identifiedtargettrainingrecords; earlier identity-unlinked data excluded. Calibration/axes/scales/gravity/bias/base/normalization/clips/correction exclude held people. Frozen reference geometry/QC and TRAIN-assisted clock prep remain inherited; not completely independent synchronization.',parameters=GRID,validation_accessed=False,test_accessed=False,selection=False))
    manifests={src:json.loads((src/'artifact_manifest.json').read_text()) for src in (OLD,NEW)};trials=[]
    for id in ids:
        row=inventory[id];assert row['partition']=='train';src=OLD if id in fallback else NEW;d,_=load_cache(src,id,manifests[src]);trials.append((row,d,{}))
    records=[]
    for fold,held in enumerate(FOLDS):
        fitting=[q for q in trials if q[0]['participant'] not in held];cal=p.calibrate(fitting,cfg);p.save_json(OUT/f'fold_{fold}_calibration.json',cal);entries=[]
        for row,d,_ in trials:
            state=initialization(row,cal,cfg);v=p.velocities(d,cal[row['setup']]);m=np.c_[v[:,0],np.zeros(len(v)),v[:,1]];x=feature_matrix(d,m,cal[row['setup']],state,'gravity_rotation');label=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])
            entries.append(dict(row=row,data=d,motion=m,linear=x,nonlinear=nonlinear_features(x),label=label,target=np.c_[d['gt_v'],d['gt_yaw']]-m[:,[0,2]],setup=row['setup'],group=training_group(row)))
        fitentries=[e for e in entries if e['row']['participant'] not in held];evaluation=[e for e in entries if e['row']['participant'] in held];clips=bounds(fitentries);fits=fit(normal_system(adapted(fitentries,C['basis'],clips)),C['alpha'],C['endpoint_weight'])
        p.save_json(OUT/f'fold_{fold}_model.json',dict(fits=fits,feature_clip=clips,fit_ids=[e['row']['id'] for e in fitentries],held_ids=[e['row']['id'] for e in evaluation]))
        for c in GRID:
            f=fit(normal_system(adapted(fitentries,c['basis'],clips)),c['alpha'],c['endpoint_weight']) if c['gain'] else {}
            (_,_,_),rr=score(adapted(evaluation,c['basis'],clips),f,c,cfg);records.extend([dict(fold=fold,method=c['name'],**r) for r in rr]);p.save_json(OUT/f"fold_{fold}_{c['name']}_model.json",dict(candidate=c,fits=f,feature_clip=clips,fit_ids=[e['row']['id'] for e in fitentries]))
        print('Completed independent estimator fold',fold,flush=True)
    p.write_csv(OUT/'trials.csv',records);summaries={};persons={}
    for name in sorted({r['method'] for r in records}):
        s,pp,mm=p.summarize([r for r in records if r['method']==name]);summaries[name]=s;persons[name]={q['participant']:q['mean_trial_position_rmse_m'] for q in pp};p.write_csv(OUT/(name+'_participants.csv'),pp);p.write_csv(OUT/(name+'_maneuvers.csv'),mm)
    ratios={name:{q:persons[name][q]/v for q,v in persons['physics'].items()} for name in persons}; candidates=[dict(name=name,score=summaries[name]['equal_participant_mean_position_rmse_m'],worst_ratio=max(ratios[name].values())) for name in persons]; selected=min([q for q in candidates if q['worst_ratio']<=1.05],key=lambda q:q['score'])
    p.save_json(OUT/'run.json',dict(summary=summaries,participant_ratios=ratios,candidates=candidates,selected=selected,validation_accessed=False,test_accessed=False,training_records=207,base_calibration_refitted=True,clock_reference_preparation_refitted=False,runtime_s=time.perf_counter()-start))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(q.relative_to(OUT)):p.digest(q) for q in OUT.rglob('*') if q.is_file()}));print(json.dumps(summaries,indent=2),flush=True)
if __name__=='__main__':main()
