"""IMU-only v24 loader using the audited v21 predictor implementation."""
from pipeline import ROOT
from nonlinear_endpoint_inference_v21 import load_nonlinear_endpoint

def load_participant_folds(folder=None):
    return load_nonlinear_endpoint(ROOT/'outputs_participant_folds_v24' if folder is None else folder)
