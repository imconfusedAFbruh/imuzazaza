"""Frozen v8 three-channel motion inference; labels are not inference inputs."""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,velocities
from learning import load_predictor
from planar_experiment import planar_features
from planar_neural_experiment import PlanarResNet,predict_windows


def load_retrained_predictor(out=None):
    out=Path(out) if out is not None else ROOT/'outputs_observed_training_v8'
    selection=json.loads((out/'selection.json').read_text())
    for name,sha in selection['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError(f'Changed training dependency: {name}')
    manifest=json.loads((out/'artifact_manifest.json').read_text())
    for name,sha in manifest['sha256'].items():
        if digest(out/name)!=sha:raise RuntimeError(f'Changed v8 artifact: {name}')
    norm=json.loads((out/'normalization.json').read_text())
    mean,std,scale,cap=[np.array(norm[k],np.float32) for k in ('mean','std','target_scale','residual_cap')]
    parent=ROOT/'outputs_amended_v2'
    cal=json.loads((parent/'calibration.json').read_text())
    tcn_predict=load_predictor(parent,'tcn32')
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    state=torch.load(out/'all_three.pt',map_location='cpu',weights_only=True)
    model=PlanarResNet().to(device).eval();model.load_state_dict(state['state'])
    def motion(data):
        base=velocities(data,cal[str(data['setup'])]);tcn=tcn_predict(data,base)
        x=(planar_features(data,base,tcn,cal).astype(np.float32)-mean)/std
        correction=state['gain']*np.clip(predict_windows(model,x,device)*scale,-cap,cap)
        return np.c_[tcn[:,0],np.zeros(len(tcn)),tcn[:,1]]+correction
    motion.future_imu_context_seconds=1.28
    motion.reference_inputs='none; caller supplies initial reference pose only to integrator'
    return motion
