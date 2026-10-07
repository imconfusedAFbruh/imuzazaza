"""CPU IMU-only v14 inference; startup initialization must be supplied."""
import json
from pathlib import Path
import numpy as np
import torch
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,digest
from pipeline import runs
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix

def initialize_startup(startup,cal):
    """Startup raw18 samples/times only; identical frozen v14 gate."""
    default=dict(gravity=cal['center_gravity_direction'],gyro_bias=cal['gyro_bias_counts'][2],eligible=False,quiet_seconds=0.,algorithm='native initial five seconds',reason='No contiguous initial stationary candidate')
    if startup is None:return dict(default,reason='No startup IMU history supplied; declared training-date fallback')
    t=np.asarray(startup['t']);raw=np.asarray(startup['raw']);valid=np.asarray(startup.get('imu_valid',np.ones(len(t),bool)))
    if len(t)<150:return dict(default,reason='Initial shared IMU interval too short')
    keep=t<=t[0]+5.;t,raw,valid=t[keep],raw[keep],valid[keep]
    acc=raw[:,12:15]/cal['accel_counts_per_g'][2];gyro=(raw[:,15:18]-cal['gyro_bias_counts'][2])*abs(cal['terms'][2]['scale']);wheel=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in cal['terms'][:2]]];sd=np.sqrt(np.maximum(uniform_filter1d(acc**2,101,axis=0)-uniform_filter1d(acc,101,axis=0)**2,0));gate=(np.max(np.abs(wheel),axis=1)<.05)&(np.linalg.norm(gyro,axis=1)<.1)&(np.max(sd,axis=1)<.02)&valid;gate[:50]=False;gate[-50:]=False;quiet=np.zeros(len(gate),bool)
    for a,b in runs(gate):
        if b-a>=100:quiet[a:b]=True
    if not quiet.any():return default
    g=np.median(acc[quiet],axis=0);bias=np.median(raw[quiet,15:18],axis=0);return dict(gravity=g.tolist(),gyro_bias=bias.tolist(),eligible=True,quiet_seconds=float(quiet.sum()/100),algorithm=default['algorithm'],reason='')

def load_stationary_gravity(out=None):
    out=Path(out) if out else ROOT/'outputs_stationary_gravity_v14'
    if torch.cuda.is_available():raise RuntimeError('v14 paired reproduction requires CUDA_VISIBLE_DEVICES=-1 before process startup')
    run=json.loads((out/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed experiment dependency '+name)
    for name,sha in json.loads((out/'artifact_manifest.json').read_text())['sha256'].items():
        if digest(out/name)!=sha:raise RuntimeError('Changed model artifact '+name)
    model=json.loads((out/'model.json').read_text());candidate=model['candidate'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    def motion(data):
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')};base=ridge(sensor)
        if not candidate['gain']:return base
        setup=str(data['setup']);state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cal[setup]);fit=model['fits'][setup];x=feature_matrix(sensor,base,cal[setup],state,candidate['mode']);z=np.c_[(x-fit['mean'])/fit['std'],np.ones(len(x))];residual=np.clip(z@fit['weights'],-np.array(fit['cap']),np.array(fit['cap']));base[:,[0,2]]+=candidate['gain']*residual;return base
    motion.reference_inputs='none; startup initialization is IMU-only and initial optical pose is supplied separately'
    motion.context_seconds=.5
    motion.base_future_context_seconds=1.28
    return motion
