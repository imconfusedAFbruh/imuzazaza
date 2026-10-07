"""IMU-only loader for sealed v21 selected physical-product comparator."""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from stationary_gravity_inference_v14 import initialize_startup
from nonlinear_endpoint_experiment_v21 import nonlinear_features

def load_nonlinear_endpoint(folder=None):
    folder=ROOT/'outputs_nonlinear_endpoint_v21' if folder is None else Path(folder)
    if torch.cuda.is_available():raise RuntimeError('Set CUDA_VISIBLE_DEVICES=-1 before initializing torch for paired CPU reproduction')
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed v21 dependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name in ('model.json','run.json','inner_selection.json'):
        if digest(folder/name)!=manifest[name]:raise RuntimeError('Changed v21 fitted artifact '+name)
    model=json.loads((folder/'model.json').read_text());candidate=model['candidate'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    def predict(data):
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')};base=ridge(sensor);setup=str(sensor['setup'])
        if not candidate['gain'] or setup not in model['fits']:return base
        state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cal[setup]);x=feature_matrix(sensor,base,cal[setup],state,'gravity_rotation')
        if candidate['basis']=='physical_products':
            q=model['feature_clip'][setup];xx=nonlinear_features(x);x=np.c_[x,np.clip(xx[:,75:],q['low'],q['high'])].astype(np.float32)
        fitted=model['fits'][setup];z=np.c_[(x-fitted['mean'])/fitted['std'],np.ones(len(x))];residual=np.clip(z@fitted['weights'],-np.array(fitted['cap']),np.array(fitted['cap']));result=base.copy();result[:,[0,2]]+=candidate['gain']*residual
        if not np.array_equal(result[:,1],base[:,1]):raise RuntimeError('Lateral invariant violated')
        return result
    predict.reference_inputs='none; optical initialpose separately supplied; startup state from IMU only'
    predict.context_seconds=.5
    predict.base_future_context_seconds=1.28
    return predict
