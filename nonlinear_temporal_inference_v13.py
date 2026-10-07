"""Sealed v13 nonlinear residual candidate, not promoted."""
import json
import numpy as np
from pipeline import ROOT,digest
from learning import load_predictor
from observed_reference_experiment import load_planar
from observed_ridge_experiment import imu_features
from observed_ridge_inference import load_observed_ridge
from nonlinear_temporal_v13 import expand,correct

def load_nonlinear_temporal():
    folder=ROOT/'outputs_nonlinear_temporal_v13'
    run=json.loads((folder/'run.json').read_text())
    manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name in ('run.json','model.npz','selection.json'):
        if digest(folder/name)!=manifest[name]:raise RuntimeError('Changed candidate artifact')
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed candidate dependency')
    load_observed_ridge()
    parent=ROOT/'outputs_amended_v2';cal=json.loads((parent/'calibration.json').read_text());tcn=load_predictor(parent,'tcn32');champ=load_planar()
    selected=json.loads((ROOT/'outputs_observed_ridge_v8/selection.json').read_text())['best']
    with np.load(ROOT/'outputs_observed_ridge_v8/linear_artifacts.npz') as a:
        mean,std,cap,w=[a[k].copy() for k in ('mean','std','cap',f'weights_{selected["alpha"]}')]
    with np.load(folder/'model.npz') as a:model={k:a[k].copy() for k in a.files}
    c=run['selected']
    def predict(d):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')}
        x,m=imu_features(imu,cal,tcn,champ)
        m=m+selected['gain']*np.clip(np.c_[(x-mean)/std,np.ones(len(x))]@w,-cap,cap)
        return correct(dict(x=expand(x,m).astype(np.float32),motion=m),model,c['gain'],c['channels'])
    return predict
