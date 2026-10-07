"""Training-selected refit damping on SAME corrected clock; preserve alias risk."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import torch
import pipeline as p
from stationary_gravity_experiment_v14 import initialization,feature_matrix
from nonlinear_endpoint_experiment_v21 import nonlinear_features
from dynamic_tilt_experiment_v33 import dynamic_features
from clock_refit_experiment_v38 import predict,C,CUTOFF,BLEND,OLD,NEW,load_cache
from observed_ridge_inference import load_observed_ridge
from planar_experiment import integrate_planar

OUT=p.ROOT/'outputs_clock_arbitrated_damped_v46';FOLDS=p.ROOT/'outputs_clock_arbitrated_folds_v43';SENSORS=p.ROOT/'outputs_clock_sensor_cache_v40';REFIT=p.ROOT/'outputs_clock_arbitrated_v42'
WEIGHTS=(0.,.1,.25,.5,.75,1.)
def record(row,d,m,name):
    xy,h=integrate_planar(d['t'],m,d['gt_xy'][0],d['gt_heading'][0],d['imu_valid'])
    return dict(id=row['id'],participant=row['participant'],condition=row['condition'],method=name,**p.metrics(d,xy,h,SETTINGS)),xy,h

def main():
    global SETTINGS
    start=time.perf_counter();torch.set_num_threads(4)
    if OUT.exists():raise RuntimeError('Preserve experiment')
    OUT.mkdir();(OUT/'fold_motion').mkdir();(OUT/'validation_trajectories').mkdir()
    protocol=json.loads((REFIT/'protocol.json').read_text());SETTINGS=protocol['old_clock_settings'];cal=json.loads((p.ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    inventory={q['id']:q for q in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())};oldfoldsource=p.ROOT/'outputs_dynamic_blend_v34';oldmanifest=json.loads((oldfoldsource/'artifact_manifest.json').read_text())['sha256']
    for source in (FOLDS,SENSORS):
        manifest=json.loads((source/'artifact_manifest.json').read_text())['sha256']
        for name,sha in manifest.items():
            if p.digest(source/name)!=sha:raise RuntimeError('Changed parent:'+str(source/name))
    p.save_json(OUT/'protocol.json',dict(weights=WEIGHTS,clock='SAME correctedv9/fallbackclock forfrozenoldfoldmodelandrefittedfoldmodel',training_selection='Min12personmean among BOTH same-clock and old-clock worst-person ratios<=1.05; selection precedes validation',
        no_validation_retuning=True,known_clock_alias='No13long10x5Trial3 v9+4.8517s shift contradicts bounded observed local lagâˆ’5ms; damping cannot fixreferenceclock',inherited_base_calibration=True,test_accessed=False))
    records=[];oldrecords=[];models={};rowfold={}
    for i in range(3):
        file=oldfoldsource/f'fold_{i}_models.json'
        if p.digest(file)!=oldmanifest[file.name]:raise RuntimeError('Changed foldparent')
        q=json.loads(file.read_text());models[i]=(dict(fits=q['original'],feature_clip=q['feature_clip']),dict(fits=q['tilt'],feature_clip=q['feature_clip'],extra_clip=q['extra_clip'],cutoff=.3))
        held=json.loads((FOLDS/f'fold_{i}_models.json').read_text())['held_ids'];rowfold.update({id:i for id in held})
    for n,(id,i) in enumerate(sorted(rowfold.items())):
        row=inventory[id]
        if row['partition']!='train':raise RuntimeError('Forbidden heldsplit')
        source=OLD if id in protocol['fallback_old_clock_ids'] else NEW
        data,_=load_cache(source,id,json.loads((source/'artifact_manifest.json').read_text()))
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')};ref_t=data['ref_t']
        state=initialization(row,cal,SETTINGS);m=ridge(sensor);x=feature_matrix(sensor,m,cal[row['setup']],state,'gravity_rotation');e=dict(motion=m,linear=x,nonlinear=nonlinear_features(x),setup=row['setup']);e['extra']=dynamic_features(sensor,m,cal[row['setup']],state,CUTOFF)
        a,b=models[i];frozen=(1-BLEND)*predict(e,a)+BLEND*predict(e,b,True)
        with np.load(FOLDS/'common_trajectories'/(id+'.npz')) as z:
            rt=z['native_c3d_time_s'];d=dict(t=z['time_s'],gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'],imu_valid=z['imu_valid']);refit=z['new_clock_blend_motion'];old=z['old_clock_blend_motion']
        sampled=[]
        for j in range(3):
            values,valid=p.masked_interp(rt,ref_t,frozen[:,j],sensor['imu_valid']);assert valid[d['imu_valid']].all();sampled.append(values)
        frozen=np.column_stack(sampled);r,_,_=record(row,d,old,'old_clock_control');oldrecords.append(r)
        for w in WEIGHTS:
            r,_,_=record(row,d,(1-w)*frozen+w*refit,f'weight_{w:g}');records.append(r)
        np.savez_compressed(OUT/'fold_motion'/(id+'.npz'),frozen_new_clock_motion=frozen,refit_new_clock_motion=refit,native_c3d_time_s=rt,imu_valid=d['imu_valid'])
        if (n+1)%25==0:print('Dampingheld',n+1,flush=True)
    p.write_csv(OUT/'training_trials.csv',records+oldrecords);base={r['participant']:r['mean_trial_position_rmse_m'] for r in p.summarize([r for r in records if r['method']=='weight_0'])[1]};oldbase={r['participant']:r['mean_trial_position_rmse_m'] for r in p.summarize(oldrecords)[1]};candidates=[]
    for w in WEIGHTS:
        ss,pp,mm=p.summarize([r for r in records if r['method']==f'weight_{w:g}']);ratios={q['participant']:q['mean_trial_position_rmse_m']/base[q['participant']] for q in pp};oldratios={q['participant']:q['mean_trial_position_rmse_m']/oldbase[q['participant']] for q in pp};candidates.append(dict(weight=w,score=ss['equal_participant_mean_position_rmse_m'],heading=ss['equal_participant_mean_heading_rmse_deg'],worst_same_clock_ratio=max(ratios.values()),worst_old_clock_ratio=max(oldratios.values()),same_clock_ratios=ratios,old_clock_ratios=oldratios))
        p.write_csv(OUT/f'weight_{w:g}_participants.csv',pp);p.write_csv(OUT/f'weight_{w:g}_maneuvers.csv',mm)
    eligible=[q for q in candidates if q['worst_old_clock_ratio']<=1.05 and q['worst_same_clock_ratio']<=1.05]
    if not eligible:
        p.save_json(OUT/'selection.json',dict(candidates=candidates,selected=None,guard_passed=False));raise RuntimeError('No candidate passes both guards; do not access validation')
    selected=min(eligible,key=lambda q:q['score']);p.save_json(OUT/'selection.json',dict(selected=selected,candidates=candidates,selected_before_validation=True,old_clock_guard_passed=selected['worst_old_clock_ratio']<=1.05))
    # All473-fitted fullrefit/frozenmodelmotions alreadysealed inv38. No fitting
    # or parameterchoice uses these71 validation files.
    validation=[];weight=selected['weight'];manifest=json.loads((REFIT/'artifact_manifest.json').read_text())['sha256']
    for id in protocol['validation_ids']:
        path=REFIT/'common_trajectories'/(id+'.npz')
        if p.digest(path)!=manifest[str(path.relative_to(REFIT))]:raise RuntimeError('Changed validationcache')
        with np.load(path) as z:
            d=dict(t=z['time_s'],gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'],imu_valid=z['imu_valid']);frozen=z['new_clock_frozen_blend_motion'];refit=z['new_clock_refit_blend_motion'];rt=z['native_c3d_time_s'];old=z['old_clock_blend_motion']
        arrays=dict(time_s=d['t'],native_c3d_time_s=rt,reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'])
        for name,motion in [('old_clock_control',old),('new_clock_frozen',frozen),('new_clock_selected',(1-weight)*frozen+weight*refit)]:
            r,xy,h=record(inventory[id],d,motion,name);validation.append(r);arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h;arrays[name+'_motion']=motion
        np.savez_compressed(OUT/'validation_trajectories'/(id+'.npz'),**arrays)
    p.write_csv(OUT/'validation_trials.csv',validation);summary={}
    for name in sorted({r['method'] for r in validation}):
        ss,pp,mm=p.summarize([r for r in validation if r['method']==name]);summary[name]=ss;p.write_csv(OUT/(name+'_participants.csv'),pp);p.write_csv(OUT/(name+'_maneuvers.csv'),mm)
    p.save_json(OUT/'run.json',dict(summary=summary,selected=selected,training_held_trials=207,training_people=12,validation_trials=71,test_accessed=False,no_validation_retuning=True,old_clock_guard_passed=selected['worst_old_clock_ratio']<=1.05,runtime_seconds=time.perf_counter()-start,source_sha256=p.digest(Path(__file__))))
    (OUT/'report.md').write_text('# Signal-arbitrated corrected-clock damping v46\n\nPredeclared0/.1/.25/.5/.75/1 motiondamping betweenoldfoldcoefficients andrefitfoldcoefficients evaluatedon SAMEcorrectedclock. FreshnativeIMUstartup, exact207heldtrial12personcommonmasks/initialpose. Selectiononsameclock5%worstpersonguard precedesvalidation. Independentoldclockguardreported; knownNo13cyclealiasfixedbyTRAINsignalrule andcannotbehiddenbya badfrozennewclockbaseline.\n\n'+json.dumps(dict(selection=selected,validation=summary),indent=2)+'\n',encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(dict(selected=selected,summary=summary),indent=2),flush=True)

if __name__=='__main__':main()
