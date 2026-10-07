"""CPU-only training-participant diagnostics; no validation/test access."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfiltfilt
from pipeline import ROOT,save_json,write_csv,digest,velocities,runs
from observed_training_experiment import observed_rows
from learning import training_group

FOLD={'No.3','No.8','No.15','No.20'}
def smooth(x):
    return sosfiltfilt(butter(2,6,fs=100,output='sos'),x,axis=0) if len(x)>=40 else x.copy()
def fit(train,features,alpha=.1):
    result={}
    for setup in {e['setup'] for e in train}:
        es=[e for e in train if e['setup']==setup];x=np.concatenate([e[features][e['valid']][::10] for e in es]);y=np.concatenate([e['a'][e['valid']][::10] for e in es]);groups=sum([[e['group']]*len(e['a'][e['valid']][::10]) for e in es],[]);counts=Counter(groups);w=np.array([1/counts[g] for g in groups]);w/=w.sum();mean=(x*w[:,None]).sum(0);std=np.maximum(np.sqrt(((x-mean)**2*w[:,None]).sum(0)),1e-5);z=np.c_[(x-mean)/std,np.ones(len(x))];reg=np.eye(z.shape[1])*alpha;reg[-1,-1]=0;coef=np.linalg.solve(z.T@(z*w[:,None])+reg,z.T@(y*w));result[setup]=(mean,std,coef)
    return result
def main():
    out=ROOT/'outputs_feature_diagnosis_v12'
    if out.exists():raise RuntimeError('Preserve diagnosis')
    out.mkdir();source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());entries=[];stats=[]
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        c=cal[row['setup']];raw=d['raw'];m=velocities(d,c);w=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]];wy=(w[:,1]-w[:,0])/c['track_width_m'];wa=np.gradient(smooth(w.mean(1)),d['t']);mask=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v']);a=np.full(len(mask),np.nan);valid=np.zeros(len(mask),bool)
        for lo,hi in runs(mask):
            if hi-lo>=40:a[lo:hi]=np.gradient(d['gt_v'][lo:hi],d['t'][lo:hi]);valid[lo+15:hi-15]=True
        acc=smooth(raw[:,12:15]/c['accel_counts_per_g'][2]-c['center_gravity_direction']);gyro=smooth(raw[:,15:18]-np.array(c['gyro_bias_counts'][2]))*abs(c['terms'][2]['scale']);center=np.c_[acc,gyro];full=np.c_[center,smooth(w),m[:,0],m[:,1],m[:,0]*m[:,1],wa];lags=np.c_[*[np.stack([np.interp(d['t']+lag,d['t'],center[:,i]) for i in range(6)],1) for lag in (-.3,0,.3)]]
        entries.append(dict(row=row,setup=row['setup'],group=training_group(row),a=a,valid=valid,center=center,full=full,lags=lags,wheel=wa[:,None]))
        braking=valid&(a<-.5);target=d['gt_yaw'][mask];ch=m[mask,1];wheel=wy[mask];good=np.isfinite(target)&np.isfinite(ch)&np.isfinite(wheel)
        stats.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],setup=row['setup'],fold='inner' if row['participant'] in FOLD else 'fit',label_fraction=float(mask.mean()),accel_label_fraction=float(valid.mean()),wheel_yaw_rmse_rad_s=float(np.sqrt(np.mean((wheel[good]-target[good])**2))),chassis_yaw_rmse_rad_s=float(np.sqrt(np.mean((ch[good]-target[good])**2))),wheel_chassis_disagreement_rms_rad_s=float(np.sqrt(np.mean((wheel[good]-ch[good])**2))),wheel_yaw_bias_rad_s=float(np.mean(wheel[good]-target[good])),chassis_yaw_bias_rad_s=float(np.mean(ch[good]-target[good])),brake_frames=int(braking.sum()),brake_wheel_accel_error_mean_mps2=float(np.mean(wa[braking]-a[braking])) if braking.any() else '',brake_forward_velocity_bias_mps=float(np.mean(m[braking,0]-d['gt_v'][braking])) if braking.any() else '',center_gravity_quiet_delta_g=float(np.linalg.norm(np.median(raw[np.abs(m[:,0])<.05,12:15],axis=0)/c['accel_counts_per_g'][2]-c['center_gravity_direction'])) if np.any(np.abs(m[:,0])<.05) else ''))
    fitrows=[e for e in entries if e['row']['participant'] not in FOLD];inner=[e for e in entries if e['row']['participant'] in FOLD];results=[]
    for name in ('center','wheel','full','lags'):
        fits=fit(fitrows,name)
        for e in inner:
            if not e['valid'].any():continue
            mean,std,coef=fits[e['setup']];pred=np.c_[(e[name]-mean)/std,np.ones(len(e['a']))]@coef;v=e['valid'];brake=v&(e['a']<-.5);err=pred-e['a'];results.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],model=name,rmse_mps2=float(np.sqrt(np.mean(err[v]**2))),bias_mps2=float(err[v].mean()),brake_rmse_mps2=float(np.sqrt(np.mean(err[brake]**2))) if brake.any() else '',brake_bias_mps2=float(err[brake].mean()) if brake.any() else '',samples=int(v.sum())))
    write_csv(out/'training_conflicts.csv',stats);write_csv(out/'acceleration_inner_fold.csv',results);summary=[]
    for condition in ('ALL','PS','SL'):
        for model in ('center','wheel','full','lags'):
            rs=[r for r in results if r['model']==model and (condition=='ALL' or r['condition']==condition)];ps={r['participant'] for r in rs};summary.append(dict(condition=condition,model=model,trials=len(rs),participants=len(ps),participant_mean_trial_accel_rmse=float(np.mean([np.mean([r['rmse_mps2'] for r in rs if r['participant']==p]) for p in ps])),mean_trial_brake_bias=float(np.mean([r['brake_bias_mps2'] for r in rs if r['brake_bias_mps2']!='']))))
    save_json(out/'summary.json',dict(summary=summary,training_trials=len(entries),inner_ids=sorted(FOLD),test_evaluated=False,validation_evaluated=False,interpretation='Training inner participant fold only; models regress acceleration, not trajectory; full model uses physical base instead of ridge inputs, so diagnostic approximation to v11.',provenance={str(Path(__file__).relative_to(ROOT)):digest(Path(__file__)),str(source.relative_to(ROOT)/'artifact_manifest.json'):digest(source/'artifact_manifest.json')}));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
