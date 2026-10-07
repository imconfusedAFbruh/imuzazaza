"""CPU IMU-only forward context v17 inference; yaw/lateral remain ridge."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_inference_v14 import initialize_startup
from braking_context_experiment_v17 import features
def load_braking_context(out=None):
    out=Path(out) if out else ROOT/'outputs_braking_context_v17'
    if torch.cuda.is_available():raise RuntimeError('CPU comparator requires CUDA_VISIBLE_DEVICES=-1')
    run=json.loads((out/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed dependency '+name)
    for name,sha in json.loads((out/'artifact_manifest.json').read_text())['sha256'].items():
        if digest(out/name)!=sha:raise RuntimeError('Changed model artifact '+name)
    model=json.loads((out/'model.json').read_text());candidate=model['selected'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    def motion(data):
        imu={k:data[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu)
        if not candidate['gain']:return m
        setup=str(data['setup']);state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cal[setup]);x=features(imu,m,cal[setup],state,candidate['context']);fit=model['fits'][setup];z=np.c_[(x-fit['mean'])/fit['std'],np.ones(len(x))];r=np.clip(z@fit['weights'],-fit['cap'],fit['cap']);m[:,0]+=candidate['gain']*r;return m
    motion.reference_inputs='None. Optional initialization/startup_imu comes from original IMU acquisition first five seconds.'
    motion.future_context_seconds=max(1.28,candidate['context'])
    return motion
