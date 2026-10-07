"""Restore discarded individual wheel fits and test differential-drive yaw."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,time,copy
from pathlib import Path
import numpy as np
from pipeline import ROOT,robust_line,velocities,metrics,summarize,digest,save_json,write_csv
from trajectory_calibration_v10 import integrate
from participant_folds_experiment_v24 import FOLDS
from observed_training_experiment import observed_rows
OUT=ROOT/'outputs_physical_wheel_v38';WEIGHTS=(0.,.25,.5,.75,1.)
def read(p):return json.loads(p.read_text())
def restore_individual(trials,joint,cfg):
    model=copy.deepcopy(joint)
    for setup,q in model.items():
        chosen=[t for t in trials if t[0]['setup']==setup];assert {r['id'] for r,d,_ in chosen}==set(q['training_trials'])
        raw=np.concatenate([d['raw'][d['label_valid']][::5] for r,d,_ in chosen]);v=np.concatenate([d['gt_v'][d['label_valid']][::5] for r,d,_ in chosen]);yaw=np.concatenate([d['gt_yaw'][d['label_valid']][::5] for r,d,_ in chosen])
        for side,sign in [(0,-1),(1,1)]:
            old=q['terms'][side];fit=robust_line(raw[:,old['column']],v+sign*cfg['track_width_m']*yaw/2);old.update(fit,fit_objective='Individual rigid differential-drive rim velocity v±L*yaw/2; physical .52m track assumed')
    return model
def motion(d,q,weight,joint=None):
    if joint is not None:
        v=velocities(d,joint);return np.c_[v[:,0],np.zeros(len(v)),v[:,1]]
    wheels=[d['raw'][:,p['column']]*p['scale']+p['intercept'] for p in q['terms'][:2]];center=d['raw'][:,q['terms'][2]['column']]*q['terms'][2]['scale']+q['terms'][2]['intercept'];yaw=(wheels[1]-wheels[0])/q['track_width_m'];return np.c_[(wheels[0]+wheels[1])/2,np.zeros(len(center)),(1-weight)*center+weight*yaw]
def scores(row,d,name,m,cfg,fold=None):
    xy,h=integrate(d,m);return dict(candidate=name,fold=fold,id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,cfg))
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve experiment')
    OUT.mkdir();cfg=read(ROOT/'outputs_observed_reference_v7/run.json')['settings'];p=ROOT/'outputs_motion_endpoint_v16';manifest=read(p/'artifact_manifest.json')['sha256'];train=[]
    for path in sorted((p/'prepared_training').glob('*.npz')):
        meta=path.with_suffix('.json')
        for f in (path,meta):assert digest(f)==manifest[str(f.relative_to(p))]
        r=read(meta)['row'];assert r['partition']=='train'
        with np.load(path) as z:d={k:z[k] for k in ['setup','t','raw','imu_valid','gt_xy','gt_heading','gt_v','gt_yaw','gt_valid','label_valid']}
        train.append((r,d,{}))
    assert len(train)==473
    calout=ROOT/'outputs_calibration_fold_v37';seal=read(calout/'artifact_manifest.json')['sha256']
    for f in ['all473_observed_calibration.json',*[f'fold_{i}_calibration.json' for i in range(3)]]:assert digest(calout/f)==seal[f]
    save_json(OUT/'protocol.json',dict(hypothesis='Joint midpoint coefficients discarded individual wheel dynamics; fitting v±L*yaw/2 may recover useful gyro-independent yaw',weights=WEIGHTS,track_m=.52,axis_selection='Reuse exact axes chosen only on each fitting subset by pipeline.calibrate',individual_fit='Six-pass robust_line on each rim-speed target; training derivative labels sampled every5frames; center gyro stays same fitting-only calibration',selection='Three conditional training folds: equal12person mean; <=5%worstperson regression against joint midpoint speed+center yaw. Baseline eligible. Selection saved before validation.',scope='Raw physics measurement audit with inherited clocks/referencegeometry and no residual model. No test or arbitrary trajectory transformations. Units empirical; true rigid track and nonholonomic wheel targets remain assumptions.'))
    rows=[];fitstats=[]
    for i,heldpeople in enumerate(FOLDS):
        fitting=[t for t in train if t[0]['participant'] not in heldpeople];held=[t for t in train if t[0]['participant'] in heldpeople];joint=read(calout/f'fold_{i}_calibration.json');ind=restore_individual(fitting,joint,cfg);save_json(OUT/f'fold_{i}_individual_calibration.json',ind)
        for setup in ind:
            for side in (0,1):
                a,b=joint[setup]['terms'][side],ind[setup]['terms'][side];fitstats.append(dict(fold=i,setup=setup,side=side,axis=b['axis'],joint_scale=a['scale'],individual_scale=b['scale'],joint_intercept=a['intercept'],individual_intercept=b['intercept'],scale_change_percent=100*(b['scale']/a['scale']-1),individual_fit_mse=b['mse']))
        for r,d,_ in held:
            rows.append(scores(r,d,'joint_center',motion(d,None,None,joint[r['setup']]),cfg,i))
            for w in WEIGHTS:rows.append(scores(r,d,f'individual_yaw_{w}',motion(d,ind[r['setup']],w),cfg,i))
        print('Individual wheel fold',i,flush=True)
    write_csv(OUT/'fold_trials.csv',rows);write_csv(OUT/'fit_terms.csv',fitstats);base={r['participant']:r['mean_trial_position_rmse_m'] for r in summarize([r for r in rows if r['candidate']=='joint_center'])[1]};candidates=[]
    for name in ['joint_center',*[f'individual_yaw_{w}' for w in WEIGHTS]]:
        s,p,c=summarize([r for r in rows if r['candidate']==name]);candidates.append(dict(candidate=name,score=s['equal_participant_mean_position_rmse_m'],heading=s['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(r['mean_trial_position_rmse_m']/base[r['participant']] for r in p)))
        for suffix,rr in [('participants',p),('maneuvers',c)]:write_csv(OUT/f'fold_{name}_{suffix}.csv',rr)
    selected=min((c for c in candidates if c['worst_person_ratio']<=1.05),key=lambda c:c['score']);save_json(OUT/'selection.json',dict(selected=selected,candidates=candidates,selected_before_validation=True));print('Selected',selected,flush=True)
    validation={};promising=selected['candidate']!='joint_center' and selected['score']<candidates[0]['score']
    if promising:
        joint=read(calout/'all473_observed_calibration.json');ind=restore_individual(train,joint,cfg);save_json(OUT/'full_individual_calibration.json',ind);weight=float(selected['candidate'].split('_')[-1]);source=ROOT/'outputs_observed_reference_v7';sm=read(source/'artifact_manifest.json');vr=[];cache=OUT/'trajectories';cache.mkdir()
        for r,d,_ in observed_rows(source,cfg,'validation',sm):
            arr=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'])
            for name,m in [('joint_center',motion(d,None,None,joint[r['setup']])),('selected_physical',motion(d,ind[r['setup']],weight))]:
                vr.append(scores(r,d,name,m,cfg));xy,h=integrate(d,m);arr[name+'_motion']=m;arr[name+'_xy_m']=xy;arr[name+'_heading_rad']=h
            np.savez_compressed(cache/(r['id']+'.npz'),**arr)
        write_csv(OUT/'validation_trials.csv',vr)
        for name in ('joint_center','selected_physical'):
            s,p,c=summarize([r for r in vr if r['candidate']==name]);validation[name]=s
            for suffix,rr in [('participants',p),('maneuvers',c)]:write_csv(OUT/f'validation_{name}_{suffix}.csv',rr)
    save_json(OUT/'run.json',dict(selected=selected,fold_candidates=candidates,validation_summary=validation,validation_accessed=promising,test_accessed=False,training_records=473,held_records=207,full_stack_refit=False,production_model_unchanged=True,runtime_seconds=time.perf_counter()-start,source_sha256=digest(Path(__file__))))
    print(json.dumps(dict(fold=candidates,validation=validation),indent=2),flush=True)
if __name__=='__main__':main()
