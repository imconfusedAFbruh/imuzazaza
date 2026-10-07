"""Matched473/71 corrected-clock conditional residual refit; fixed parameters.

Original accepted IDs preserved. Use v9 clocks for465 train/71 validation and
explicitly retain original v7 clocks for8 train exclusions. One common native
observed initial pose for paired scores. No test or validation retuning.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,csv,time,gc
from pathlib import Path
import numpy as np
import torch
import pipeline as p
from learning import training_group
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix,correction
from nonlinear_endpoint_experiment_v21 import nonlinear_features,bounds,adapted
from motion_endpoint_experiment_v16 import normal_system,fit
from dynamic_tilt_experiment_v33 import dynamic_features,clips_extra,expanded
from trajectory_calibration_v10 import integrate
from planar_experiment import integrate_planar
from observed_reference_experiment import observed_markers

OUT=p.ROOT/'outputs_clock_refit_v38';OLD=p.ROOT/'outputs_observed_reference_v7';NEW=p.ROOT/'outputs_observed_sync_v9'
C=dict(basis='physical_products',alpha=.1,endpoint_weight=1.,gain=.5);BLEND=.75;CUTOFF=.3

def load_cache(folder,id,manifest):
    path=folder/'cache'/(id+'.npz');meta=path.with_suffix('.json')
    for f in (path,meta):
        if p.digest(f)!=manifest['sha256'][str(f.relative_to(folder))]:raise RuntimeError('Changed cache:'+str(f))
    with np.load(path) as z:d={k:z[k] for k in z.files}
    return d,json.loads(meta.read_text())

def entry(row,d,ridge,cal,state):
    sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};motion=ridge(sensor);x=feature_matrix(sensor,motion,cal[row['setup']],state,'gravity_rotation')
    label=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])
    e=dict(row=row,data=d,motion=motion,linear=x,nonlinear=nonlinear_features(x),label=label,target=np.c_[d['gt_v'],d['gt_yaw']]-motion[:,[0,2]],setup=row['setup'],group=training_group(row))
    e['extra']=dynamic_features(d,motion,cal[row['setup']],state,CUTOFF)
    return e

def predict(e,q,tilt=False):
    entries=expanded([e],q['feature_clip'],q['extra_clip']) if tilt else adapted([e],C['basis'],q['feature_clip'])
    z=entries[0];return correction(dict(z,x={'gravity_rotation':z['x']}),q['fits'],dict(C,mode='gravity_rotation'))

def common(row,old,new,motions,cfg,out):
    saved_reader=p.read_markers
    try:p.read_markers=observed_markers;gt=p.reference(p.ROOT/row['c3d'],cfg,row['setup'])
    finally:p.read_markers=saved_reader
    lo=max(old['ref_t'][0],new['ref_t'][0]);hi=min(old['ref_t'][-1],new['ref_t'][-1]);native=np.flatnonzero((gt['t']>=lo)&(gt['t']<=hi));rt=gt['t'][native]
    sampled={};support=np.ones(len(rt),bool)
    for name,(d,motion) in motions.items():
        channels=[]
        for j in range(3):
            values,valid=p.masked_interp(rt,d['ref_t'],motion[:,j],d['imu_valid']);channels.append(values);support &=valid
        sampled[name]=np.column_stack(channels)
    starts=np.flatnonzero(gt['valid'][native]&support)
    if not len(starts):raise RuntimeError('No common initial native pose')
    first=int(starts[0]);native=native[first:];rt=rt[first:];support=support[first:]
    d=dict(t=rt-rt[0],gt_xy=gt['xy'][native],gt_heading=gt['heading'][native],gt_valid=gt['valid'][native],imu_valid=support)
    records=[];arrays=dict(time_s=d['t'],native_c3d_time_s=rt,reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=support)
    for name,m in sampled.items():
        m=m[first:];xy,h=integrate_planar(d['t'],m,d['gt_xy'][0],d['gt_heading'][0],support)
        records.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],method=name,**p.metrics(d,xy,h,cfg)))
        arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h;arrays[name+'_motion']=m
    if len({r['scored_frames'] for r in records})!=1:raise RuntimeError('Common masks differ')
    np.savez_compressed(out/'common_trajectories'/(row['id']+'.npz'),**arrays)
    coverage=dict(id=row['id'],participant=row['participant'],condition=row['condition'],old_first_c3d_s=float(old['ref_t'][0]),new_first_c3d_s=float(new['ref_t'][0]),
                  common_first_c3d_s=float(rt[0]),common_last_c3d_s=float(rt[-1]),common_scored_frames=records[0]['scored_frames'],common_total_frames=len(rt),
                  old_observed_frames=int(old['gt_valid'].sum()),new_observed_frames=int(new['gt_valid'].sum()),initial_pose_shared=True,reference_interpolated=False)
    return records,coverage

def main():
    started=time.perf_counter();torch.set_num_threads(4)
    if OUT.exists():raise RuntimeError('Preserve immutable run')
    OUT.mkdir();(OUT/'common_trajectories').mkdir();(OUT/'new_clock_trajectories').mkdir()
    oldrun=json.loads((OLD/'run.json').read_text());cfg=oldrun['settings'];newrun=json.loads((NEW/'run.json').read_text())
    manifests={f:json.loads((f/'artifact_manifest.json').read_text()) for f in (OLD,NEW)}
    rows={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    oldaccepted=[r for r in csv.DictReader((OLD/'qc.csv').open(newline='')) if r['status']=='accepted' and r['partition'] in ('train','validation')]
    newaccepted={r['id'] for r in csv.DictReader((NEW/'qc.csv').open(newline='')) if r['status']=='accepted' and r['partition'] in ('train','validation')}
    trainids=[r['id'] for r in oldaccepted if r['partition']=='train'];validids=[r['id'] for r in oldaccepted if r['partition']=='validation'];fallback=sorted(set(trainids)-newaccepted)
    assert len(trainids)==473 and len(validids)==71 and len(fallback)==8 and set(validids)<=newaccepted
    assert not ({rows[i]['participant'] for i in trainids}&{rows[i]['participant'] for i in validids})
    cal=json.loads((p.ROOT/'outputs_amended_v2/calibration.json').read_text());statefile=p.ROOT/'outputs_stationary_gravity_v14/initialization.json'
    states={r['id']:r for r in json.loads(statefile.read_text())['records']};ridge=load_observed_ridge()
    oldmodel=json.loads((p.ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text());oldtilt=json.loads((p.ROOT/'outputs_dynamic_tilt_v33/tilt_0.3_model.json').read_text())
    p.save_json(OUT/'protocol.json',dict(training_ids=trainids,validation_ids=validids,fallback_old_clock_ids=fallback,corrected_training_count=465,fallback_training_count=8,
        corrected_validation_count=71,parameters=C,tilt_cutoff_hz=CUTOFF,motion_blend=BLEND,no_validation_retuning=True,test_accessed=False,
        startup='Sealed native-first5s IMU-onlyv14 states reused; sameacquisitions and inherited calibration, independent of optical clock/crop',
        inherited='Base ridge, physical calibration, empirical units and earlier label limitations remain; conditional residual refit only',
        common_score='Native observed C3D timestamps on common support; interpolate each motion using its own ref_t; one shared initialobserved pose and no resets',
        old_clock_settings=cfg,new_clock_settings=newrun['settings'],parent_hashes={str(f.relative_to(p.ROOT)):p.digest(f) for f in [OLD/'artifact_manifest.json',NEW/'artifact_manifest.json',statefile,p.ROOT/'outputs_nonlinear_endpoint_v21/model.json',p.ROOT/'outputs_dynamic_tilt_v33/tilt_0.3_model.json',p.ROOT/'outputs_observed_ridge_v8/artifact_manifest.json']}))
    training=[];clockrows=[]
    for n,id in enumerate(trainids):
        row=rows[id];folder=NEW if id in newaccepted else OLD;d,meta=load_cache(folder,id,manifests[folder]);old,oldmeta=load_cache(OLD,id,manifests[OLD]);state=states[id]
        if state['partition']!='train' or state['setup']!=row['setup']:raise RuntimeError('Startupstate differs')
        training.append(entry(row,d,ridge,cal,state));clockrows.append(dict(id=id,partition='train',source=folder.name,fallback=id in fallback,old_offset_s=oldmeta['synchronization']['offset_s'],new_offset_s=meta['synchronization']['offset_s'],offset_delta_s=meta['synchronization']['offset_s']-oldmeta['synchronization']['offset_s'],old_observed_frames=int(old['gt_valid'].sum()),new_observed_frames=int(d['gt_valid'].sum())))
        if (n+1)%50==0:print('Prepared train',n+1,flush=True)
    clips=bounds(training);extra=clips_extra(training);newmodel=dict(candidate=C,fits=fit(normal_system(adapted(training,C['basis'],clips)),.1,1.),feature_clip=clips,training_ids=trainids)
    newtilt=dict(candidate=C,fits=fit(normal_system(expanded(training,clips,extra)),.1,1.),feature_clip=clips,extra_clip=extra,cutoff=.3,training_ids=trainids)
    p.save_json(OUT/'v21_model.json',newmodel);p.save_json(OUT/'tilt_model.json',newtilt);p.save_json(OUT/'blend_model.json',dict(weight=BLEND,v21_model='v21_model.json',tilt_model='tilt_model.json',startup_source_sha256=p.digest(statefile),sensor_features_only=True))
    del training;gc.collect();commonrecords=[];fullrecords=[];coverage=[]
    for n,id in enumerate(validids):
        row=rows[id];old,oldmeta=load_cache(OLD,id,manifests[OLD]);new,newmeta=load_cache(NEW,id,manifests[NEW]);state=states[id];eo=entry(row,old,ridge,cal,state);en=entry(row,new,ridge,cal,state)
        oldv=predict(eo,oldmodel);oldt=predict(eo,oldtilt,True);controlblend=(1-BLEND)*oldv+BLEND*oldt
        frozenv=predict(en,oldmodel);frozent=predict(en,oldtilt,True);frozenblend=(1-BLEND)*frozenv+BLEND*frozent
        refitv=predict(en,newmodel);refitt=predict(en,newtilt,True);refitblend=(1-BLEND)*refitv+BLEND*refitt
        motions={'old_clock_v21':(old,oldv),'old_clock_blend':(old,controlblend),'new_clock_frozen_v21':(new,frozenv),'new_clock_frozen_blend':(new,frozenblend),'new_clock_refit_v21':(new,refitv),'new_clock_refit_blend':(new,refitblend)}
        arrays=dict(old_time_s=old['t'],old_ref_t=old['ref_t'],old_reference_valid=old['gt_valid'],new_time_s=new['t'],new_ref_t=new['ref_t'],new_reference_xy_m=new['gt_xy'],new_reference_heading_rad=new['gt_heading'],new_reference_valid=new['gt_valid'],new_imu_valid=new['imu_valid'])
        for name,(d,m) in motions.items():
            xy,h=integrate(d,m);fullrecords.append(dict(id=id,participant=row['participant'],condition=row['condition'],method=name,**p.metrics(d,xy,h,cfg)))
            arrays[name+'_motion']=m
            if d is new:arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h
        np.savez_compressed(OUT/'new_clock_trajectories'/(id+'.npz'),**arrays)
        rr,cc=common(row,old,new,motions,cfg,OUT);commonrecords.extend(rr);coverage.append(cc)
        clockrows.append(dict(id=id,partition='validation',source=NEW.name,fallback=False,old_offset_s=oldmeta['synchronization']['offset_s'],new_offset_s=newmeta['synchronization']['offset_s'],offset_delta_s=newmeta['synchronization']['offset_s']-oldmeta['synchronization']['offset_s'],old_observed_frames=int(old['gt_valid'].sum()),new_observed_frames=int(new['gt_valid'].sum())))
        if (n+1)%10==0:print('Scored validation',n+1,flush=True)
    p.write_csv(OUT/'clock_changes.csv',clockrows);p.write_csv(OUT/'common_coverage.csv',coverage);summary={}
    for benchmark,records in [('own_clock_full',fullrecords),('common_native',commonrecords)]:
        p.write_csv(OUT/(benchmark+'_trials.csv'),records);summary[benchmark]={}
        for name in sorted({r['method'] for r in records}):
            ss,pp,mm=p.summarize([r for r in records if r['method']==name]);summary[benchmark][name]=ss
            p.write_csv(OUT/(benchmark+'_'+name+'_participants.csv'),pp);p.write_csv(OUT/(benchmark+'_'+name+'_maneuvers.csv'),mm)
    assert abs(summary['own_clock_full']['old_clock_v21']['equal_participant_mean_position_rmse_m']-.10258517940337783)<1e-8
    assert abs(summary['own_clock_full']['old_clock_blend']['equal_participant_mean_position_rmse_m']-.1007021193993738)<1e-8
    p.save_json(OUT/'run.json',dict(summary=summary,train_trials=473,validation_trials=71,corrected_train=465,fallback_train_ids=fallback,test_accessed=False,base_refit=False,calibration_refit=False,no_validation_retuning=True,runtime_seconds=time.perf_counter()-started,source_sha256=p.digest(Path(__file__))))
    lines=['# Corrected-clock conditional residual refit v38','','Exactly473originalacceptedtrainIDs:465v9correctedclocks plus8explicitoldv7fallbackIDs. Validation71v9correctedclockIDs, frozen split. Ridge/calibration are inherited; startupstates use original native-first5s IMU only. Fit correctionclips/normalization/weights on train only with fixedv21 andtilt/blendparameters. No validation retuning or test.','', 'Fallback IDs: '+', '.join(fallback), '', 'Two benchmarks are deliberately separate: own-clockfull uses each preparation\'s own observed initialpose/mask; common-native integrates all6motionstreams on nativeC3Dtimestamps from ONE identical observed initialpose and exact common masks. No internal reference resets or geometric alignment. Originalproduction100.702119mm is reproduced independently.','', '| Benchmark | Method | PositionRMSE(mm) | HeadingRMSE(deg) |','|---|---|---:|---:|']
    lines +=[f"| {b} | {n} | {s['equal_participant_mean_position_rmse_m']*1000:.6f} | {s['equal_participant_mean_heading_rmse_deg']:.6f} |" for b,results in summary.items() for n,s in results.items()]
    lines +=['','Allperson/maneuverregressions remain inCSV tables. Refittingnewclocklabels is scientifically more coherent than applyingv37timestampreassignment, but this is still conditional: inheritedbase/calibration were trainedunderolderlabels. Fullparticipantnestedpipelineandindependentphysicalcalibrationremainrequired.','']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
