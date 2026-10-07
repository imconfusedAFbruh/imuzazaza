"""CPU IMU-only endpoint-trained motion residual with startup initialization."""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from stationary_gravity_inference_v14 import initialize_startup

def load_motion_endpoint(folder=None):
    folder=ROOT/'outputs_motion_endpoint_v16' if folder is None else Path(folder)
    if torch.cuda.is_available():raise RuntimeError('v16 paired CPU reproduction requires CUDA_VISIBLE_DEVICES=-1 before torch initialization')
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed endpoint experiment dependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())
    for name in ('model.json','run.json','inner_selection.json'):
        if digest(folder/name)!=manifest['sha256'][name]:raise RuntimeError('Changed endpoint model artifact '+name)
    model=json.loads((folder/'model.json').read_text());candidate=model['candidate'];ridge=load_observed_ridge();cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    def predict(data):
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')};base=ridge(sensor)
        if not candidate['gain']:return base
        setup=str(sensor['setup'])
        if setup not in model['fits']:return base
        state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cal[setup]);fit=model['fits'][setup];x=feature_matrix(sensor,base,cal[setup],state,candidate['mode']);z=np.c_[(x-fit['mean'])/fit['std'],np.ones(len(x))];residual=np.clip(z@fit['weights'],-np.array(fit['cap']),np.array(fit['cap']));result=base.copy();result[:,[0,2]]+=candidate['gain']*residual
        if not np.array_equal(result[:,1],base[:,1]):raise RuntimeError('Lateral invariant violated')
        return result
    predict.reference_inputs='none; initial pose supplied separately, initialization from IMU-only startup'
    predict.context_seconds=.5
    predict.base_future_context_seconds=1.28
    return predict
