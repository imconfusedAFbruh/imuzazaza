"""IMU-only gravity-state endpoint model; all sensor constants remain fixed."""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from stationary_gravity_inference_v14 import initialize_startup
from nonlinear_endpoint_experiment_v21 import nonlinear_features
from adaptive_gravity_experiment_v23 import gravity_states,state_features

def load_adaptive_gravity(folder=None):
    folder=ROOT/'outputs_adaptive_gravity_v23' if folder is None else Path(folder)
    if torch.cuda.is_available():raise RuntimeError('Paired CPU prediction requires CUDA_VISIBLE_DEVICES=-1 before initializing torch')
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed gravity-state source '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name in ('model.json','inner_selection.json','run.json'):
        if digest(folder/name)!=manifest[name]:raise RuntimeError('Changed gravity-state model '+name)
    model=json.loads((folder/'model.json').read_text());variant=model['variant'];ridge=load_observed_ridge();cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    def predict(data):
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')};base=ridge(sensor);setup=str(sensor['setup'])
        if variant=='zero' or setup not in model['fits']:return base
        if variant=='static_v21':
            state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cal[setup]);x=feature_matrix(sensor,base,cal[setup],state,'gravity_rotation')
        else:
            states,stats=gravity_states(sensor,cal[setup]);x=state_features(sensor,base,cal[setup],states[variant],stats['eligible'])
        xx=nonlinear_features(x);clip=model['feature_clip'][setup];x=np.c_[x,np.clip(xx[:,75:],clip['low'],clip['high'])].astype(np.float32);q=model['fits'][setup];z=np.c_[(x-q['mean'])/q['std'],np.ones(len(x))];r=np.clip(z@q['weights'],-np.array(q['cap']),np.array(q['cap']));m=base.copy();m[:,[0,2]]+=.5*r
        if not np.array_equal(m[:,1],base[:,1]):raise RuntimeError('Lateral invariant failed')
        return m
    predict.reference_inputs='none; no participant/record lookup; initial pose supplied separately'
    predict.state_estimation='Gravity unit direction only; all training sensor bias/scale/magnitude constants fixed'
    predict.future_imu_context_seconds='Full available valid IMU segment for new gravity variants; legacy static base has1.28s future context'
    return predict
