"""IMU-only long-horizon experiment inference, with the original window context."""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,velocities
from learning import load_predictor
from planar_experiment import planar_features
from planar_neural_experiment import PlanarResNet,predict_windows


def load_long_horizon(out=None,label=None):
    out=Path(out) if out else ROOT/'outputs_long_horizon_v9'
    selection=json.loads((out/'selection.json').read_text());label=label or selection['selected']
    if label not in selection['candidates']:raise ValueError('Unknown declared candidate')
    for name,sha in selection['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed training dependency '+name)
    for name,sha in json.loads((out/'artifact_manifest.json').read_text())['sha256'].items():
        if digest(out/name)!=sha:raise RuntimeError('Changed model artifact '+name)
    norm=json.loads((out/'normalization.json').read_text())
    mean,std,scale,cap=[np.array(norm[k],np.float32) for k in ('mean','std','target_scale','residual_cap')]
    parent=ROOT/'outputs_amended_v2';cal=json.loads((parent/'calibration.json').read_text());tcn=load_predictor(parent,'tcn32')
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    labels=[label] if not label.endswith('_ensemble') else [label.removesuffix('_ensemble')+'_'+str(s) for s in (42,43,44)]
    models=[]
    for name in labels:
        checkpoint=torch.load(out/(name+'.pt'),map_location='cpu',weights_only=True)
        model=PlanarResNet().to(device).eval();model.load_state_dict(checkpoint['state']);models.append((model,checkpoint['gain']))
    def motion(data):
        base=velocities(data,cal[str(data['setup'])]);reference=tcn(data,base)
        x=(planar_features(data,base,reference,cal).astype(np.float32)-mean)/std
        corrections=[gain*np.clip(predict_windows(model,x,device)*scale,-cap,cap) for model,gain in models]
        return np.c_[reference[:,0],np.zeros(len(reference)),reference[:,1]]+np.mean(corrections,axis=0)
    motion.future_imu_context_seconds=1.28
    motion.reference_inputs='none; initial pose is supplied separately to integration'
    return motion


def load_endpoint_ensemble():
    return load_long_horizon(label='endpoint_ensemble')


def load_short_ensemble():
    return load_long_horizon(label='short_ensemble')
