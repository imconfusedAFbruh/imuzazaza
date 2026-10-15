"""Diagnose failed baseline reproduction only; never call v121."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
import pipeline as p
from observed_training_experiment import observed_rows
from dynamic_blend_inference_v34 import load_dynamic_blend,integrate_motion
from stationary_gravity_inference_v14 import initialize_startup

out=p.ROOT/'research_state/v123_baseline_failure'
out.mkdir(exist_ok=False)
source=p.ROOT/'outputs_observed_reference_v7'
cfg=json.loads((source/'run.json').read_text())['settings']
manifest=json.loads((source/'artifact_manifest.json').read_text())
saved={r['id']:r for r in csv.DictReader((p.ROOT/'outputs_dynamic_blend_v34/selected_blend_trials.csv').open())}
cal=json.loads((p.ROOT/'outputs_amended_v2/calibration.json').read_text())
states={r['id']:r for r in json.loads((p.ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
completed={f.stem for f in (p.ROOT/'outputs_frozen_validation_v123_completed/baseline').glob('*.npz')}
predict=load_dynamic_blend()
for row,d,_ in observed_rows(source,cfg,'validation',manifest):
    if row['id'] in completed:continue
    ident=row['id'];t,raw,iv=p.sample_streams(p.imu_streams(p.ROOT/row['imu']),cfg)
    state=initialize_startup(dict(t=t,raw=raw,imu_valid=iv),cal[row['setup']])
    sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};sensor['initialization']=state
    records=[]
    with np.load(p.ROOT/'outputs_dynamic_blend_v34/trajectories'/(ident+'.npz')) as z:
        for threads in (2,4):
            torch.set_num_threads(threads);m=predict(sensor)
            xy,h=integrate_motion(d['t'],m,d['gt_xy'][0],d['gt_heading'][0],d['imu_valid'])
            score=p.metrics(d,xy,h,cfg)
            records.append(dict(threads=threads,heading_rmse_deg=score['heading_rmse_deg'],
                heading_metric_delta=score['heading_rmse_deg']-float(saved[ident]['heading_rmse_deg']),
                max_motion_delta=float(np.nanmax(abs(m-z['selected_blend_motion']))),
                max_xy_delta=float(np.nanmax(abs(xy-z['selected_blend_xy_m']))),
                max_heading_delta=float(np.nanmax(abs(h-z['selected_blend_heading_rad'])))))
        cached=p.metrics(d,z['selected_blend_xy_m'],z['selected_blend_heading_rad'],cfg)
    result=dict(id=ident,old_state=states[ident],fresh_state=state,
                saved_heading=float(saved[ident]['heading_rmse_deg']),cached_heading=cached['heading_rmse_deg'],
                baseline_only=True,candidate_evaluations=0,checks=records)
    p.save_json(out/'diagnosis.json',result);print(json.dumps(result,indent=2));break
