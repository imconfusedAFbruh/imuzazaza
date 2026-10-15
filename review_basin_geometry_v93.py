"""Same-context numerical review using independent brackets/dot correlations."""
import csv,json
import numpy as np
import pipeline as p
from basin_completeness_v91 import OUT as BASINS,CANDIDATES,SIGNALS,FROZEN,verify,DOC
from geometry_roles_v92 import OUT as ROLES,GEOMETRY,REFERENCES

OUT=p.ROOT/'outputs_basin_geometry_review_v93'


def interpolate(query,t,a,valid):
    right=np.searchsorted(t,query).clip(1,len(t)-1);left=right-1
    ok=valid[left]&valid[right]&(query>=t[0])&(query<=t[-1])&((t[right]-t[left])<=1.5*np.median(np.diff(t)))
    fraction=(query-t[left])/(t[right]-t[left])
    clean=np.nan_to_num(a);x=clean[left]+fraction*(clean[right]-clean[left]);x[~ok]=np.nan
    return x,ok


def corr(a,b,mask):
    good=mask&np.isfinite(a)&np.isfinite(b)
    if good.sum()<60:return np.nan
    x=a[good];y=b[good]
    if min(x.std(),y.std())<=.04:return np.nan
    x=x-x.mean();y=y-y.mean()
    return float(np.dot(x,y)/np.sqrt(np.dot(x,x)*np.dot(y,y)))


def check():
    t=np.arange(100)/10;valid=np.ones(100,bool);valid[30]=False
    x,ok=interpolate(t,t,t,valid);assert not ok[30:32].any() and np.allclose(x[ok],t[ok])
    _,ok=interpolate(np.array([-1.,10.]),t,t,valid);assert not ok.any()
    assert abs(corr(t,t,np.ones(100,bool))-1)<1e-15
    assert np.isnan(corr(t,t,np.zeros(100,bool)))


