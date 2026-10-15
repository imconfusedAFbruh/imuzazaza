"""Offline IMU-only motion inference for the sealed training-selected v34 blend.

The caller supplies raw18 sensor arrays and original startup IMU history.
An initial position/heading is supplied separately to integrate_motion. No
optical trajectory, derivative, correction, or reset is consumed by prediction.
"""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT, digest
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from stationary_gravity_inference_v14 import initialize_startup
from nonlinear_endpoint_experiment_v21 import nonlinear_features
from dynamic_tilt_experiment_v33 import dynamic_features


def _read_sealed(folder, name):
    manifest = json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    if digest(folder/name) != manifest[name]:
        raise RuntimeError('Changed sealed artifact: '+str(folder/name))
    return json.loads((folder/name).read_text())


def load_dynamic_blend(folder=None):
    """Return predict(sensor)->N x [forward,lateral,yaw] empirical motion.

    Paired reproduction requires a process started with CUDA_VISIBLE_DEVICES=-1.
    Full-record noncausal filtering makes this an offline reconstruction model.
    """
    folder = Path(folder) if folder else ROOT/'outputs_dynamic_blend_v34'
    if torch.cuda.is_available():
        raise RuntimeError('Paired CPU reproduction requires CUDA_VISIBLE_DEVICES=-1 before importing torch')
    meta = _read_sealed(folder, 'model.json')
    selection = _read_sealed(folder, 'selection.json')
    if meta['weight'] != selection['selected']['weight']:
        raise RuntimeError('Model weight differs from training-selected weight')
    for name, expected in [(meta['original_parent'], meta['original_sha256']),
                           (meta['dynamic_parent'], meta['dynamic_sha256']),
                           ('dynamic_tilt_experiment_v33.py', meta['feature_source_sha256'])]:
        if digest(ROOT/name) != expected:
            raise RuntimeError('Changed blend dependency: '+name)
    original_folder = (ROOT/meta['original_parent']).parent
    run = _read_sealed(original_folder, 'run.json')
    for name, expected in run['provenance'].items():
        if digest(ROOT/name) != expected:
            raise RuntimeError('Changed original dependency: '+name)
    original = _read_sealed(original_folder, 'model.json')
    dynamic = _read_sealed((ROOT/meta['dynamic_parent']).parent,
                           Path(meta['dynamic_parent']).name)
    cal = json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    ridge = load_observed_ridge()

    def predict(data):
        sensor = {k: data[k] for k in ('setup', 't', 'raw', 'imu_valid')}
        setup = str(sensor['setup'])
        if setup not in original['fits'] or setup not in dynamic['fits']:
            raise ValueError('No fitted correction for acquisition setup '+setup)
        t, raw = np.asarray(sensor['t']), np.asarray(sensor['raw'])
        if raw.shape != (len(t), 18) or len(t) < 2 or not np.all(np.diff(t) > 0):
            raise ValueError('Expected increasing times and N x 18 raw L/R/C samples')
        if np.shape(sensor['imu_valid']) != (len(t),):
            raise ValueError('Invalid IMU support mask')
        state = data.get('initialization')
        if state is None:
            state = initialize_startup(data.get('startup_imu'), cal[setup])
        base = ridge(sensor)
        linear = feature_matrix(sensor, base, cal[setup], state, 'gravity_rotation')
        nonlinear = nonlinear_features(linear)
        extra = dynamic_features(sensor, base, cal[setup], state, dynamic['cutoff'])

        def corrected(model, extra_features=None):
            clip = model['feature_clip'][setup]
            x = np.c_[linear, np.clip(nonlinear[:,75:], clip['low'], clip['high'])].astype(np.float32)
            if extra_features is not None:
                q = model['extra_clip'][setup]
                x = np.c_[x, np.clip(extra_features, q['low'], q['high'])].astype(np.float32)
            fitted = model['fits'][setup]
            z = np.c_[(x-fitted['mean'])/fitted['std'], np.ones(len(x))]
            residual = np.clip(z@fitted['weights'], -np.asarray(fitted['cap']), fitted['cap'])
            motion = base.copy()
            motion[:,[0,2]] += model['candidate']['gain']*residual
            return motion

        a, b = corrected(original), corrected(dynamic, extra)
        result = (1-meta['weight'])*a + meta['weight']*b
        if not np.allclose(result[:,1], base[:,1], atol=1e-14, rtol=1e-14, equal_nan=True):
            raise RuntimeError('Unexpected lateral correction')
        return result

    predict.reference_inputs = 'none; initialization must originate from IMU startup only'
    predict.filtering = 'offline, full-record forward/backward lowpass; no causal claim'
    predict.empirical_units = True
    predict.training_trials = len(meta['training_ids'])
    return predict


def integrate_motion(time_s, motion, initial_xy_m, initial_heading_rad, imu_valid=None):
    """Single initial pose, trapezoid body motion and midpoint heading integration."""
    t = np.asarray(time_s)
    m = np.asarray(motion)
    if m.shape != (len(t),3) or not np.all(np.diff(t)>0):
        raise ValueError('Invalid time/motion arrays')
    dt = np.diff(t)
    v = (m[1:]+m[:-1])/2
    heading = np.r_[0,np.cumsum(dt*v[:,2])] + float(initial_heading_rad)
    angle = (heading[1:]+heading[:-1])/2
    c, s = np.cos(angle), np.sin(angle)
    step = dt[:,None]*np.c_[v[:,0]*c-v[:,1]*s, v[:,0]*s+v[:,1]*c]
    xy = np.vstack((np.zeros(2),np.cumsum(step,axis=0))) + np.asarray(initial_xy_m)
    if imu_valid is not None:
        bad = np.flatnonzero(~np.asarray(imu_valid, dtype=bool))
        if len(bad):
            xy[bad[0]:] = np.nan
            heading[bad[0]:] = np.nan
    return xy, heading
