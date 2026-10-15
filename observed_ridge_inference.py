"""Load the sealed observed-reference v8 ridge motion predictor."""
import json

import numpy as np

from pipeline import ROOT, digest
from learning import load_predictor
from observed_reference_experiment import load_planar
from observed_ridge_experiment import imu_features
from legacy_inference_compat_v121 import dependency_matches


def load_observed_ridge(folder=None):
    """Return predict(IMU-only data)->N x [forward,lateral,yaw] motion."""
    folder = ROOT/'outputs_observed_ridge_v8' if folder is None else folder
    selection = json.loads((folder/'selection.json').read_text())
    for name, sha in selection['provenance'].items():
        if not dependency_matches(name, sha, digest(ROOT/name)):
            raise RuntimeError(f'Ridge dependency changed: {name}')
    manifest = json.loads((folder/'artifact_manifest.json').read_text())
    for name in ('selection.json','linear_artifacts.npz','normalization.json'):
        if digest(folder/name) != manifest['sha256'][name]:
            raise RuntimeError(f'Sealed ridge artifact changed: {name}')
    best = selection['best']
    with np.load(folder/'linear_artifacts.npz') as arrays:
        mean, std, cap = [arrays[name].copy() for name in ('mean','std','cap')]
        weights = arrays[f'weights_{best["alpha"]}'].copy() if best['gain'] else None
    parent = ROOT/'outputs_amended_v2'
    cal = json.loads((parent/'calibration.json').read_text())
    tcn, champion = load_predictor(parent,'tcn32'), load_planar()

    def predict(data):
        x, motion = imu_features(data,cal,tcn,champion)
        if not best['gain']:
            return motion
        design = np.c_[(x-mean)/std,np.ones(len(x))]
        return motion + best['gain']*np.clip(design@weights,-cap,cap)

    return predict
