"""Native IMU-only wheel quiet bias and zero-intercept rim speed fits."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,time,copy
from pathlib import Path
import numpy as np
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,digest,save_json,write_csv,imu_streams,sample_streams,runs,velocities,metrics,summarize
from trajectory_calibration_v10 import integrate
from participant_folds_experiment_v24 import FOLDS
OUT=ROOT/'outputs_wheel_bias_v39';WEIGHTS=(0.,.25,.5)
def read(p):return json.loads(p.read_text())
def native(row,cfg):
    t,raw,valid=sample_streams(imu_streams(ROOT/row['imu']),cfg);keep=t<=t[0]+5.;return t[keep],raw[keep],valid[keep]
def bias_state(native_data,c,cfg):
    t,raw,valid=native_data;default=[-q['intercept']/q['scale'] for q in c['terms'][:2]];state=dict(eligible=False,quiet_seconds=0.,wheel_bias_counts=default,reason='No contiguous qualifying startup quiet interval')
    if len(t)<150:return state
    acc=raw[:,12:15]/c['accel_counts_per_g'][2];gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale']);wheel=np.c_[*[raw[:,q['column']]*q['scale']+q['intercept'] for q in c['terms'][:2]]]
    sd=np.sqrt(np.maximum(uniform_filter1d(acc**2,101,axis=0)-uniform_filter1d(acc,101,axis=0)**2,0));gate=(np.max(np.abs(wheel),axis=1)<.05)&(np.linalg.norm(gyro,axis=1)<.1)&(np.max(sd,axis=1)<.02)&valid;gate[:50]=False;gate[-50:]=False;quiet=np.zeros(len(gate),bool)
    for a,b in runs(gate):
        if b-a>=100:quiet[a:b]=True
    if not quiet.any():return state
    bs=[float(np.median(raw[quiet,q['column']])) for q in c['terms'][:2]]
    return dict(eligible=True,quiet_seconds=float(quiet.sum()/cfg['hz']),wheel_bias_counts=bs,reason='',quiet_wheel_velocity_before_m_s=[float(np.median(wheel[quiet,i])) for i in (0,1)],first_quiet_s=float(t[np.flatnonzero(quiet)[0]]-t[0]),last_quiet_s=float(t[np.flatnonzero(quiet)[-1]]-t[0]))
def robust_zero(x,y):
    valid=np.isfinite(x)&np.isfinite(y);x,y=x[valid],y[valid];assert len(x)>500 and np.std(x)>1
    slope=float(x@y/(x@x))
    for _ in range(6):
        err=x*slope-y;mad=max(float(np.median(np.abs(err-np.median(err))))*1.4826,.005);w=np.minimum(1.,1.5*mad/np.maximum(np.abs(err),1e-9));slope=float((w*x)@y/((w*x)@x))
    return slope,float(np.mean((slope*x-y)**2))
def fit(fitting,cal,states,cfg):
    model=copy.deepcopy(cal)
    for setup,c in model.items():
        chosen=[t for t in fitting if t[0]['setup']==setup];assert set(c['training_trials'])=={r['id'] for r,d,_ in chosen}
        for side,sgn in [(0,-1),(1,1)]:
            q=c['terms'][side];xs=[];ys=[]
            for r,d,_ in chosen:
                valid=d['label_valid'];b=states[r['id']]['wheel_bias_counts'][side];xs.append((d['raw'][valid,q['column']]-b)[::5]);ys.append((d['gt_v'][valid]+sgn*.5*cfg['track_width_m']*d['gt_yaw'][valid])[::5])
            q['scale'],q['mse']=robust_zero(np.concatenate(xs),np.concatenate(ys));q['intercept']=0.;q['fit_objective']='Zero physical intercept after per-record native wheel quiet bias; rigid differential-drive rim target'
    return model
def motion(r,d,model,states,w):
    c=model[r['setup']];b=states[r['id']]['wheel_bias_counts'];wheel=[(d['raw'][:,q['column']]-b[i])*q['scale'] for i,q in enumerate(c['terms'][:2])];q=c['terms'][2];center=d['raw'][:,q['column']]*q['scale']+q['intercept'];yaw=(wheel[1]-wheel[0])/c['track_width_m'];return np.c_[(wheel[0]+wheel[1])/2,np.zeros(len(center)),(1-w)*center+w*yaw]
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve experiment')
    OUT.mkdir();cfg=read(ROOT/'outputs_observed_reference_v7/run.json')['settings'];p=ROOT/'outputs_motion_endpoint_v16';manifest=read(p/'artifact_manifest.json')['sha256'];identity={r['id']:r for r in read(ROOT/'outputs_amended_v2/input_identity_audit.json')['records']};train=[];natives={}
    save_json(OUT/'protocol.json',dict(hypothesis='Regression wheel intercepts are not actual rest biases; independently gated native startup wheel biases and zero-intercept rim fits may stabilize differentialyaw',weights=WEIGHTS,track_m=.52,gate='Nativefirst5s, both empirical wheels<.05m/s,center3gyro<.1rad/s,center accelerationrollingSD<.02g, validIMU, >=1contiguoussecond; exclude.5svariance boundaries. IMUonly; fallbackdatewheelzero counts.',fit='Sixpass robust zero-intercept slope on fitting-only v±L*yaw/2; center calibration unchanged',selection='Threeconditionalfolds12person mean <=5%worstperson regression vs matchingjointcenter; zero eligible. Savebeforevalidation.',caveat='Gate is empirical and does not independently prove body stationarity; wheel lock/coasting can defeat inference. No opticalstationarity labels or motionresets. Frozen clocks/referencegeometry/QC; no fullresidual refit.'))
    for i,path in enumerate(sorted((p/'prepared_training').glob('*.npz'))):
        meta=path.with_suffix('.json')
        for f in (path,meta):assert digest(f)==manifest[str(f.relative_to(p))]
        r=read(meta)['row'];assert r['partition']=='train';assert digest(ROOT/r['imu'])==identity[r['id']]['imu_sha256']
        with np.load(path) as z:d={k:z[k] for k in ['setup','t','raw','imu_valid','gt_xy','gt_heading','gt_v','gt_yaw','gt_valid','label_valid']}
        train.append((r,d,{}));natives[r['id']]=native(r,cfg)
        if (i+1)%100==0:print('Native training startups',i+1,flush=True)
    assert len(train)==473;rows=[];state_records=[]
    for fold,people in enumerate(FOLDS):
        fitting=[t for t in train if t[0]['participant'] not in people];held=[t for t in train if t[0]['participant'] in people];cal=read(ROOT/f'outputs_calibration_fold_v37/fold_{fold}_calibration.json');states={r['id']:bias_state(natives[r['id']],cal[r['setup']],cfg) for r,d,_ in train};model=fit(fitting,cal,states,cfg);save_json(OUT/f'fold_{fold}_model.json',model)
        state_records.extend(dict(fold=fold,id=r['id'],participant=r['participant'],condition=r['condition'],held=r['participant'] in people,**states[r['id']]) for r,d,_ in train)
        for r,d,_ in held:
            v=velocities(d,cal[r['setup']]);base=np.c_[v[:,0],np.zeros(len(v)),v[:,1]]
            for name,m in [('joint_center',base),*[(f'bias_yaw_{w}',motion(r,d,model,states,w)) for w in WEIGHTS]]:
                xy,h=integrate(d,m);rows.append(dict(candidate=name,fold=fold,id=r['id'],participant=r['participant'],condition=r['condition'],startup_eligible=states[r['id']]['eligible'],**metrics(d,xy,h,cfg)))
        print('Wheel bias fold',fold,flush=True)
    save_json(OUT/'startup_states.json',dict(records=state_records));write_csv(OUT/'fold_trials.csv',rows);baseline={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize([r for r in rows if r['candidate']=='joint_center'])[1]};choices=[]
    for name in ['joint_center',*[f'bias_yaw_{w}' for w in WEIGHTS]]:
        s,p,c=summarize([r for r in rows if r['candidate']==name]);choices.append(dict(candidate=name,score=s['equal_participant_mean_position_rmse_m'],heading=s['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/baseline[p['participant']] for p in p)))
        for suffix,rr in [('participants',p),('maneuvers',c)]:write_csv(OUT/f'fold_{name}_{suffix}.csv',rr)
    selected=min((q for q in choices if q['worst_person_ratio']<=1.05),key=lambda q:q['score']);save_json(OUT/'selection.json',dict(selected=selected,candidates=choices,selected_before_validation=True));print('Selected',selected,flush=True)
    validation={};vr=[]
    if selected['candidate']!='joint_center' and selected['score']<choices[0]['score']:
        cal=read(ROOT/'outputs_calibration_fold_v37/all473_observed_calibration.json');states={r['id']:bias_state(natives[r['id']],cal[r['setup']],cfg) for r,d,_ in train};model=fit(train,cal,states,cfg);save_json(OUT/'full_model.json',model);weight=float(selected['candidate'].split('_')[-1]);source=ROOT/'outputs_observed_reference_v7';sm=read(source/'artifact_manifest.json');cache=OUT/'trajectories';cache.mkdir();valstates=[]
        from observed_training_experiment import observed_rows
        for r,d,_ in observed_rows(source,cfg,'validation',sm):
            states[r['id']]=bias_state(native(r,cfg),cal[r['setup']],cfg);valstates.append(dict(id=r['id'],participant=r['participant'],condition=r['condition'],**states[r['id']]));v=velocities(d,cal[r['setup']]);base=np.c_[v[:,0],np.zeros(len(v)),v[:,1]];arrays=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],imu_valid=d['imu_valid'])
            for name,m in [('joint_center',base),('selected_bias',motion(r,d,model,states,weight))]:
                xy,h=integrate(d,m);vr.append(dict(candidate=name,id=r['id'],participant=r['participant'],condition=r['condition'],startup_eligible=states[r['id']]['eligible'],**metrics(d,xy,h,cfg)));arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h;arrays[name+'_motion']=m
            np.savez_compressed(cache/(r['id']+'.npz'),**arrays)
        save_json(OUT/'validation_startup_states.json',dict(records=valstates));write_csv(OUT/'validation_trials.csv',vr)
        for name in ('joint_center','selected_bias'):
            s,p,c=summarize([r for r in vr if r['candidate']==name]);validation[name]=s
            for suffix,rr in [('participants',p),('maneuvers',c)]:write_csv(OUT/f'validation_{name}_{suffix}.csv',rr)
    save_json(OUT/'run.json',dict(selected=selected,candidates=choices,validation_summary=validation,test_accessed=False,production_model_unchanged=True,training_trials=473,held_trials=207,eligible_held_trials=sum(s['eligible'] for s in state_records if s['held']),held_startups=207,runtime_seconds=time.perf_counter()-start,source_sha256=digest(Path(__file__))))
    print(json.dumps(dict(candidates=choices,validation=validation),indent=2),flush=True)
if __name__=='__main__':main()
