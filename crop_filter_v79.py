"""Audit clock-dependent filtering on the same acquisition, TRAIN207 only."""
import json
import numpy as np
import pipeline as p
from clock_arbitrated_refit_v42 import OLD,NEW,load_cache
from clock_calibration_decomposition_v73 import motion
from backfill_metric_contract_v75 import SOURCE,summaries

OUT=p.ROOT/'outputs_crop_filter_v79'


def main():
    OUT.mkdir(exist_ok=False)
    p.save_json(OUT/'protocol.json',dict(hypothesis='Slope phase residual comes from clock-dependent crop boundaries changing offline gravity projection, not different raw acquisitions',
        comparison='Same old fitted model; old-cache motion transported to new clock versus actual new-cache motion; raw and linear wheel channels as controls',
        disproof='Raw/wheel channels differ materially on matched sensor support, or projected-yaw remainder is negligible',
        reference='No C3D motion used; transport support is a diagnostic only, never a new scoring mask',budget='one deterministic audit, no fits',promotion=False))
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text());models=json.loads((p.ROOT/'outputs_paired_clock_refit_v72/models.json').read_text())
    by_id={i:q['original_clock'] for q in models.values() for i in q['original_clock']['held_ids']}
    manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    frozen=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256'];rows=[]
    for ident,q in sorted(by_id.items()):
        r=inv[ident];assert r['partition']=='train' and ident not in q['fit_ids']
        old,om=load_cache(OLD,ident,manifests[OLD]);src=OLD if ident in protocol['fallback_old_clock_ids'] else NEW
        new,nm=load_cache(src,ident,manifests[src]);delta=nm['synchronization']['offset_s']-om['synchronization']['offset_s']
        mo=motion(old,q,r['setup']);f=SOURCE/'common_trajectories'/(ident+'.npz');assert p.digest(f)==frozen[str(f.relative_to(SOURCE))]
        with np.load(f) as z:
            rt=z['native_c3d_time_s'];actual=z['old_model_new_clock_motion'];clock=old['ref_t']-delta
            transported=[];valid=np.ones(len(rt),bool)
            for j in range(3):
                v,ok=p.masked_interp(rt,clock,mo[:,j],old['imu_valid']);transported.append(v);valid &=ok
            transported=np.c_[tuple(transported)];valid &=np.isfinite(actual).all(1)
            # Raw controls matched on the same physical IMU time, without optical targets.
            raw_old=[];raw_new=[]
            for j in range(18):
                x,ok=p.masked_interp(rt,clock,old['raw'][:,j],old['imu_valid'])
                y,nok=p.masked_interp(rt,new['ref_t'],new['raw'][:,j],new['imu_valid']);valid &=ok&nok
                raw_old.append(x);raw_new.append(y)
            raw_old=np.c_[tuple(raw_old)];raw_new=np.c_[tuple(raw_new)];assert valid.any()
            error=transported-actual
            edge=(rt-clock[0]<1.)|(clock[-1]-rt<1.)|(rt-new['ref_t'][0]<1.)|(new['ref_t'][-1]-rt<1.)
            omega=error[:,2];rms=lambda x:float(np.sqrt(np.mean(x*x))) if len(x) else None
            rows.append(dict(recording_id=ident,participant_id=r['participant'],maneuver=r['condition'],trial=r['repetition'],offset_delta_s=delta,
                matched_sensor_frames=int(valid.sum()),transport_coverage_pct=float(valid.mean()*100),
                raw_matched_RMSE_counts=rms((raw_old-raw_new)[valid]),linear_wheel_speed_transport_RMSE_mps=rms(error[valid,0]),
                projected_yaw_transport_RMSE_degps=float(np.rad2deg(rms(omega[valid]))),
                yaw_transport_edge_RMSE_degps=float(np.rad2deg(rms(omega[valid&edge]))) if (valid&edge).any() else None,
                yaw_transport_interior_RMSE_degps=float(np.rad2deg(rms(omega[valid&~edge]))) if (valid&~edge).any() else None,
                crop_sensor_start_shift_s=float(new['ref_t'][0]+nm['synchronization']['offset_s']-old['ref_t'][0]-om['synchronization']['offset_s']),
                crop_sensor_end_shift_s=float(new['ref_t'][-1]+nm['synchronization']['offset_s']-old['ref_t'][-1]-om['synchronization']['offset_s'])))
    assert len(rows)==207
    assert max(r['raw_matched_RMSE_counts'] for r in rows)<1e-6
    assert max(r['linear_wheel_speed_transport_RMSE_mps'] for r in rows)<1e-9
    p.write_csv(OUT/'filter_diagnostics.csv',rows)
    for name,groups in [('participants',('participant_id',)),('maneuvers',('maneuver',))]:p.write_csv(OUT/(name+'.csv'),summaries([dict(r,Failure_Flags='',Endpoint_Supported=False) for r in rows],groups))
    comparisons=json.loads((p.ROOT/'outputs_metric_contract_v75/trial_metrics.json').read_text())
    comparisons=[dict(r,experiment_id='v79_frozen_prediction_control') for r in comparisons if r['model'] in ('old_model_old_clock','old_model_new_clock')]
    p.write_csv(OUT/'trial_metrics.csv',comparisons);p.write_csv(OUT/'maneuver_summary.csv',summaries(comparisons,('model','maneuver')))
    p.save_json(OUT/'run.json',dict(recordings=len(rows),maximum_raw_matched_RMSE_counts=max(r['raw_matched_RMSE_counts'] for r in rows),
        maximum_wheel_transport_RMSE_mps=max(r['linear_wheel_speed_transport_RMSE_mps'] for r in rows),
        maximum_projected_yaw_transport_RMSE_degps=max(r['projected_yaw_transport_RMSE_degps'] for r in rows),
        promotion=False,test_accessed=False,validation_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text())


if __name__=='__main__':main()
