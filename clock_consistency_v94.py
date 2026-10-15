"""Whole sealed profiles; signal-objective ambiguity, never clock selection."""
import json
import numpy as np
import pipeline as p
from basin_completeness_v91 import OUT as BASINS, verify, identities
from distributed_clock_evidence_v87 import OUT as SIGNALS
from distributed_clock_candidates_v86 import OUT as CANDIDATES, correlation
from native_refit_v81 import OUT as FROZEN
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_clock_consistency_v94'
DOC=p.ROOT/'research_docs/consistency_backfill_v94_v96.md'
MODES=('signed_yaw','speed')


def pareto(scores):
    valid=np.isfinite(scores).all(1)
    return np.array([bool(valid[i] and not np.any(valid & np.all(scores>=q,axis=1) & np.any(scores>q,axis=1)))
                     for i,q in enumerate(scores)])


def passing_range(lags,mask):
    # Sealed union grids may have gaps; never describe those as tested intervals.
    indices=np.flatnonzero(mask)
    groups=np.split(indices,np.flatnonzero((np.diff(indices)>1)|(np.diff(lags[indices])>.00100001))+1)
    return [dict(lower_s=float(lags[g[0]]),upper_s=float(lags[g[-1]]),grid_points=len(g)) for g in groups if len(g)]


def events(s,mode,mask,lag,tolerance):
    pg=s[mode+'_pg'];pg=pg[mask[pg]]
    pi=s[mode+'_pi'];query=s['t'][pi]-lag
    j=np.searchsorted(s['rt'],query).clip(0,len(s['rt'])-1)
    pi=pi[(query>=s['rt'][0])&(query<=s['rt'][-1])&mask[j]]
    return identities(s['t'],s['rt'],pi,pg,lag,tolerance)


