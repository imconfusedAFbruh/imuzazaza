"""Reuse the IMU-only v21 feature loader with sealed v22 weights/bounds."""
from pathlib import Path
from pipeline import ROOT
from nonlinear_endpoint_inference_v21 import load_nonlinear_endpoint

def load_nonlinear_endpoint_v22(folder=None):
    return load_nonlinear_endpoint(ROOT/'outputs_nonlinear_endpoint_tuning_v22' if folder is None else Path(folder))
