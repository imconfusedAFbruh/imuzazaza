"""Offline IMU-only rotation-quiet predictor bias, fixed conditional-fold guard.

No velocity zeroing, reference updates, or optical stationarity gating. Quiet
is an imperfect rotation proxy; predicted quiet yaw is bounded before removal.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,csv,time
import numpy as np
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,runs,digest,save_json,write_csv,metrics,summarize
from dynamic_blend_inference_v34 import integrate_motion

OUT=ROOT/'outputs_quiet_yaw_v41';GAINS=(0.,.25,.5,1.);CAP=.01


def bias(sensor,motion,c):
    raw=sensor['raw'];valid=sensor['imu_valid'];t=sensor['t'];hz=1/np.median(np.diff(t));window=int(round(hz))|1
    acc=raw[:,12:15]/c['accel_counts_per_g'][2]
    gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale'])
    wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]]
    sd=np.sqrt(np.maximum(uniform_filter1d(acc**2,window,axis=0)-uniform_filter1d(acc,window,axis=0)**2,0))
    gate=(np.max(np.abs(wheel),axis=1)<.05)&(np.linalg.norm(gyro,axis=1)<.1)&(np.max(sd,axis=1)<.02)&valid
    half=window//2;gate[:half]=False;gate[-half:]=False
    # A complete variance window must remain within valid IMU support.
    gate &= uniform_filter1d(valid.astype(float),window,mode='constant')>.999999
    observations=[];quiet=np.zeros(len(t),bool)
    for a,b in runs(gate):
        if b-a>=round(hz):
            rate=motion[a:b,2];finite=np.isfinite(rate)
            if finite.all():
                quiet[a:b]=True;observations.append((float(np.median(t[a:b])),float(np.clip(np.median(rate),-CAP,CAP))))
    offset=np.zeros(len(t))
    if observations:
        times,values=np.array(observations).T
        offset=np.interp(t,times,values)
    return offset,dict(quiet_seconds=float(quiet.sum()/hz),segments=len(observations),maximum_abs_bias_rad_s=float(np.max(np.abs(offset))),mean_abs_bias_rad_s=float(np.mean(np.abs(offset))),observations=observations),quiet


def score_one(row,z,raw,motion,cal,gains,records,details):
    d=dict(t=z['time_s'],gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'],imu_valid=z['imu_valid'])
    sensor=dict(t=d['t'],raw=raw,imu_valid=d['imu_valid']);offset,stats,quiet=bias(sensor,motion,cal[row['setup']]);details.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**stats))
    for gain in gains:
        m=motion.copy();m[:,2]-=gain*offset
        xy,h=integrate_motion(d['t'],m,d['gt_xy'][0],d['gt_heading'][0],d['imu_valid']);records.append(dict(gain=gain,id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,{})))
    return offset,quiet


def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve experiment')
    OUT.mkdir();cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());inventory={r['id']:r for r in json.loads((ROOT/'outputs_amended_v2/inventory.json').read_text())};cfg=json.loads((ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings']
    # metrics needs only distance intervals from settings; no fitted threshold.
    global metrics
    original_metrics=metrics;metrics=lambda d,xy,h,unused:original_metrics(d,xy,h,cfg)
    save_json(OUT/'protocol.json',dict(hypothesis='Learned yaw output during strict all3IMU rotation-quiet intervals reveals a residual constant/drifting bias; interpolate quiet observations across motion offline',gains=GAINS,bias_cap_rad_s=CAP,gate='Existing v14 wheel<.05,center3gyro<.1,centeracc1sSD<.02g,min1s,halfwindowboundaryexclusion,completevalidIMUvariancewindow',no_velocity_zeroing=True,quiet_caveat='Quiet proxy imperfect and empirical scale; slow rotation/slip/tilt may misclassify. No optical gate.',selection='207heldtargettraining motions fromthreeconditionalfolds, mean12people <=5%worstregression vsidenticaloldclockblend control. Basecalibrationinherited.',test_accessed=False))
    parent=ROOT/'outputs_clock_folds_v39';pm=json.loads((parent/'artifact_manifest.json').read_text())['sha256'];sensors=ROOT/'outputs_clock_sensor_cache_v40';sm=json.loads((sensors/'artifact_manifest.json').read_text())['sha256'];train=[];details=[]
    for path in sorted((parent/'common_trajectories').glob('*.npz')):
        id=path.stem;row=inventory[id]
        if row['partition']!='train':raise RuntimeError('Unexpectedpartition')
        sp=sensors/'sensors'/path.name
        if digest(path)!=pm[str(path.relative_to(parent))] or digest(sp)!=sm[str(sp.relative_to(sensors))]:raise RuntimeError('Changed fold/sensorcache')
        with np.load(path) as q:z={k:q[k] for k in q.files}
        with np.load(sp) as q:raw=q['old_common_raw'];assert np.array_equal(q['native_c3d_time_s'],z['native_c3d_time_s'])
        score_one(row,z,raw,z['old_clock_blend_motion'],cal,GAINS,train,details)
    write_csv(OUT/'fold_trials.csv',train);save_json(OUT/'training_quiet_details.json',details);base={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in train if r['gain']==0])[1]};choices=[]
    for gain in GAINS:
        s,p,_=summarize([r for r in train if r['gain']==gain]);choices.append(dict(gain=gain,score=s['equal_participant_mean_position_rmse_m'],heading=s['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(q['mean_trial_position_rmse_m']/base[q['participant']] for q in p)))
    selected=min([q for q in choices if q['worst_person_ratio']<=1.05],key=lambda q:q['score']);save_json(OUT/'selection.json',dict(selected=selected,candidates=choices,selected_before_validation=True));print('Selected',selected,flush=True)
    # Validation old-clock predictor remains originalv34, same original observed mask.
    predictions=ROOT/'outputs_dynamic_blend_v34';manifest=json.loads((predictions/'artifact_manifest.json').read_text())['sha256'];source=ROOT/'outputs_observed_reference_v7';source_manifest=json.loads((source/'artifact_manifest.json').read_text())['sha256'];records=[];valdetails=[];cache=OUT/'trajectories';cache.mkdir()
    for path in sorted((predictions/'trajectories').glob('*.npz')):
        row=inventory[path.stem];sp=source/'cache'/path.name
        if row['partition']!='validation' or digest(path)!=manifest[str(path.relative_to(predictions))] or digest(sp)!=source_manifest[str(sp.relative_to(source))]:raise RuntimeError('Invalid validation')
        with np.load(path) as q:z={k:q[k] for k in q.files}
        with np.load(sp) as q:raw=q['raw'];assert np.array_equal(q['t'],z['time_s'])
        offset,quiet=score_one(row,z,raw,z['selected_blend_motion'],cal,(0.,selected['gain']),records,valdetails)
        save=dict(time_s=z['time_s'],reference_xy_m=z['reference_xy_m'],reference_heading_rad=z['reference_heading_rad'],reference_valid=z['reference_valid'],imu_valid=z['imu_valid'],quiet=quiet,bias_yaw_rad_s=offset)
        for name,gain in [('control',0.),('selected',selected['gain'])]:
            m=z['selected_blend_motion'].copy();m[:,2]-=gain*offset;xy,h=integrate_motion(z['time_s'],m,z['reference_xy_m'][0],z['reference_heading_rad'][0],z['imu_valid']);save[name+'_xy_m']=xy;save[name+'_heading_rad']=h;save[name+'_motion']=m
        np.savez_compressed(cache/path.name,**save)
    save_json(OUT/'validation_quiet_details.json',valdetails);summaries={}
    for name,gain in [('control',0.),('selected',selected['gain'])]:
        # Zero-selected duplicate rows are identical; take one record perID.
        subset=list({r['id']:r for r in records if r['gain']==gain}.values());summaries[name],p,c=summarize(subset)
        for suffix,rr in [('trials',subset),('participants',p),('maneuvers',c)]:write_csv(OUT/f'{name}_{suffix}.csv',rr)
    result=dict(summary=summaries,selection=selected,training_trials=len(details),training_people=len(base),validation_trials=len(valdetails),training_quiet_eligible=sum(d['segments']>0 for d in details),validation_quiet_eligible=sum(d['segments']>0 for d in valdetails),test_accessed=False,base_refit=False,runtime_seconds=time.perf_counter()-start,source_sha256=digest(ROOT/'quiet_yaw_bias_experiment_v41.py'));save_json(OUT/'run.json',result);save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