def main():
    hashes=sum(verify(q) for q in (BASINS,SIGNALS,CANDIDATES,FROZEN))
    cfg=verified_json(CANDIDATES,'protocol.json')['settings']
    proposals=verified_json(CANDIDATES,'candidates.json')
    rows=verified_json(BASINS,'basins.json')
    OUT.mkdir(exist_ok=False);(OUT/'profiles').mkdir()
    p.save_json(OUT/'protocol.json',dict(preregistration_sha256=p.digest(DOC),parent_hashes_verified=hashes,
        window_s=8,contrast=.025,intervals='exact sealed v91',clock_acceptance=False))
    results=[];windows=[]
    for ident in sorted({r['id'] for r in rows}):
        with np.load(BASINS/'grids'/(ident+'.npz')) as z:g={k:z[k] for k in z.files}
        with np.load(SIGNALS/'signals'/(ident+'.npz')) as z:s={k:z[k] for k in z.files}
        with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:f={k:z[k] for k in ('native_c3d_time_s','imu_valid','reference_valid')}
        lags=g['lags'];window_arrays={};starts=np.arange(0,s['rt'][-1],8.)
        sampled={m:np.array([p.masked_interp(s['rt']+lag,s['t'],s[m+'_a'],s['imu_valid'])[0] for lag in lags]) for m in MODES}
        for mode in MODES:
            matrix=np.full((len(starts),len(lags)),np.nan)
            for wi,start in enumerate(starts):
                mask=g[mode+'_mask']&(s['rt']>=start)&(s['rt']<start+8)
                for li,x in enumerate(sampled[mode]):
                    c=correlation(x,s[mode+'_b'],mask)
                    if c is not None:matrix[wi,li]=c
            window_arrays[mode]=matrix
        np.savez_compressed(OUT/'profiles'/(ident+'.npz'),**g,window_starts_s=starts,
            **{m+'_window_correlations':window_arrays[m] for m in MODES})
        eligible=[]
        for m in MODES:
            motion=next(q['motion_eligible'] for q in proposals if q['id']==ident and q['channel']==m)
            eligible.append(motion & np.isfinite(g[m+'_correlations']) & (g[m+'_matches']>=cfg['min_peak_matches']))
        scores=np.column_stack([g[m+'_correlations'] for m in MODES])
        for row in [r for r in rows if r['id']==ident]:
            ix=np.flatnonzero((lags>=row['lower_s'])&(lags<=row['upper_s']))
            opts={m:int(ix[np.nanargmax(scores[ix,mi])]) if np.isfinite(scores[ix,mi]).any() else None for mi,m in enumerate(MODES)}
            both=eligible[0][ix]&eligible[1][ix]&(scores[ix]>=cfg['min_sync_corr']).all(1)
            nondominated=pareto(np.where((eligible[0][ix]&eligible[1][ix])[:,None],scores[ix],np.nan))
            identity_sets={m:{tuple((e['imu_index'],e['reference_index']) for e in events(s,m,g[m+'_mask'],float(lags[i]),cfg['peak_tolerance_s'])) for i in ix} for m in MODES}
            losses=[]
            for i in ix[both]:
                _,ok=p.masked_interp(f['native_c3d_time_s']+lags[i],s['t'],s['signed_yaw_a'],s['imu_valid'])
                losses.append(dict(offset_s=float(lags[i]),imu_lost=int((f['imu_valid']&~ok).sum()),scored_lost=int((f['imu_valid']&f['reference_valid']&~ok).sum())))
            result=dict(id=ident,basin=row['basin'],lower_s=row['lower_s'],upper_s=row['upper_s'],
                channel_optima={m:dict(offset_s=float(lags[i]),yaw_correlation=float(scores[i,0]),speed_correlation=float(scores[i,1]),passes_own_event_motion_gate=bool(eligible[mi][i]),matched_events=int(g[m+'_matches'][i]),events=events(s,m,g[m+'_mask'],float(lags[i]),cfg['peak_tolerance_s'])) if i is not None else None for mi,(m,i) in enumerate(opts.items())},
                optimum_separation_ms=float(abs(lags[opts[MODES[0]]]-lags[opts[MODES[1]]])*1000) if all(i is not None for i in opts.values()) else None,
                both_gate_ranges=passing_range(lags[ix],both),pareto_offsets_s=lags[ix[nondominated]].tolist(),
                identity_variants={m:len(v) for m,v in identity_sets.items()},support_at_both_gate_points=losses,
                zero_support_loss_both_gate_points=sum(q['imu_lost']==q['scored_lost']==0 for q in losses))
            for mode in MODES:
                a,b=opts[MODES[0]],opts[MODES[1]]
                valid=np.isfinite(window_arrays[mode][:,a])&np.isfinite(window_arrays[mode][:,b]) if a is not None and b is not None else np.zeros(len(starts),bool)
                for wi in np.flatnonzero(valid):
                    ca,cb=window_arrays[mode][wi,a],window_arrays[mode][wi,b]
                    windows.append(dict(id=ident,basin=row['basin'],channel=mode,start_s=float(starts[wi]),yaw_optimum_correlation=float(ca),speed_optimum_correlation=float(cb),delta_speed_minus_yaw=float(cb-ca)))
            results.append(result)
        print('v94',ident,flush=True)
    assert len(results)==12
    p.save_json(OUT/'basins.json',results);p.write_csv(OUT/'windows.csv',windows)
    p.write_csv(OUT/'basins.csv',[{k:r[k] for k in ('id','basin','lower_s','upper_s','optimum_separation_ms','zero_support_loss_both_gate_points')} for r in results])
    p.save_json(OUT/'run.json',dict(basins=12,cases=3,window_comparisons=len(windows),both_gate_basins=sum(bool(r['both_gate_ranges']) for r in results),
        zero_support_loss_basins=sum(r['zero_support_loss_both_gate_points']>0 for r in results),accepted_clocks_unchanged=199,rejected_clocks_unchanged=8,
        all_207_clock_gate=False,promotion=False,validation_accessed=False,test_accessed=False,decision='diagnostic ambiguity ranges only; no clock truth or acceptance'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
