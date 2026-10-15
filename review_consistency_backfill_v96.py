"""Independent profile arithmetic and frozen metric accounting; no fitting."""
import csv,json
import numpy as np
import pipeline as p
from review_basin_geometry_v93 import interpolate,corr,check
from basin_completeness_v91 import verify
from clock_consistency_v94 import OUT as PROFILE, BASINS,SIGNALS,FROZEN,CANDIDATES,MODES,DOC
from failed_metrics_v95 import OUT as BACKFILL,SOURCES

OUT=p.ROOT/'outputs_consistency_backfill_review_v96'


def main():
    check();assert not (p.ROOT/'research_state/STOP').exists()
    hashes=sum(verify(q) for q in (PROFILE,BACKFILL,BASINS,SIGNALS,FROZEN,CANDIDATES)+tuple(p.ROOT/s for s in SOURCES))
    rows=json.loads((PROFILE/'basins.json').read_text());cfg=json.loads((CANDIDATES/'protocol.json').read_text())['settings']
    sealed=p.ROOT/'research_docs/consistency_backfill_v94_v95_sealed_preregistration.md'
    for folder in (PROFILE,BACKFILL):
        assert json.loads((folder/'protocol.json').read_text())['preregistration_sha256']==p.digest(sealed)
    proposals=json.loads((CANDIDATES/'candidates.json').read_text())
    supplement=[];maximum=0.;points=0;window_points=0
    window_rows=list(csv.DictReader((PROFILE/'windows.csv').open()))
    for ident in sorted({r['id'] for r in rows}):
        with np.load(PROFILE/'profiles'/(ident+'.npz')) as z:g={k:z[k] for k in z.files}
        with np.load(BASINS/'grids'/(ident+'.npz')) as z:
            for key in z.files:assert np.array_equal(z[key],g[key],equal_nan=True)
        with np.load(SIGNALS/'signals'/(ident+'.npz')) as z:s={k:z[k] for k in z.files}
        with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:f={k:z[k] for k in ('native_c3d_time_s','imu_valid','reference_valid')}
        computed=[]
        for mode in MODES:
            values=[]
            for li,lag in enumerate(g['lags']):
                x,_=interpolate(s['rt']+lag,s['t'],s[mode+'_a'],s['imu_valid'])
                value=corr(x,s[mode+'_b'],g[mode+'_mask']);saved=g[mode+'_correlations'][li]
                assert np.isnan(value)==np.isnan(saved)
                if np.isfinite(value):maximum=max(maximum,abs(value-saved));assert abs(value-saved)<1e-12
                values.append(value);points+=1
                for wi,start in enumerate(g['window_starts_s']):
                    mask=g[mode+'_mask']&(s['rt']>=start)&(s['rt']<start+8)
                    v=corr(x,s[mode+'_b'],mask);old=g[mode+'_window_correlations'][wi,li]
                    assert np.isnan(v)==np.isnan(old)
                    if np.isfinite(v):maximum=max(maximum,abs(v-old));assert abs(v-old)<1e-12
                    window_points+=1
            computed.append(values)
        scores=np.array(computed).T;lag=g['lags']
        for r in [q for q in rows if q['id']==ident]:
            ix=np.flatnonzero((lag>=r['lower_s'])&(lag<=r['upper_s']))
            raw=[]
            for i in ix:
                if not np.isfinite(scores[i]).all():continue
                dominating=[j for j in ix if np.isfinite(scores[j]).all() and
                    scores[j,0]>=scores[i,0] and scores[j,1]>=scores[i,1] and
                    (scores[j,0]>scores[i,0] or scores[j,1]>scores[i,1])]
                if not dominating:
                    raw.append(dict(offset_s=float(lag[i]),yaw_correlation=float(scores[i,0]),speed_correlation=float(scores[i,1]),
                        yaw_events=int(g['signed_yaw_matches'][i]),speed_events=int(g['speed_matches'][i]),
                        both_event_gate=bool(g['signed_yaw_matches'][i]>=cfg['min_peak_matches'] and g['speed_matches'][i]>=cfg['min_peak_matches']),
                        both_correlation_gate=bool((scores[i]>=cfg['min_sync_corr']).all())))
            support=[]
            for mi,mode in enumerate(MODES):
                opt=r['channel_optima'][mode]
                if opt is None:assert not np.isfinite(scores[ix,mi]).any();continue
                i=int(ix[np.nanargmax(scores[ix,mi])]);assert opt['offset_s']==lag[i]
                assert opt['matched_events']==int(g[mode+'_matches'][i])==len(opt['events'])
                motion=next(q['motion_eligible'] for q in proposals if q['id']==ident and q['channel']==mode)
                assert opt['passes_own_event_motion_gate']==bool(motion and g[mode+'_matches'][i]>=cfg['min_peak_matches'])
                for e in opt['events']:
                    assert abs(e['residual_s']-(s['t'][e['imu_index']]-s['rt'][e['reference_index']]-lag[i]))<1e-12
                _,ok=interpolate(f['native_c3d_time_s']+lag[i],s['t'],s['signed_yaw_a'],s['imu_valid'])
                support.append(dict(channel=mode,offset_s=float(lag[i]),imu_lost=int((f['imu_valid']&~ok).sum()),
                    scored_lost=int((f['imu_valid']&f['reference_valid']&~ok).sum())))
            both=np.ones(len(ix),bool)
            for mi,mode in enumerate(MODES):
                motion=next(q['motion_eligible'] for q in proposals if q['id']==ident and q['channel']==mode)
                both &= motion & (g[mode+'_matches'][ix]>=cfg['min_peak_matches']) & np.isfinite(scores[ix,mi]) & (scores[ix,mi]>=cfg['min_sync_corr'])
            # All joint ranges are empty; certify that from independent scores, not JSON alone.
            assert not both.any() and r['both_gate_ranges']==[]
            for w in [w for w in window_rows if w['id']==ident and int(w['basin'])==r['basin']]:
                mode=w['channel'];wi=int(np.flatnonzero(g['window_starts_s']==float(w['start_s']))[0])
                ai=int(np.flatnonzero(lag==r['channel_optima']['signed_yaw']['offset_s'])[0])
                bi=int(np.flatnonzero(lag==r['channel_optima']['speed']['offset_s'])[0])
                a,b=g[mode+'_window_correlations'][wi,[ai,bi]]
                assert abs(a-float(w['yaw_optimum_correlation']))<1e-12 and abs(b-float(w['speed_optimum_correlation']))<1e-12
                assert abs(b-a-float(w['delta_speed_minus_yaw']))<1e-12
            supplement.append(dict(id=ident,basin=r['basin'],raw_pareto=raw,raw_optimum_support=support,
                v94_pareto_definition='event/motion-gated',joint_gate_is_new_policy=False))
        print('v96 profiles checked',ident,flush=True)
    metrics=json.loads((BACKFILL/'trial_metrics.json').read_text());inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    manifest=json.loads((BACKFILL/'artifact_manifest.json').read_text())
    assert manifest['metric_code_sha256']==p.digest(p.ROOT/'metric_contract_v74.py')
    checkpoint=json.loads((BACKFILL/'checkpoint.json').read_text())
    assert checkpoint['source_sha256']==p.digest(p.ROOT/'failed_metrics_v95.py')
    final={(r['model'],r['recording_id']):r for r in metrics}
    for r in checkpoint['rows']:assert r==final[(r['model'],r['recording_id'])]
    directmax=0.;checked=0
    for source in SOURCES:
        for file in sorted((p.ROOT/source/'trajectories').glob('*.npz')):
            ident=file.stem.rsplit('__',1)[0] if 'v60' in source else file.stem
            assert inv[ident]['partition']=='train'
            with np.load(file) as z:
                ref=z['reference_xy'];mask=z['valid'] if 'valid' in z.files else z['reference_valid']
                names=['baseline'] if 'xy' in z.files else [k[:-3] for k in z.files if k.endswith('_xy') and k!='reference_xy']
                for name in names:
                    xy=z['xy'] if 'xy' in z.files else z[name+'_xy'];good=mask&np.isfinite(xy).all(1)
                    diff=xy[good]-ref[good];ate=float(np.sqrt(sum(np.dot(v,v) for v in diff)/len(diff)))
                    r=next(r for r in metrics if r['source']==source and r['recording_id']==ident and r['model']==source+'/'+name)
                    directmax=max(directmax,abs(ate-r['ATE_RMSE_m']));assert abs(ate-r['ATE_RMSE_m'])<1e-12
                    assert r['Valid_Frame_Count']==int(good.sum()) and r['Endpoint_Error_mm'] is None
                    if 'motion' not in z.files:assert r['Speed_RMSE_mps'] is None and r['Angular_Velocity_RMSE_degps'] is None
                    checked+=1
    summary=list(csv.DictReader((BACKFILL/'summary.csv').open()))
    for r in summary:
        selected=[m for m in metrics if m['model']==r['model']];people=sorted({m['participant_id'] for m in selected})
        value=sum(sum(m['ATE_RMSE_mm'] for m in selected if m['participant_id']==person)/sum(m['participant_id']==person for m in selected) for person in people)/len(people)
        assert abs(value-float(r['ATE_RMSE_mm']))<1e-9
        assert len(selected)==207 and len(people)==12
    assert checked==len(metrics)==2898 and len(summary)==14
    availability=json.loads((BACKFILL/'availability.json').read_text())
    for r in availability:
        if 'v63' in r['source']:
            historical=list(csv.DictReader((p.ROOT/r['source']/'trials.csv').open()))
            r.update(historical_model_trials=len(historical),missing_prediction_trials=len(historical),
                missing_models=sorted({q['method'] for q in historical}),reason='Historical diagnostic predictions were not saved; no regeneration')
        if 'v61' in r['source']:
            run=json.loads((p.ROOT/r['source']/'run.json').read_text())
            assert run['trajectory_changed'] is False
            r.update(reason='Uncertainty-only diagnostic; no new trajectory candidates to backfill',trajectory_backfill_applicable=False)
    OUT.mkdir(exist_ok=False)
    p.save_json(OUT/'raw_pareto_support.json',supplement)
    p.save_json(OUT/'availability_corrected.json',availability)
    p.save_json(OUT/'verification_sources.json',{name:p.digest(p.ROOT/name) for name in
        ('clock_consistency_v94.py','failed_metrics_v95.py','metric_contract_v74.py','backfill_metric_contract_v75.py',
         'outputs_amended_v2/inventory.json','research_docs/consistency_backfill_v94_v96.md')})
    p.save_json(OUT/'run.json',dict(parent_hashes_verified=hashes,grid_points=points,window_points=window_points,
        maximum_correlation_difference=maximum,independent_ATE_checks=checked,maximum_ATE_difference_m=directmax,participant_aggregates=14,
        window_contrast_rows=len(window_rows),
        clocks_accepted_unchanged=199,clocks_rejected_unchanged=8,promotion=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},
        source_sha256=p.digest(__file__),preregistration_sha256=p.digest(DOC)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
