"""Sealed v38 IMU-only motion loader, native startup, no optical inputs.

predict(sensor, imu_csv_path) -> Nx[forward,lateral,yaw]. sensor must contain
exactly setup,t,raw,imu_valid. Offline future context/filtering remains.
"""
import json
from pathlib import Path
import numpy as np
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import initialization,feature_matrix,correction
from nonlinear_endpoint_experiment_v21 import nonlinear_features,adapted
from dynamic_tilt_experiment_v33 import dynamic_features,expanded

def load_clock_refit(folder=None):
    folder=ROOT/'outputs_clock_refit_v38' if folder is None else Path(folder)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name in ('protocol.json','run.json','v21_model.json','tilt_model.json','blend_model.json'):
        if digest(folder/name)!=manifest[name]:raise RuntimeError('Changed v38 model:'+name)
    protocol=json.loads((folder/'protocol.json').read_text())
    for name,sha in protocol['parent_hashes'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed inherited dependency:'+name)
    ridge=load_observed_ridge();cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    cfg=protocol['old_clock_settings'];v21=json.loads((folder/'v21_model.json').read_text());tilt=json.loads((folder/'tilt_model.json').read_text());blend=json.loads((folder/'blend_model.json').read_text())
    candidate=protocol['parameters'];weight=float(blend['weight'])
    def predict(sensor,imu_csv_path):
        if set(sensor)!=set(('setup','t','raw','imu_valid')):raise ValueError('Only setup,t,raw,imu_valid are accepted; no reference fields')
        setup=str(sensor['setup']);path=Path(imu_csv_path).resolve()
        if setup not in cal:raise ValueError('No inherited calibration for this setup')
        state=initialization(dict(setup=setup,imu=str(path)),cal,cfg)
        motion=ridge(sensor);x=feature_matrix(sensor,motion,cal[setup],state,'gravity_rotation')
        entry=dict(motion=motion,linear=x,nonlinear=nonlinear_features(x),setup=setup)
        z=adapted([entry],candidate['basis'],v21['feature_clip'])[0]
        original=correction(dict(z,x={'gravity_rotation':z['x']}),v21['fits'],dict(candidate,mode='gravity_rotation'))
        entry['extra']=dynamic_features(sensor,motion,cal[setup],state,tilt['cutoff'])
        z=expanded([entry],tilt['feature_clip'],tilt['extra_clip'])[0]
        dynamic=correction(dict(z,x={'gravity_rotation':z['x']}),tilt['fits'],dict(candidate,mode='gravity_rotation'))
        return (1-weight)*original+weight*dynamic,state
    return predict
