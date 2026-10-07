"""IMU-only pivot correction; optical orientation remains unchanged."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json
import numpy as np
from pipeline import ROOT,digest
from controlled_motion_inference_v25 import load_controlled
from nonlinear_endpoint_inference_v21 import load_nonlinear_endpoint
from controlled_motion_experiment_v25 import basic_features,slip_prediction
from rotation_motion_experiment_v29 import inputs

def load_pivot():
    folder=ROOT/'outputs_pivot_channels_v30';manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name in ('model.json','selection.json','run.json'):
        if digest(folder/name)!=manifest[name]:raise RuntimeError('Changed pivot artifact '+name)
    model=json.loads((folder/'model.json').read_text());c=model['candidate'];parent=ROOT/model['parent']
    if digest(parent/'artifact_manifest.json')!=model['parent_manifest_sha256']:raise RuntimeError('Changed pivot parent')
    q=json.loads((parent/'model.json').read_text());cal=q['calibration']
    base=load_controlled('conditional') if c['branch']=='conservative' else load_nonlinear_endpoint()
    def predict(data):
        d={k:data[k] for k in ('setup','t','raw','imu_valid')};s=str(d['setup']);m=base(data).copy()
        if c['branch']=='stronger':
            x,_,_,_=basic_features(d,m,cal[s]);m[:,0]+=.5*slip_prediction(dict(setup=s,x=x),q['correction']['slip'])
        info=inputs(d,m,cal[s]);fg=info['gate']*c['forward'];lg=info['gate']*c['lateral']
        m[:,0]=(1-fg)*m[:,0]+fg*info['wheel_v'];m[:,1]*=1-lg
        return m
    predict.reference_inputs='none; integrator receives original initial pose separately'
    predict.orientation_amended=False
    return predict
