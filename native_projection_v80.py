"""Full sensor-record projection before evaluator clocks/crops; TRAIN207 audit."""
import json
import numpy as np
import pipeline as p
from projected_yaw_folds_v52 import proxy
from clock_arbitrated_refit_v42 import OLD,NEW,load_cache
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_native_projection_v80'


def sample_projection(full,cal,sensor_times):
    # Same fixed offline proxy, now filtered on sensor-only full-record support.
    return p.masked_interp(snap_grid(full['t'],sensor_times),full['t'],proxy(full,cal),full['imu_valid'])


def snap_grid(t,query):
    # Undo sub-nanosecond cancellation in ref_t + frozen offset at exact grid edges.
    ix=np.clip(np.rint((query-t[0])/np.median(np.diff(t))).astype(int),0,len(t)-1)
    return np.where(abs(t[ix]-query)<1e-9,t[ix],query)


def main():
    from test_native_projection_v80 import check
    check(sample_projection)
    OUT.mkdir(exist_ok=False);(OUT/'sensors').mkdir()
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())
    models=verified_json(p.ROOT/'outputs_paired_clock_refit_v72','models.json')
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    by_id={i:q['original_clock'] for q in models.values() for i in q['original_clock']['held_ids']}
    p.save_json(OUT/'protocol.json',dict(hypothesis='Full sensor-record filtering makes projected yaw invariant to evaluator optical crop',
        filter='Identical v52 offline 0.3Hz second-order filter, full common L/R/C IMU100Hz grid only',
        budget='one correctness audit; next v81 two frozen clocks, fixed weight1, no hyperparameter search',
        prospective_gates='ATE improves; every participant and maneuver <=1.05 relative matched-clock crop control; P95, route, last-supported endpoint and RTE10 aggregate <=1.05; no new trial above1m ATE or1m last-supported endpoint; no lost frames/trials',
        endpoint='Genuine acquisition endpoint unsupported stays null; no genuine endpoint improvement claimed',
        limitations='Offline future sensor samples; inherited evaluator clocks/geometry/QC remain; no strict nesting claim',validation_accessed=False,test_accessed=False,promotion=False))
    rows=[]
    for n,(ident,q) in enumerate(sorted(by_id.items()),1):
        row=inv[ident];assert row['partition']=='train'
        old,om=load_cache(OLD,ident,manifests[OLD]);src=OLD if ident in protocol['fallback_old_clock_ids'] else NEW
        new,nm=load_cache(src,ident,manifests[src])
        raw_path=p.ROOT/row['imu'];assert p.digest(raw_path)==om['signature']['imu_sha256']==nm['signature']['imu_sha256']
        t,raw,valid=p.sample_streams(p.imu_streams(raw_path),protocol['old_clock_settings'])
        full=dict(t=t,raw=raw,imu_valid=valid);cal=q['calibration'][row['setup']]
        arrays=dict(full);offsets={};projections={};maximum=0.
        for name,d,meta in [('old',old,om),('new',new,nm)]:
            sensor_time=d['ref_t']+meta['synchronization']['offset_s'];ix=np.rint((sensor_time-t[0])*100).astype(int)
            assert (ix>=0).all() and (ix<len(t)).all() and np.max(abs(t[ix]-sensor_time))<1e-8
            maximum=max(maximum,float(np.max(abs(raw[ix]-d['raw']))))
            assert np.array_equal(valid[ix],d['imu_valid'])
            projected,ok=sample_projection(full,cal,sensor_time)
            assert np.array_equal(ok,d['imu_valid'])
            assert np.max(abs(projected[ok]-proxy(full,cal)[ix][ok]))<1e-6
            arrays[name+'_indices']=ix;offsets[name]=meta['synchronization']['offset_s'];projections[name]=projected
        overlap=np.intersect1d(arrays['old_indices'],arrays['new_indices'])
        a=projections['old'][np.searchsorted(arrays['old_indices'],overlap)]
        b=projections['new'][np.searchsorted(arrays['new_indices'],overlap)]
        delta=float(np.max(abs(a-b)));assert delta<1e-6 and maximum<1e-6
        np.savez_compressed(OUT/'sensors'/(ident+'.npz'),**arrays)
        p.save_json(OUT/'sensors'/(ident+'.json'),dict(offsets=offsets,raw_sha256=p.digest(raw_path)))
        rows.append(dict(recording_id=ident,participant_id=row['participant'],maneuver=row['condition'],full_sensor_frames=len(t),
            matched_sensor_frames=len(overlap),max_raw_difference_counts=maximum,max_shared_projection_difference_counts=delta,
            old_crop_vs_full_projection_RMSE_counts=float(np.sqrt(np.mean((proxy(old,cal)-projections['old'])**2)))))
        if n%25==0:print('v80 prepared',n,flush=True)
    assert len(rows)==207
    p.write_csv(OUT/'invariance.csv',rows)
    p.save_json(OUT/'run.json',dict(recordings=len(rows),max_raw_difference_counts=max(r['max_raw_difference_counts'] for r in rows),
        max_shared_projection_difference_counts=max(r['max_shared_projection_difference_counts'] for r in rows),
        synthetic_check=True,promotion=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
