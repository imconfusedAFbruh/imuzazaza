"""CPU IMU-only loader for total-coefficient iterative endpoint refinement."""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from stationary_gravity_inference_v14 import initialize_startup

def load_iterative_motion(folder=None):
    folder=ROOT/'outputs_motion_endpoint_iterative_v19' if folder is None else Path(folder)
    if torch.cuda.is_available():raise RuntimeError('Paired CPU inference requires CUDA_VISIBLE_DEVICES=-1 before torch initialization')
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed iterative experiment dependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())
    for name in ('model.json','inner_selection.json','run.json'):
        if digest(folder/name)!=manifest['sha256'][name]:raise RuntimeError('Changed iterative model artifact '+name)
    model=json.loads((folder/'model.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    def predict(data):
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')};base=ridge(sensor);setup=str(sensor['setup'])
        if setup not in model['fits']:return base
        state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cal[setup]);q=model['fits'][setup];x=feature_matrix(sensor,base,cal[setup],state,'gravity_rotation');z=np.c_[(x-q['mean'])/q['std'],np.ones(len(x))];r=np.clip(z@q['weights'],-np.array(q['cap']),np.array(q['cap']));m=base.copy();m[:,[0,2]]+=r
        if not np.array_equal(m[:,1],base[:,1]):raise RuntimeError('Lateral invariant failed')
        return m
    predict.reference_inputs='none; startup initialization is IMU-only, initial pose supplied separately'
    predict.context_seconds=.5
    predict.base_future_context_seconds=1.28
    return predict
