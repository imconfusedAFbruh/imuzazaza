"""Reference-free inference for the sealed controlled motion experiments."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json
import numpy as np
from pipeline import ROOT,digest,velocities
from controlled_motion_experiment_v25 import basic_features,quiet_yaw_state,predict_affine,corrected
from nonlinear_endpoint_experiment_v21 import nonlinear_features
from stationary_gravity_experiment_v14 import feature_matrix
from stationary_gravity_inference_v14 import initialize_startup
from observed_ridge_inference import load_observed_ridge

def load_controlled(branch='conditional',variant='selected'):
    folder=ROOT/('outputs_controlled_refit_v26' if branch=='independent' else 'outputs_controlled_motion_v25')
    manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name in ('model.json','selection.json','run.json'):
        if digest(folder/name)!=manifest[name]:raise RuntimeError('Changed controlled fitted artifact '+name)
    model=json.loads((folder/'model.json').read_text());selection=json.loads((folder/'selection.json').read_text())
    c=selection['representatives'][variant];cal=model['calibration'];base=model['base'];ind=branch=='independent'
    ridge=None if ind else load_observed_ridge()
    def predict(data):
        d={k:data[k] for k in ('setup','t','raw','imu_valid')};s=str(d['setup']);cc=cal[s]
        if ind:
            v=velocities(d,cc);motion=np.c_[v[:,0],np.zeros(len(v)),v[:,1]]
            state=dict(gravity=cc['center_gravity_direction'],gyro_bias=cc['gyro_bias_counts'][2],eligible=False)
        else:
            motion=ridge(d);state=data.get('initialization') or initialize_startup(data.get('startup_imu'),cc)
        x=feature_matrix(d,motion,cc,state,'gravity_rotation');e=dict(setup=s,motion=motion,linear=x,nonlinear=nonlinear_features(x))
        motion=predict_affine(e,base)
        if ind:
            q=base['lateral'][s];z=np.c_[(x-q['mean'])/q['std'],np.ones(len(x))];motion[:,1]=np.clip(z@q['weights'],-q['cap'],q['cap'])
        features,ax,regime,wheel=basic_features(d,motion,cc);state,stats=quiet_yaw_state(d,motion,cc,wheel)
        entry=dict(setup=s,data=d,motion=motion,x=features,ax=ax,regime=regime,yaw_state=state)
        return corrected(entry,model['correction'],c)
    predict.reference_inputs='none; initial pose supplied to integrator separately'
    predict.offline=True
    return predict

def load_conditional():return load_controlled('conditional')
def load_independent():return load_controlled('independent')
