"""IMU-only CPU channel blend v20; selected weights currently equal v16."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json
from pathlib import Path
import torch
from pipeline import ROOT,digest
from stationary_gravity_inference_v14 import initialize_startup
from stationary_gravity_experiment_v14 import feature_matrix
from braking_context_experiment_v17 import features
from motion_blend_experiment_v20 import prediction
from observed_ridge_inference import load_observed_ridge
def load_motion_blend(folder=None):
    folder=Path(folder) if folder else ROOT/'outputs_motion_blend_v20'
    if torch.cuda.is_available():raise RuntimeError('CPUreproductionrequiresCUDA_VISIBLE_DEVICES=-1')
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changeddependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())
    for name,sha in manifest['sha256'].items():
        if digest(folder/name)!=sha:raise RuntimeError('Changedartifact '+name)
    model=json.loads((folder/'model.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    def predict(data):
        imu={k:data[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu);setup=str(imu['setup'])
        if setup not in model['endpoint_fits'] or setup not in model['forward_fits']:return m
        state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cal[setup]);e=dict(motion=m,setup=setup,x16=feature_matrix(imu,m,cal[setup],state,'gravity_rotation'),x17=features(imu,m,cal[setup],state,.5));return prediction(e,model['endpoint_fits'],model['forward_fits'],model['selected'])
    predict.reference_inputs='none; optional original startup IMU state and separate initial pose'
    predict.base_future_context_seconds=1.28
    return predict
