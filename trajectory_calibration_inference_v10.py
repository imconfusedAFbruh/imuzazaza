"""IMU-only loader for the sealed training-only trajectory correction."""
import json
import numpy as np
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from long_horizon_inference import load_endpoint_ensemble
from trajectory_calibration_v10 import design

def load_trajectory_calibration(folder=None):
    folder=ROOT/'outputs_trajectory_calibration_v10' if folder is None else folder
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed correction dependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())
    for name in ('weights.json','inner_selection.json','run.json'):
        if digest(folder/name)!=manifest['sha256'][name]:raise RuntimeError('Changed correction artifact '+name)
    state=json.loads((folder/'weights.json').read_text());weights={k:np.array(v) for k,v in state['weights'].items()}
    ridge=load_observed_ridge();endpoint=load_endpoint_ensemble() if state['gain'] else None
    def predict(data):
        imu={k:data[k] for k in ('setup','t','raw','imu_valid')}
        m=ridge(imu)
        if state['gain']:
            w=weights.get(str(imu['setup']),np.zeros(9));e=endpoint(imu)
            m+=state['gain']*np.einsum('nci,i->nc',design(m,e),w)
        return m
    predict.reference_inputs='none; initial pose is provided separately'
    predict.future_imu_context_seconds=1.28
    return predict
