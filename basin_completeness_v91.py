"""Prespecified local basin diagnostic; no clock acceptance or widening."""
import json
import numpy as np
import pipeline as p
from audit_fold_routes_v59 import verified_json
from distributed_clock_candidates_v86 import OUT as CANDIDATES, correlation
from distributed_clock_evidence_v87 import OUT as SIGNALS
from native_refit_v81 import OUT as FROZEN

OUT=p.ROOT/'outputs_basin_completeness_v91'
DOC=p.ROOT/'research_docs/basin_geometry_v91_v93.md'


def verify(folder):
    manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
    for name,sha in manifest.items():assert p.digest(folder/name)==sha,(folder,name)
    return len(manifest)


def grid(center,radius,limit):
    ticks=np.arange(round(center*1000)-round(radius*1000),round(center*1000)+round(radius*1000)+1)
    return ticks[np.abs(ticks)<=round(limit*1000)]/1000.


def identities(t,rt,pi,pg,lag,tolerance):
    i=j=0;out=[]
    while i<len(pi) and j<len(pg):
        delta=float(t[pi[i]]-rt[pg[j]]-lag)
        if abs(delta)<=tolerance:
            out.append(dict(imu_index=int(pi[i]),reference_index=int(pg[j]),residual_s=delta));i+=1;j+=1
        elif delta<0:i+=1
        else:j+=1
    return out


def check():
    assert np.array_equal(grid(4.9,.2,5),np.arange(4700,5001)/1000)
    assert len(grid(-.8,.2,5))==401
    t=np.array([1.,2.,3.]);pi=np.arange(3)
    assert len(identities(t,t-.7,pi,pi,.7,.2))==3
    assert not identities(t,t+10,pi,pi,0,.2)


def main():
    check();hashes=sum(verify(q) for q in (CANDIDATES,SIGNALS,FROZEN))
    cfg=verified_json(CANDIDATES,'protocol.json')['settings']
    proposals=verified_json(CANDIDATES,'candidates.json')
    OUT.mkdir(exist_ok=False);(OUT/'grids').mkdir()
    p.save_json(OUT/'protocol.json',dict(preregistration_sha256=p.digest(DOC),radius_s=cfg['peak_tolerance_s'],step_s=.001,
        support='case/channel union of all prescribed grids',parent_hashes_verified=hashes))
    rows=[];overlaps=[];scores=[]
    for ident in sorted({q['id'] for q in proposals if q['candidates']}):
        groups=[q for q in proposals if q['id']==ident]
        basins=[(q,c) for q in groups for c in q['candidates']]
        grids=[grid(c['coarse_offset_s'],cfg['peak_tolerance_s'],cfg['max_lag_s']) for q,c in basins]
        union=np.unique(np.concatenate(grids))
        with np.load(SIGNALS/'signals'/(ident+'.npz')) as z:s={k:z[k] for k in z.files}
        with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:f={k:z[k] for k in ('native_c3d_time_s','imu_valid','reference_valid')}
        common={};cs={};counts={}
        for mode in ('signed_yaw','speed'):
            mask=s[mode+'_bm'].copy()
            for lag in union:
                _,ok=p.masked_interp(s['rt']+lag,s['t'],s[mode+'_a'],s['imu_valid']);mask &=ok
            common[mode]=mask;values=[];matches=[]
            for lag in union:
                x,_=p.masked_interp(s['rt']+lag,s['t'],s[mode+'_a'],s['imu_valid'])
                values.append(correlation(x,s[mode+'_b'],mask))
                pg=s[mode+'_pg'];pg=pg[mask[pg]];pi=s[mode+'_pi'];query=s['t'][pi]-lag
                ix=np.searchsorted(s['rt'],query).clip(0,len(s['rt'])-1)
                pi=pi[(query>=s['rt'][0])&(query<=s['rt'][-1])&mask[ix]]
                matches.append(len(identities(s['t'],s['rt'],pi,pg,lag,cfg['peak_tolerance_s'])))
            cs[mode]=np.array([np.nan if c is None else c for c in values]);counts[mode]=np.array(matches)
        np.savez_compressed(OUT/'grids'/(ident+'.npz'),lags=union,**{m+'_mask':common[m] for m in common},
            **{m+'_correlations':cs[m] for m in cs},**{m+'_matches':counts[m] for m in counts})
        for number,((q,c),g) in enumerate(zip(basins,grids)):
            mode=q['channel'];ix=np.searchsorted(union,g)
            eligible=np.isfinite(cs[mode][ix])&(counts[mode][ix]>=cfg['min_peak_matches'])&q['motion_eligible']
            best=int(ix[np.argmax(np.where(eligible,cs[mode][ix],-np.inf))]) if eligible.any() else None
            lag=float(union[best]) if best is not None else None
            row=dict(id=ident,basin=number,channel=mode,coarse_offset_s=c['coarse_offset_s'],old_offset_s=c['offset_s'],
                lower_s=float(g[0]),upper_s=float(g[-1]),grid_points=len(g),common_frames=int(common[mode].sum()),
                eligible_grid_points=int(eligible.sum()),offset_s=lag,correlation=float(cs[mode][best]) if best is not None else None,
                boundary=bool(best is not None and (lag==g[0] or lag==g[-1])),motion_eligible=q['motion_eligible'])
            if best is not None:
                pg=s[mode+'_pg'];pg=pg[common[mode][pg]];pi=s[mode+'_pi'];query=s['t'][pi]-lag
                j=np.searchsorted(s['rt'],query).clip(0,len(s['rt'])-1)
                pi=pi[(query>=s['rt'][0])&(query<=s['rt'][-1])&common[mode][j]]
                row['events']=identities(s['t'],s['rt'],pi,pg,lag,cfg['peak_tolerance_s'])
                row['passes_correlation_gate']=row['correlation']>=cfg['min_sync_corr']
                row['other_channel_correlation']=float(cs['speed' if mode=='signed_yaw' else 'signed_yaw'][best])
                _,ok=p.masked_interp(f['native_c3d_time_s']+lag,s['t'],s['signed_yaw_a'],s['imu_valid'])
                row['frozen_imu_lost']=int((f['imu_valid']&~ok).sum())
                row['frozen_scored_lost']=int((f['imu_valid']&f['reference_valid']&~ok).sum())
            rows.append(row)
            for earlier,h in enumerate(grids[:number]):
                if max(g[0],h[0])<=min(g[-1],h[-1]):overlaps.append(dict(id=ident,a=earlier,b=number))
        print('v91',ident,'basins',len(basins),flush=True)
    assert len(rows)==12
    p.save_json(OUT/'basins.json',rows);p.save_json(OUT/'overlaps.json',overlaps)
    p.write_csv(OUT/'basins.csv',[{k:v for k,v in r.items() if k!='events'} for r in rows])
    p.save_json(OUT/'run.json',dict(basins=len(rows),interior=sum(r['offset_s'] is not None and not r['boundary'] for r in rows),
        boundary=sum(r['boundary'] for r in rows),no_eligible_optimum=sum(r['offset_s'] is None for r in rows),overlaps=len(overlaps),
        all_207_clock_gate=False,accepted_clocks_unchanged=199,rejected_clocks_unchanged=8,promotion=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
