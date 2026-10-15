"""Fixed-model first-order clock-phase diagnostic; never select a clock by ATE."""
import csv,json
import numpy as np
import pipeline as p
from backfill_metric_contract_v75 import SOURCE,summaries

OUT=p.ROOT/'outputs_clock_phase_v78'


def phase(xy,h,m,offset):
    c,s=np.cos(h),np.sin(h)
    world=np.c_[m[:,0]*c-m[:,1]*s,m[:,0]*s+m[:,1]*c]
    travel=xy-xy[0];jtravel=np.c_[-travel[:,1],travel[:,0]]
    return offset*(world-world[0]-m[0,2]*jtravel),offset*(m[:,2]-m[0,2])


def main():
    t=np.arange(101)/100;xy=np.c_[t*t/2,np.zeros(len(t))];m=np.c_[t,np.zeros((len(t),2))]
    q,w=phase(xy,np.zeros(len(t)),m,.1);assert np.allclose(q[:,0],.1*t) and not w.any()
    OUT.mkdir(exist_ok=False)
    p.save_json(OUT/'protocol.json',dict(hypothesis='Fixed-model clock-change trajectory differences are first-order motion-phase effects, rather than changed initial optical pose',
        first_order='delta_xy = delta_offset*(world_velocity(t)-world_velocity(0)-omega(0)*J*travel(t)); delta_heading=delta_offset*(omega(t)-omega(0))',
        budget='one deterministic diagnostic, no search',disproof='large residual against actual fixed-model difference despite sufficiently small clock changes',
        controls='same stored initial pose, support and old fitted model; all207TRAIN',promotion=False))
    changes={r['id']:r for r in csv.DictReader((p.ROOT/'outputs_clock_arbitrated_v42/clock_changes.csv').open()) if r['partition']=='train'}
    manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256'];rows=[]
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    for f in sorted((SOURCE/'common_trajectories').glob('*.npz')):
        r=inv[f.stem];assert r['partition']=='train' and p.digest(f)==manifest[str(f.relative_to(SOURCE))]
        with np.load(f) as z:
            old=z['old_model_old_clock_xy_m'];new=z['old_model_new_clock_xy_m'];h=z['old_model_old_clock_heading_rad'];m=z['old_model_old_clock_motion']
            dh=z['old_model_new_clock_heading_rad']-h;delta=new-old;offset=float(changes[f.stem]['offset_delta_s'])
            assert np.array_equal(old[0],new[0]) and dh[0]==0
            approximate,ah=phase(old,h,m,offset);valid=z['reference_valid']&np.isfinite(delta).all(1)
            rms=lambda a:float(np.sqrt(np.mean(np.sum(a[valid]**2,axis=1))))
            actual=rms(delta);residual=rms(delta-approximate);initial=z['time_s']<=1
            rows.append(dict(recording_id=f.stem,participant_id=r['participant'],maneuver=r['condition'],trial=r['repetition'],split='train_fixed_model_diagnostic',
                offset_delta_s=offset,initial_pose_difference_m=0.,initial_heading_difference_deg=0.,
                initial_speed_abs_mean_mps=float(np.mean(np.linalg.norm(m[initial,:2],axis=1))),initial_yaw_abs_mean_degps=float(np.rad2deg(np.mean(abs(m[initial,2])))),
                initial_yaw_point_degps=float(np.rad2deg(m[0,2])),actual_clock_position_difference_mm=1000*actual,first_order_residual_mm=1000*residual,
                first_order_explained_squared_fraction=1-(residual/actual)**2 if actual>1e-9 else None,
                actual_heading_difference_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(dh[valid]**2)))),
                heading_phase_residual_deg=float(np.rad2deg(np.sqrt(np.mean((dh[valid]-ah[valid])**2)))),source_sha256=p.digest(f)))
    assert len(rows)==207
    p.write_csv(OUT/'phase_diagnostics.csv',rows)
    for name,groups in [('summary',('split',)),('participants',('participant_id',)),('maneuvers',('maneuver',))]:
        # Reuse numeric participant-balanced aggregation; these rows are diagnostics, not candidate scores.
        p.write_csv(OUT/(name+'.csv'),summaries([dict(r,Failure_Flags='',Endpoint_Supported=False) for r in rows],groups))
    historical=json.loads((p.ROOT/'outputs_metric_contract_v75/trial_metrics.json').read_text())
    comparison=[dict(r,experiment_id='v78_unchanged_frozen_predictions') for r in historical if r['model'] in ('old_model_old_clock','old_model_new_clock')]
    p.write_csv(OUT/'trial_metrics.csv',comparison);p.write_csv(OUT/'maneuver_summary.csv',summaries(comparison,('model','maneuver')))
    p.write_csv(OUT/'participant_summary.csv',summaries(comparison,('model','participant_id')))
    changed=[r for r in rows if abs(r['offset_delta_s'])>1e-6]
    p.save_json(OUT/'run.json',dict(recordings=207,changed_clocks=len(changed),initial_pose_checks=207,
        median_changed_actual_mm=float(np.median([r['actual_clock_position_difference_mm'] for r in changed])),
        median_changed_residual_mm=float(np.median([r['first_order_residual_mm'] for r in changed])),
        median_changed_explained=float(np.median([r['first_order_explained_squared_fraction'] for r in changed])),promotion=False,test_accessed=False,validation_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text())


if __name__=='__main__':main()
