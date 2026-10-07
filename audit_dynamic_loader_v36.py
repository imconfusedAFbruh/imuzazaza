"""Reproduce sealed v34 motion with fresh IMU-only startup initialization."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json
import time
import numpy as np
import torch
from pipeline import ROOT, digest, imu_streams, sample_streams, metrics, summarize, save_json, write_csv
from observed_training_experiment import observed_rows
from dynamic_blend_inference_v34 import load_dynamic_blend, integrate_motion
from stationary_gravity_inference_v14 import initialize_startup

OUT = ROOT/'outputs_dynamic_loader_v36'


def main():
    started = time.perf_counter()
    if OUT.exists():
        raise RuntimeError('Preserve completed audit')
    OUT.mkdir()
    torch.set_num_threads(2)
    source = ROOT/'outputs_observed_reference_v7'
    cfg = json.loads((source/'run.json').read_text())['settings']
    manifest = json.loads((source/'artifact_manifest.json').read_text())
    predict = load_dynamic_blend()
    cal = json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    oldstates = {r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
    cache = ROOT/'outputs_dynamic_blend_v34'
    sealed = json.loads((cache/'artifact_manifest.json').read_text())['sha256']
    rows = []
    state_delta = []
    for row, data, _ in observed_rows(source,cfg,'validation',manifest):
        native_t, native_raw, native_valid = sample_streams(imu_streams(ROOT/row['imu']),cfg)
        startup = dict(t=native_t,raw=native_raw,imu_valid=native_valid)
        state = initialize_startup(startup, cal[row['setup']])
        previous = oldstates[row['id']]
        state_delta.append(dict(id=row['id'],gravity_max_difference=float(np.max(np.abs(np.array(state['gravity'])-previous['gravity']))),bias_max_difference=float(np.max(np.abs(np.array(state['gyro_bias'])-previous['gyro_bias']))),eligible_equal=state['eligible']==previous['eligible']))
        sensor = {k:data[k] for k in ('setup','t','raw','imu_valid')}
        sensor['startup_imu'] = startup
        motion = predict(sensor)
        xy, h = integrate_motion(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
        path = cache/'trajectories'/(row['id']+'.npz')
        if digest(path)!=sealed[str(path.relative_to(cache))]:
            raise RuntimeError('Changed sealed prediction')
        with np.load(path) as z:
            motion_delta = float(np.nanmax(np.abs(motion-z['selected_blend_motion'])))
            xy_delta = float(np.nanmax(np.abs(xy-z['selected_blend_xy_m'])))
        record = dict(id=row['id'],participant=row['participant'],condition=row['condition'],motion_max_difference=motion_delta,xy_max_difference_m=xy_delta,**metrics(data,xy,h,cfg))
        rows.append(record)
        if len(rows)==1:
            # Reference-shaped values deliberately cannot enter the predictor.
            poisoned = dict(sensor,gt_xy=np.full((len(data['t']),2),1e9),gt_heading=np.full(len(data['t']),1e9),gt_v=np.full(len(data['t']),1e9),gt_yaw=np.full(len(data['t']),1e9))
            if not np.array_equal(predict(poisoned),motion,equal_nan=True):
                raise RuntimeError('Reference fields affected inference')
        if len(rows)%10==0:
            print('Reproduced',len(rows),flush=True)
    summary, people, maneuvers = summarize(rows)
    write_csv(OUT/'trials.csv',rows)
    write_csv(OUT/'participants.csv',people)
    write_csv(OUT/'maneuvers.csv',maneuvers)
    write_csv(OUT/'startup_reproduction.csv',state_delta)
    result = dict(summary=summary,maximum_motion_difference=max(r['motion_max_difference'] for r in rows),maximum_xy_difference_m=max(r['xy_max_difference_m'] for r in rows),maximum_startup_gravity_difference=max(r['gravity_max_difference'] for r in state_delta),maximum_startup_bias_difference=max(r['bias_max_difference'] for r in state_delta),all_startup_eligibility_equal=all(r['eligible_equal'] for r in state_delta),reference_poison_test_passed=True,test_accessed=False,inference_inputs='setup,time,raw18,IMU_valid,native_startup_IMU only',initial_pose='same one original optical initial pose; no subsequent optical updates',runtime_seconds=time.perf_counter()-started,loader_sha256=digest(ROOT/'dynamic_blend_inference_v34.py'))
    save_json(OUT/'run.json',result)
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}))
    print(json.dumps(result,indent=2),flush=True)
    if result['maximum_xy_difference_m']>1e-8 or abs(summary['equal_participant_mean_position_rmse_m']-.1007021193993738)>1e-9:
        raise RuntimeError('Loader does not reproduce candidate; inspect audit and do not promote')


if __name__=='__main__':
    main()
