"""Exact v120 research-fold motion inference; no optical data or maneuver labels."""
import json
import numpy as np
import pipeline as p
from projected_yaw_folds_v52 import proxy
from braking_hysteresis_folds_v56 import hysteresis_features


def predict_motion(sensor, setup, model):
    cal=model['calibration'][setup]; yaw=model['yaw'][setup]; residual=model['residual'][setup]
    t=np.asarray(sensor['t']); raw=np.asarray(sensor['raw']); valid=np.asarray(sensor['imu_valid'],dtype=bool)
    if len(t)<2 or raw.shape!=(len(t),18) or valid.shape!=t.shape or not np.all(np.diff(t)>0):
        raise ValueError('Expected increasing timestamps, Nx18 IMU counts and matching validity')
    d=dict(t=t,raw=raw,imu_valid=valid)
    v=p.velocities(d,cal)
    motion=np.c_[v[:,0],np.zeros(len(t)),proxy(d,cal)*yaw['scale']+yaw['intercept']]
    features=hysteresis_features(d,cal)
    z=np.c_[(features-np.asarray(residual['mean']))/np.asarray(residual['std']),np.ones(len(t))]
    correction=np.clip((z@np.asarray(residual['coef']))*residual['scale'],[-.1,-.05],[.1,.05])
    correction[~valid]=0
    motion[:,[0,2]]+=model['gain']*correction
    if not np.isfinite(motion).all():raise ValueError('Nonfinite predicted motion')
    return motion


def load_fold(bundle, fold):
    """Load an explicitly selected research fold; never infer a fold from motion."""
    bundle=p.ROOT/bundle
    manifest=json.loads((bundle/'artifact_manifest.json').read_text())['sha256']
    path=bundle/f'fold_{int(fold)}.json'
    if p.digest(path)!=manifest[path.name]:raise ValueError('Model artifact hash mismatch')
    return json.loads(path.read_text())
