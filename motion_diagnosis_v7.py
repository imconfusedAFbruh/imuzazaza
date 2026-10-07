"""Training/validation motion consistency diagnosis, never test data."""
import csv,json
from pathlib import Path
import numpy as np
import pipeline as p

def main():
    source=p.ROOT/'outputs_synchronization_v5'
    out=p.ROOT/'outputs_motion_diagnosis_v7'
    out.mkdir(exist_ok=True)
    if (out/'summary.json').exists():raise RuntimeError('Preserve completed diagnosis')
    cal=json.loads((source/'calibration.json').read_text())
    rows=list(csv.DictReader((p.ROOT/'outputs_amended_v2/inventory.csv').open(newline='')))
    records=[]
    for row in rows:
        if row['partition'] not in ('train','validation'):continue
        path=source/'cache'/(row['id']+'.npz')
        if not path.exists():continue
        with np.load(path) as z:d={k:z[k] for k in z.files}
        base=p.velocities(d,cal[row['setup']])
        stop=min(int(np.searchsorted(d['t'],2.)),len(d['t'])-1)
        h=d['gt_heading'];g=d['raw'][:,15:18]
        yaw2=np.trapezoid(base[:stop+1,1],d['t'][:stop+1])
        truth2=h[stop]-h[0]
        gr=np.trapezoid(g[:stop+1]-np.array(cal[row['setup']]['gyro_bias_counts'][2]),d['t'][:stop+1],axis=0)
        gyro_vector_degrees=np.linalg.norm(gr)*abs(cal[row['setup']]['terms'][2]['scale'])*180/np.pi
        m=d['label_valid']&d['gt_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])
        initialnorms=[float(np.median(np.linalg.norm(d['raw'][:stop+1,i*6:i*6+3],axis=1))) for i in range(3)]
        record={k:row[k] for k in ('id','participant','condition','date','partition')}
        record.update(initial_2s_gt_heading_change_deg=float(np.rad2deg(truth2)),
                      initial_2s_imu_yaw_change_deg=float(np.rad2deg(yaw2)),
                      initial_2s_heading_disagreement_deg=float(np.rad2deg(truth2-yaw2)),
                      initial_2s_center_gyro_vector_integral_deg=float(gyro_vector_degrees),
                      speed_rmse_m_s=float(np.sqrt(np.mean((base[m,0]-d['gt_v'][m])**2))),
                      yaw_rmse_deg_s=float(np.rad2deg(np.sqrt(np.mean((base[m,1]-d['gt_yaw'][m])**2)))),
                      center_accel_counts_initial_2s=initialnorms[2],
                      maximum_absolute_gyro_counts=float(np.max(np.abs(d['raw'][:,[3,4,5,9,10,11,15,16,17]]))),
                      fraction_gyro_abs_above_32000=float(np.mean(np.abs(d['raw'][:,[3,4,5,9,10,11,15,16,17]])>32000)))
        records.append(record)
    p.write_csv(out/'trials.csv',records)
    summaries=[]
    for partition in ('train','validation'):
        for condition in sorted({r['condition'] for r in records if r['partition']==partition}):
            rr=[r for r in records if r['partition']==partition and r['condition']==condition]
            summaries.append(dict(partition=partition,condition=condition,trials=len(rr),
              median_initial_2s_heading_disagreement_deg=float(np.nanmedian([abs(r['initial_2s_heading_disagreement_deg']) for r in rr])),
              initial_2s_heading_disagreement_over_10deg=sum(abs(r['initial_2s_heading_disagreement_deg'])>10 for r in rr),
              initial_2s_gt_over_10deg_with_gyro_vector_under_5deg=sum(abs(r['initial_2s_gt_heading_change_deg'])>10 and r['initial_2s_center_gyro_vector_integral_deg']<5 for r in rr),
              mean_speed_rmse_m_s=float(np.mean([r['speed_rmse_m_s'] for r in rr])),
              mean_yaw_rmse_deg_s=float(np.mean([r['yaw_rmse_deg_s'] for r in rr]))))
    p.save_json(out/'summary.json',summaries)
    p.save_json(out/'provenance.json',dict(source_sha256=p.digest(Path(__file__)),partitions=['train','validation'],test_evaluated=False,
      note='Center vector integral assumes empirical isotropic gyro scale. Reference/IMU disagreement is a diagnosis, not proof of which sensor is correct. No predictor fitting or GT trajectory alignment. Saturation near integer register limit is only a proxy because encoding unknown.'))
    print(json.dumps([r for r in summaries if r['partition']=='validation'],indent=2))

def supported_followup():
    import ezc3d
    source=p.ROOT/'outputs_synchronization_v5';out=p.ROOT/'outputs_motion_diagnosis_v7'
    cal=json.loads((source/'calibration.json').read_text())
    cfg=json.loads((source/'run.json').read_text())['settings']
    records=[]
    for row in csv.DictReader((p.ROOT/'outputs_amended_v2/inventory.csv').open(newline='')):
        if row['partition']!='validation':continue
        path=source/'cache'/(row['id']+'.npz')
        if not path.exists():continue
        c=ezc3d.c3d(str(p.ROOT/row['c3d']))
        labels=[x.strip() for x in c['parameters']['POINT']['LABELS']['value']]
        ids=[labels.index(x) for x in ('L_FAL','R_FAL')]
        residual=c['data']['meta_points']['residuals'][0,ids].T
        camera=c['data']['meta_points']['camera_masks'][:,ids].any(axis=0).T
        rawsupport=camera.all(axis=1)&(residual>0).all(axis=1)
        with np.load(path) as z:d={k:z[k] for k in z.files}
        raw_t=np.arange(len(rawsupport))/float(c['header']['points']['frame_rate'])
        support=np.interp(d['ref_t'],raw_t,rawsupport.astype(float),left=0,right=0)>.999
        good=support&d['gt_valid']&d['imu_valid']
        if not good.any():continue
        start=np.flatnonzero(good)[0]
        dd={k:(v[start:] if isinstance(v,np.ndarray) and v.ndim>0 and len(v)==len(d['t']) else v) for k,v in d.items()}
        dd['t']=dd['t']-dd['t'][0]
        dd['gt_valid']=good[start:];dd['label_valid']=dd['label_valid']&good[start:]
        base=p.velocities(dd,cal[row['setup']]);xy,h=p.integrate(dd['t'],base,dd['gt_xy'][0],dd['gt_heading'][0],dd['imu_valid'])
        result=p.metrics(dd,xy,h,cfg)
        m=dd['label_valid']&np.isfinite(dd['gt_v'])&np.isfinite(dd['gt_yaw'])
        result.update({k:row[k] for k in ('id','participant','condition','date')})
        result.update(start_trim_s=float(d['t'][start]),remaining_camera_supported_frac=float(good[start:].mean()),
            supported_speed_rmse_m_s=float(np.sqrt(np.mean((base[m,0]-dd['gt_v'][m])**2))),
            supported_yaw_rmse_deg_s=float(np.rad2deg(np.sqrt(np.mean((base[m,1]-dd['gt_yaw'][m])**2)))))
        records.append(result)
    p.write_csv(out/'supported_validation.csv',records)
    summary,people,conditions=p.summarize(records)
    p.save_json(out/'supported_summary.json',dict(summary=summary,people=people,conditions=conditions,
      caveat='Diagnostic changed scored span and initial pose, unchanged old reference filtering, synchronization and calibration. Not a like-for-like model improvement. Camera participation and positive residual required; no GT continuous correction.'))
    print(json.dumps(dict(summary=summary,conditions=conditions),indent=2))

if __name__=='__main__':main()
