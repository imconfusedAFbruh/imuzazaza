"""Load the fixed three-seed yaw ensemble or a declared individual seed."""
import json
import numpy as np
import torch
from pipeline import ROOT,digest
from observed_ridge_inference import load_observed_ridge
from yaw_heading_experiment_v12 import YawTCN,imu_features,predict

def load_yaw_ensemble(folder=None,seed=None):
    folder=ROOT/'outputs_yaw_heading_ensemble_v15' if folder is None else folder
    run=json.loads((folder/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed yaw ensemble dependency '+name)
    manifest=json.loads((folder/'artifact_manifest.json').read_text())
    for name in ('run.json','normalization.json','seed42.pt','seed43.pt','seed44.pt'):
        if digest(folder/name)!=manifest['sha256'][name]:raise RuntimeError('Changed yaw ensemble artifact '+name)
    seeds=[42,43,44] if seed is None else [seed]
    if any(s not in (42,43,44) for s in seeds):raise ValueError('Only predeclared seeds42/43/44')
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');norm=json.loads((folder/'normalization.json').read_text());models=[]
    for s in seeds:
        state=torch.load(folder/f'seed{s}.pt',map_location='cpu',weights_only=True)
        if state['epoch']!=12 or state['gain']!=.5:raise RuntimeError('Fixed epoch/gain changed')
        model=YawTCN().to(device).eval();model.load_state_dict(state['state']);models.append(model)
    ridge=load_observed_ridge();cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    def motion(data):
        imu={k:data[k] for k in ('setup','t','raw','imu_valid')};baseline=ridge(imu);x=imu_features(imu,baseline,cal)
        correction=np.mean([predict(model,x,norm,device) for model in models],axis=0);result=baseline.copy();result[:,2]+=.5*correction
        if not np.array_equal(result[:,:2],baseline[:,:2]):raise RuntimeError('Forward/lateral changed')
        return result
    motion.reference_inputs='none; initial pose supplied separately'
    motion.future_imu_context_seconds=1.28
    motion.seeds=seeds
    return motion