def main():
    check();folders=(BASINS,ROLES,CANDIDATES,SIGNALS,FROZEN,GEOMETRY,REFERENCES)
    hashes=sum(verify(q) for q in folders)
    cfg=json.loads((CANDIDATES/'protocol.json').read_text())['settings']
    rows=json.loads((BASINS/'basins.json').read_text());maximum=0.;points=0;event_checks=0
    for ident in sorted({r['id'] for r in rows}):
        with np.load(SIGNALS/'signals'/(ident+'.npz')) as z:s={k:z[k] for k in z.files}
        with np.load(BASINS/'grids'/(ident+'.npz')) as z:g={k:z[k] for k in z.files}
        with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:f={k:z[k] for k in ('native_c3d_time_s','imu_valid','reference_valid')}
        for mode in ('signed_yaw','speed'):
            common=s[mode+'_bm'].copy()
            for lag in g['lags']:
                _,ok=interpolate(s['rt']+lag,s['t'],s[mode+'_a'],s['imu_valid']);common &=ok
            assert np.array_equal(common,g[mode+'_mask'])
            computed=[]
            for index,lag in enumerate(g['lags']):
                x,_=interpolate(s['rt']+lag,s['t'],s[mode+'_a'],s['imu_valid']);value=corr(x,s[mode+'_b'],common)
                saved=g[mode+'_correlations'][index]
                assert np.isnan(value)==np.isnan(saved)
                if np.isfinite(value):maximum=max(maximum,abs(value-saved));assert abs(value-saved)<1e-12
                computed.append(value);points+=1
                pg=s[mode+'_pg'];pg=pg[common[pg]];pi=s[mode+'_pi'];query=s['t'][pi]-lag
                ix=np.searchsorted(s['rt'],query).clip(0,len(s['rt'])-1)
                pi=pi[(query>=s['rt'][0])&(query<=s['rt'][-1])&common[ix]]
                assert len(p.match_peaks(s['t'][pi],s['rt'][pg]+lag,cfg['peak_tolerance_s']))==g[mode+'_matches'][index]
                event_checks+=1
            computed=np.array(computed)
            for r in [q for q in rows if q['id']==ident and q['channel']==mode]:
                expected=np.arange(round((r['coarse_offset_s']-cfg['peak_tolerance_s'])*1000),round((r['coarse_offset_s']+cfg['peak_tolerance_s'])*1000)+1)/1000
                expected=expected[np.abs(expected)<=cfg['max_lag_s']]
                assert r['lower_s']==expected[0] and r['upper_s']==expected[-1] and r['grid_points']==len(expected)
                ix=np.searchsorted(g['lags'],expected);assert np.array_equal(g['lags'][ix],expected)
                eligible=np.isfinite(computed[ix])&(g[mode+'_matches'][ix]>=cfg['min_peak_matches'])&r['motion_eligible']
                assert int(eligible.sum())==r['eligible_grid_points']
                if not eligible.any():assert r['offset_s'] is None;continue
                best=ix[np.argmax(np.where(eligible,computed[ix],-np.inf))]
                assert r['offset_s']==g['lags'][best]
                assert r['boundary']==(best==ix[0] or best==ix[-1])
                assert abs(r['correlation']-computed[best])<1e-12
                assert r['passes_correlation_gate']==(computed[best]>=cfg['min_sync_corr'])
                events=r['events'];assert len(events)==g[mode+'_matches'][best]
                assert len({e['imu_index'] for e in events})==len({e['reference_index'] for e in events})==len(events)
                for e in events:
                    assert abs(e['residual_s']-(s['t'][e['imu_index']]-s['rt'][e['reference_index']]-r['offset_s']))<1e-12
                    assert abs(e['residual_s'])<=cfg['peak_tolerance_s']
                _,ok=interpolate(f['native_c3d_time_s']+r['offset_s'],s['t'],s[mode+'_a'],s['imu_valid'])
                assert r['frozen_imu_lost']==int((f['imu_valid']&~ok).sum())
                assert r['frozen_scored_lost']==int((f['imu_valid']&f['reference_valid']&~ok).sum())
        print('v93 grids exact',ident,flush=True)
    overlaps=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            if a['id']==b['id'] and max(a['lower_s'],b['lower_s'])<=min(a['upper_s'],b['upper_s']):
                overlaps.append(dict(id=a['id'],a=a['basin'],b=b['basin']))
    assert overlaps==json.loads((BASINS/'overlaps.json').read_text())
    contract=json.loads((ROLES/'contract.json').read_text());roles=list(csv.DictReader((ROLES/'roles.csv').open()))
    original={r['id']:r for r in csv.DictReader((GEOMETRY/'support.csv').open())}
    assert len(roles)==207 and sum(r['participant']=='No.20' for r in roles)==15
    total=0
    for r in roles:
        ident=r['id'];q=contract['folds'][r['fold']]
        assert ident in q['held_ids'] and ident not in q['fit_ids']
        assert r['scoring_retained']==r['reference_arrays_exact']==r['initial_pose_exact']=='True'
        assert r['hypothetical_geometry_lost_frames']==original[ident]['lost_frames']
        with np.load(REFERENCES/'references'/(ident+'.npz')) as a,np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as b:
            # Exact-grid dictionary lookup is independent of the v92 searchsorted projection.
            lookup={float(t):i for i,t in enumerate(a['t'])};ix=np.array([lookup[float(t)] for t in b['native_c3d_time_s']])
            for key,other in [('xy','reference_xy_m'),('heading','reference_heading_rad'),('valid','reference_valid')]:
                assert np.array_equal(a[key][ix],b[other],equal_nan=True)
            n=int(np.count_nonzero(b['imu_valid']&b['reference_valid']));assert n==int(r['native_scoring_frames']);total+=n
    assert total==318034 and sum(int(r['hypothetical_geometry_lost_frames']) for r in roles)==27580
    OUT.mkdir(exist_ok=False)
    result=dict(parent_hashes_verified=hashes,grid_channel_points=points,event_count_checks=event_checks,
        maximum_correlation_difference=maximum,basin_optima_checked=12,reference_role_checks=207,no20_preserved=15,
        scored_frames=total,review='Same-context independent arithmetic, not separate-agent timing review',
        clocks_accepted=199,clocks_rejected=8,fully_nested=False,promotion=False,validation_accessed=False,test_accessed=False)
    p.save_json(OUT/'run.json',result)
    sources=['basin_completeness_v91.py','geometry_roles_v92.py','review_basin_geometry_v93.py','pipeline.py',
        'distributed_clock_candidates_v86.py','distributed_clock_evidence_v87.py','audit_fold_routes_v59.py']
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={'run.json':p.digest(OUT/'run.json')},source_sha256={f:p.digest(p.ROOT/f) for f in sources},preregistration_sha256=p.digest(DOC)))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
