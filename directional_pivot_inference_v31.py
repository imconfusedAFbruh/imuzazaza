"""Selected IMU-only directional pivot model; reference orientation is unchanged."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json
import numpy as np
from pipeline import ROOT,digest
from controlled_motion_inference_v25 import load_controlled
from rotation_motion_experiment_v29 import inputs
def load_directional_pivot():
    folder=ROOT/'outputs_directional_pivot_v31';manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name in ('model.json','selection.json','run.json'):
        if digest(folder/name)!=manifest[name]:raise RuntimeError('Changed directional pivot artifact '+name)
    model=json.loads((folder/'model.json').read_text());parent=ROOT/'outputs_controlled_motion_v25'
    if digest(parent/'artifact_manifest.json')!=model['parent_manifest_sha256']:raise RuntimeError('Changed directional parent')
    c=model['candidate'];cal=json.loads((parent/'model.json').read_text())['calibration'];base=load_controlled('conditional')
    def predict(data):
        d={k:data[k] for k in ('setup','t','raw','imu_valid')};s=str(d['setup']);m=base(data).copy();f=inputs(d,m,cal[s]);g=f['gate']*np.where(m[:,2]>=0,c['positive'],c['negative']);m[:,0]=(1-g)*m[:,0]+g*f['wheel_v'];return m
    predict.reference_inputs='none; original initial pose supplied separately'
    predict.context_seconds=.5
    predict.base_future_context_seconds=1.28
    predict.orientation_amended=False
    return predict
