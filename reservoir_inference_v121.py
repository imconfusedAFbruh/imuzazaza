"""Frozen v121 full-TRAIN residual; optical labels are not prediction inputs."""
import json
import numpy as np
import pipeline as p
from dynamic_blend_inference_v34 import load_dynamic_blend
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from stationary_gravity_inference_v14 import initialize_startup
from reservoir_path_v121 import reservoir,CAP


def load_reservoir_model(folder=None):
    folder=p.ROOT/'models/reservoir_path_v121_completed' if folder is None else p.ROOT/folder
    manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name,sha in manifest.items():
        if p.digest(folder/name)!=sha:raise ValueError('Changed model artifact: '+name)
    model=json.loads((folder/'model.json').read_text())
    for name,sha in model['dependencies'].items():
        if p.digest(p.ROOT/name)!=sha:raise ValueError('Changed model dependency: '+name)
    baseline=load_dynamic_blend();ridge=load_observed_ridge()
    calibration=json.loads((p.ROOT/'outputs_amended_v2/calibration.json').read_text())
    def predict(data):
        sensor={k:data[k] for k in ('t','raw','imu_valid','setup')};setup=str(sensor['setup'])
        if setup not in model['fits']:raise ValueError('Unsupported acquisition setup: '+setup)
        state=data.get('initialization')
        if state is None:state=initialize_startup(data.get('startup_imu'),calibration[setup])
        motion=baseline(dict(sensor,initialization=state))
        features=feature_matrix(sensor,ridge(sensor),calibration[setup],state,'gravity_rotation')
        z=reservoir(features[:,30:45],sensor['imu_valid'],model['normalization'][setup])
        motion[:,[0,2]]+=np.clip(z@np.array(model['fits'][setup]['weights']),-1,1)*CAP
        if not np.isfinite(motion).all():raise ValueError('Nonfinite motion')
        return motion
    predict.reference_inputs='none; initial pose used separately for integration'
    return predict
