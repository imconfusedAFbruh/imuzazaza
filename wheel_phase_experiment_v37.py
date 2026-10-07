"""Train-selected wheel acceleration-phase features; conditional v21 comparator.

Rotating gravity provides a gyro-independent rotation proxy, contaminated by
propulsion and lever-arm accelerations. No verified SI or slip-label claim.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,time
import numpy as np
import torch
from scipy.signal import butter,sosfiltfilt,savgol_filter
from pipeline import ROOT,runs,digest,save_json,write_csv,metrics,summarize
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted,nonlinear_features
from dynamic_tilt_experiment_v33 import clips_extra,expanded,C
from motion_endpoint_experiment_v16 import normal_system,fit
from dynamic_tilt_blend_v34 import corrected_entry
from participant_folds_experiment_v24 import FOLDS
from trajectory_calibration_v10 import integrate
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix

OUT=ROOT/'outputs_wheel_phase_v37'
WEIGHTS=(0.,.25,.5,.75)


def phase_proxy(d,c):
    t=d['t'];raw=d['raw'];hz=1/np.median(np.diff(t));sos=butter(2,4.,fs=hz,output='sos')
    result=[]
    for side,q in enumerate(c['terms'][:2]):
        axis=q['column']-(6*side+3)
        if axis not in (0,1,2):raise ValueError('Invalid trained wheel axis')
        plane=[j for j in range(3) if j!=axis]
        a=raw[:,side*6:side*6+3]/c['accel_counts_per_g'][side]
        phase=np.zeros(len(t));quality=np.zeros(len(t));amplitude=np.zeros(len(t))
        for first,last in runs(d['imu_valid']):
            if last-first<60:continue
            low=sosfiltfilt(sos,a[first:last],axis=0)
            norm=np.linalg.norm(low[:,plane],axis=1)
            angle=np.unwrap(np.arctan2(low[:,plane[1]],low[:,plane[0]]))
            rate=savgol_filter(angle,51,2,deriv=1,delta=1/hz)
            # Plane amplitude near gravity, away from a degenerate phase vector.
            confidence=np.clip((norm-.2)/.5,0,1)*np.clip(1-np.abs(norm-1)/.75,0,1)
            confidence[:25]=0;confidence[-25:]=0
            phase[first:last]=rate;quality[first:last]=confidence;amplitude[first:last]=norm
        wheel=raw[:,q['column']]*q['scale']+q['intercept']
        result.append(dict(rate=phase,quality=quality,amplitude=amplitude,wheel=wheel))
    return result


def fit_phase_mapping(entries):
    mapping={}
    for setup in sorted({e['setup'] for e in entries}):
        mapping[setup]=[]
        for side in (0,1):
            xy=[]
            for e in entries:
                if e['setup']!=setup:continue
                p=e['phase'][side];mask=e['data']['imu_valid']&(p['quality']>.5)&(np.abs(p['wheel'])>.15)&(np.abs(p['rate'])>.3)&(np.abs(p['rate'])<20)
                ids=np.flatnonzero(mask)[::10]
                if len(ids):xy.append((p['rate'][ids],p['wheel'][ids]))
            if not xy:
                mapping[setup].append(dict(scale=0.,samples=0,usable=False));continue
            x,y=map(np.concatenate,zip(*xy));ratio=y/x;scale=float(np.median(ratio))
            # Physically plausible wheel-radius magnitude; signed mounting axis.
            usable=.15<=abs(scale)<=.6
            residual=y-scale*x
            mapping[setup].append(dict(scale=scale if usable else 0.,raw_scale=scale,samples=len(x),usable=usable,residual_rmse=float(np.sqrt(np.mean(residual**2))),median_abs_residual=float(np.median(np.abs(residual))),correlation=float(np.corrcoef(x,y)[0,1])))
    return mapping


def extras(e,mapping):
    f=[]
    for side,p in enumerate(e['phase']):
        q=mapping[e['setup']][side];quality=p['quality'] if q['usable'] else np.zeros_like(p['quality'])
        v=p['rate']*q['scale']
        f.extend([v*quality,(v-p['wheel'])*quality,quality,p['amplitude']*quality,p['wheel']*quality])
    f=np.array(f).T;t=e['data']['t']
    return np.c_[*[np.c_[*[np.interp(t+o,t,f[:,j]) for j in range(f.shape[1])]] for o in (-.5,0.,.5)]].astype(np.float32)


def main():
    start=time.perf_counter();torch.set_num_threads(2)
    if OUT.exists():raise RuntimeError('Preserve experiment')
    OUT.mkdir();source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    save_json(OUT/'protocol.json',dict(hypothesis='Wheel accelerometer rotating gravity phase gives complementary spin proxy to learned gyro axes; centrifugal/tangential acceleration may invalidate it',phase_lowpass_hz=4,angle_derivative='51-sample2nd-order Savitzky-Golay',context_s=[-.5,0,.5],weights=WEIGHTS,folds=[sorted(f) for f in FOLDS],mapping='Per-setup/side median gyro-derived wheelvelocity / acceleration-phase rate, fitting data only; plausible radius magnitude .15 to .6m; quality from gravity-plane norm',selection='Three conditional training folds, pooled12person mean with <=5%worstperson regression vs samefold original. All results retained. No test.',caveat='Inherited calibration/base; phase not factory-unit verification or independent slip groundtruth'))
    train=load_train(ROOT/'outputs_motion_endpoint_v16')
    for e in train:e['phase']=phase_proxy(e['data'],cal[e['setup']])
    records=[]
    for i,fold in enumerate(FOLDS):
        fitting=[e for e in train if e['row']['participant'] not in fold];held=[e for e in train if e['row']['participant'] in fold]
        clips=bounds(fitting);mapping=fit_phase_mapping(fitting)
        for e in fitting+held:e['extra']=extras(e,mapping)
        extra=clips_extra(fitting);a=fit(normal_system(adapted(fitting,C['basis'],clips)),.1,1.);b=fit(normal_system(expanded(fitting,clips,extra)),.1,1.)
        save_json(OUT/f'fold_{i}_model.json',dict(original=a,phase=b,feature_clip=clips,extra_clip=extra,phase_mapping=mapping,fit_ids=[e['row']['id'] for e in fitting],held_people=sorted(fold)))
        for old,new in zip(adapted(held,C['basis'],clips),expanded(held,clips,extra)):
            m0,m1=corrected_entry(old,a),corrected_entry(new,b)
            for w in WEIGHTS:
                xy,h=integrate(old['data'],(1-w)*m0+w*m1);records.append(dict(weight=w,fold=i,id=old['row']['id'],participant=old['row']['participant'],condition=old['row']['condition'],**metrics(old['data'],xy,h,cfg)))
        print('Phasefold',i,flush=True)
    write_csv(OUT/'fold_trials.csv',records);base={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in records if r['weight']==0])[1]};choices=[]
    for w in WEIGHTS:
        s,p,_=summarize([r for r in records if r['weight']==w]);choices.append(dict(weight=w,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(q['mean_trial_position_rmse_m']/base[q['participant']] for q in p)))
    selected=min([q for q in choices if q['worst_person_ratio']<=1.05],key=lambda q:q['score']);save_json(OUT/'selection.json',dict(selected=selected,candidates=choices,selected_before_validation=True));print('Selected',selected,flush=True)
    mapping=fit_phase_mapping(train);clips=bounds(train)
    for e in train:e['extra']=extras(e,mapping)
    extra=clips_extra(train);fit_all=fit(normal_system(expanded(train,clips,extra)),.1,1.)
    save_json(OUT/'model.json',dict(fits=fit_all,feature_clip=clips,extra_clip=extra,phase_mapping=mapping,candidate=C,weight=selected['weight'],training_ids=[e['row']['id'] for e in train]))
    del train,fitting,held
    oldmodel=json.loads((ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text());sm=json.loads((source/'artifact_manifest.json').read_text());ridge=load_observed_ridge();states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};rr={'original_v21':[],'selected_phase':[]};cache=OUT/'trajectories';cache.mkdir()
    for row,d,_ in observed_rows(source,cfg,'validation',sm):
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(sensor);linear=feature_matrix(sensor,m,cal[row['setup']],states[row['id']],'gravity_rotation');e=dict(row=row,data=d,motion=m,linear=linear,nonlinear=nonlinear_features(linear),setup=row['setup']);e['phase']=phase_proxy(sensor,cal[row['setup']]);e['extra']=extras(e,mapping)
        m0=corrected_entry(adapted([e],C['basis'],oldmodel['feature_clip'])[0],oldmodel['fits']);m1=corrected_entry(expanded([e],clips,extra)[0],fit_all)
        arrays=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'])
        for name,motion in [('original_v21',m0),('selected_phase',(1-selected['weight'])*m0+selected['weight']*m1)]:
            xy,h=integrate(d,motion);rr[name].append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,cfg)));arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h;arrays[name+'_motion']=motion
        np.savez_compressed(cache/(row['id']+'.npz'),**arrays)
    summaries={}
    for name,rows in rr.items():
        summaries[name],p,c=summarize(rows)
        for suffix,values in [('trials',rows),('participants',p),('maneuvers',c)]:write_csv(OUT/f'{name}_{suffix}.csv',values)
    save_json(OUT/'run.json',dict(summary=summaries,selection=selected,training_trials=473,validation_trials=71,test_accessed=False,base_refit=False,runtime_seconds=time.perf_counter()-start,source_sha256=digest(ROOT/'wheel_phase_experiment_v37.py')));save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)


if __name__=='__main__':main()
