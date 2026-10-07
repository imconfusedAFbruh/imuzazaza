"""IMU-only yaw residual loader; forward and lateral stay fixed ridge."""
import json
import numpy as np
import torch
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from yaw_heading_experiment_v12 import YawTCN,imu_features,predict

def load_yaw_heading(folder=None,comparison=False):
    folder=ROOT/'outputs_yaw_heading_v12' if folder is None else folder
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed yaw experiment dependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())
    for name in ('yaw_tcn.pt','normalization.json','inner_selection.json','run.json'):
        if digest(folder/name)!=manifest['sha256'][name]:raise RuntimeError('Changed yaw experiment artifact '+name)
    norm=json.loads((folder/'normalization.json').read_text());checkpoint=torch.load(folder/'yaw_tcn.pt',map_location='cpu',weights_only=True)
    gain=checkpoint['comparison_gain'] if comparison else checkpoint['gain'];device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=YawTCN().to(device).eval();model.load_state_dict(checkpoint['state'])
    ridge=load_observed_ridge();cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    def motion(data):
        imu={k:data[k] for k in ('setup','t','raw','imu_valid')};baseline=ridge(imu)
        if not gain:return baseline
        x=imu_features(imu,baseline,cal);correction=predict(model,x,norm,device);result=baseline.copy();result[:,2]+=gain*correction
        if not np.array_equal(result[:,:2],baseline[:,:2]):raise RuntimeError('Forward/lateral invariant violated')
        return result
    motion.reference_inputs='none; initial pose supplied separately'
    motion.future_imu_context_seconds=1.28
    motion.yaw_head_context_seconds=.30
    return motion
