"""Conservative IMU stationary candidate audit, training only, CPU only."""
import json
import numpy as np
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,save_json,write_csv,velocities,runs,digest
from observed_training_experiment import observed_rows
def main():
    source=ROOT/'outputs_observed_reference_v7';out=ROOT/'outputs_stationary_mount_diagnosis_v12'
    if out.exists():raise RuntimeError('Preserve diagnosis')
    out.mkdir();cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());records=[]
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        if row['date'] not in ('2026-09-24','2026-09-25'):continue
        c=cal[row['setup']];raw=d['raw'];w=np.c_[*[raw[:,f['column']]*f['scale']+f['intercept'] for f in c['terms'][:2]]];acc=raw[:,12:15]/c['accel_counts_per_g'][2];gyr=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale']);sd=np.sqrt(np.maximum(uniform_filter1d(acc**2,101,axis=0)-uniform_filter1d(acc,101,axis=0)**2,0));candidate=(np.max(np.abs(w),axis=1)<.05)&(np.linalg.norm(gyr,axis=1)<.1)&(np.max(sd,axis=1)<.02)&d['imu_valid'];valid=np.zeros(len(candidate),bool)
        for a,b in runs(candidate):
            if b-a>=100:valid[a:b]=True
        record=dict(id=row['id'],participant=row['participant'],condition=row['condition'],setup=row['setup'],candidate_stationary_s=float(valid.sum()/100))
        if valid.any():
            median=np.median(acc[valid],axis=0);globalg=np.array(c['center_gravity_direction']);record.update(gravity_delta_g=float(np.linalg.norm(median-globalg)),gravity_direction_delta_deg=float(np.rad2deg(np.arccos(np.clip(median@globalg/np.linalg.norm(median)/np.linalg.norm(globalg),-1,1)))),acc_norm_g=float(np.linalg.norm(median)),gravity_x=float(median[0]),gravity_y=float(median[1]),gravity_z=float(median[2]))
        records.append(record)
    write_csv(out/'stationary_candidates.csv',records);save_json(out/'summary.json',dict(records=records,validation_evaluated=False,test_evaluated=False,gates='Both calibrated wheel speeds<0.05m/s; empirically scaled center gyro norm<0.1rad/s; center acceleration each-axis 1.01s rollingSD<0.02g; uninterrupted IMU; minimum1s contiguous. Fixed diagnostic thresholds, not selected by trajectory error. Candidates are not independently verified physical stationarity.',provenance={__file__:digest(__file__)}))
if __name__=='__main__':main()
