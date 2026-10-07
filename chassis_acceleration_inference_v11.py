"""Offline IMU-only empirical acceleration smoother loader."""
import json
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from chassis_acceleration_v11 import features,correct

def load_chassis_acceleration(folder=None):
    folder=ROOT/'outputs_chassis_acceleration_v11' if folder is None else folder
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed acceleration dependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())
    for name in ('model.json','inner_selection.json','run.json'):
        if digest(folder/name)!=manifest['sha256'][name]:raise RuntimeError('Changed acceleration artifact '+name)
    model=json.loads((folder/'model.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    def predict(data):
        imu={k:data[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu)
        c=model['candidate']
        if not c['gain']:return m
        setup=str(imu['setup']);x,wa=features(imu,m,cal[setup]);entry=dict(data=imu,motion=m,x=x,wa=wa,setup=setup)
        if setup not in model['fits']:return m
        return correct(entry,model['fits'],c['lambda'],c['prior_floor'],c['gain'])
    predict.reference_inputs='none; initial pose supplied separately'
    predict.future_imu_context_seconds='complete available recording; offline smoothing'
    return predict
