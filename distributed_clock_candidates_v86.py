"""Fresh-fold signal/event candidate basins; diagnostics, never clock promotion."""
import csv,json
import numpy as np
from scipy import signal
import pipeline as p
from observed_sync_experiment import observed_feature,segment_peaks
from audit_fold_routes_v59 import verified_json
from seedless_clock_v83 import OUT as SEEDS
from fold_seedless_clock_v84 import OUT as CLOCKS
from native_projection_v80 import OUT as SENSOR

OUT=p.ROOT/'outputs_distributed_clock_candidates_v86'


def correlation(a,b,mask):
    good=mask & np.isfinite(a) & np.isfinite(b)
    if good.sum()<60 or min(np.std(a[good]),np.std(b[good]))<=.04:return None
    return float(np.corrcoef(a[good],b[good])[0,1])


def channels(full,gt,terms,cfg):
    wheels=[full['raw'][:,q['column']]*q['scale']+q['intercept'] for q in terms[:2]]
    q=terms[2]
    for mode,imu,ref in [('signed_yaw',full['raw'][:,q['column']]*q['scale']+q['intercept'],gt['yaw']),
                         ('speed',np.abs((wheels[0]+wheels[1])/2),np.abs(gt['speed']))]:
        mask=gt['derivative_valid'] & np.isfinite(ref)
        spread=float(np.std(ref[mask])) if mask.any() else 0.
        a=p.smooth_standard(imu,cfg['hz']);b,bm=observed_feature(ref,mask,float(gt['hz']))
        ap,bp=(np.abs(a),np.abs(b)) if mode=='signed_yaw' else (a,b)
        pi=segment_peaks(ap,full['imu_valid'],cfg['hz'],cfg)
        pg=segment_peaks(bp,bm,float(gt['hz']),cfg)
        yield mode,a,b,bm,pi,pg,dict(channel=mode,reference_spread=spread,
            observed_feature_frames=int(bm.sum()),imu_peaks=len(pi),reference_peaks=len(pg),
            motion_eligible=int(mask.sum())>=100 and spread>=(.025 if mode=='signed_yaw' else .03))


def discover(t,a,iv,rt,b,bm,pi,pg,cfg):
    if min(len(pi),len(pg))<cfg['min_peak_matches']:return []
    pi=pi[np.argsort(np.abs(a[pi]))[-100:]];pg=pg[np.argsort(np.abs(b[pg]))[-100:]]
    offsets=(t[pi,None]-rt[pg][None,:]).ravel()
    bins=np.unique(np.round(offsets[np.abs(offsets)<=cfg['max_lag_s']]/.025)*.025)
    scored=[]
    for lag in bins:
        x,ok=p.masked_interp(rt+lag,t,a,iv);c=correlation(x,b,bm&ok)
        matches=p.match_peaks(t[pi],rt[pg]+lag,cfg['peak_tolerance_s'])
        if c is not None and len(matches)>=cfg['min_peak_matches']:
            scored.append(dict(coarse_offset_s=float(lag),coarse_correlation=c,coarse_frames=int((bm&ok).sum()),matched_peaks=len(matches)))
    selected=[]
    for q in sorted(scored,key=lambda r:r['coarse_correlation'],reverse=True):
        if any(abs(q['coarse_offset_s']-r['coarse_offset_s'])<=.5 for r in selected):continue
        lag=q['coarse_offset_s'];grid=np.arange(-25,26)*.001+lag
        grid=grid[np.abs(grid)<=cfg['max_lag_s']];common=bm.copy()
        for candidate in grid:
            _,ok=p.masked_interp(rt+candidate,t,a,iv);common &=ok
        values=[]
        for candidate in grid:
            x,_=p.masked_interp(rt+candidate,t,a,iv);c=correlation(x,b,common)
            matches=p.match_peaks(t[pi],rt[pg]+candidate,cfg['peak_tolerance_s'])
            if c is not None and len(matches)>=cfg['min_peak_matches']:values.append((c,float(candidate)))
        best=max(values) if values else (q['coarse_correlation'],lag)
        selected.append(dict(q,offset_s=best[1],local_correlation=best[0],local_common_frames=int(common.sum()),
            local_refined=bool(values),passes_existing_correlation_gate=best[0]>=cfg['min_sync_corr']))
        if len(selected)==3:break
    return selected


def load_inputs():
    folders=(SEEDS,CLOCKS,SENSOR);manifests={};count=0
    for folder in folders:
        manifests[folder]=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
        for name,sha in manifests[folder].items():assert p.digest(folder/name)==sha;count+=1
    seeds=verified_json(SEEDS,'seeds.json');clocks=verified_json(CLOCKS,'clocks.json');models=verified_json(CLOCKS,'models.json')
    cfg=verified_json(SEEDS,'protocol.json')['settings']
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    for model in models.values():
        assert not set(model['fit_ids'])&set(model['held_ids'])
        assert not {inv[i]['participant'] for i in model['fit_ids']}&{inv[i]['participant'] for i in model['held_ids']}
    assert len(seeds)==len(clocks)==207 and {r['id'] for r in seeds}=={r['id'] for r in clocks}
    return cfg,inv,clocks,models,count


def arrays(ident):
    with np.load(SENSOR/'sensors'/(ident+'.npz')) as z:full={k:z[k] for k in ('t','raw','imu_valid')}
    with np.load(SEEDS/'references'/(ident+'.npz')) as z:gt={k:z[k] for k in z.files}
    return full,gt


def check():
    t=np.arange(0,40,.01);lag=.7
    b=sum(s*np.exp(-((t-c)/.25)**2) for c,s in [(5,1),(11,-.8),(18,1.2),(26,-1),(34,.6)])
    a=np.interp(t-lag,t,b);mask=np.ones(len(t),bool)
    cfg=dict(min_peak_matches=2,max_lag_s=5.,peak_tolerance_s=.2,min_sync_corr=.6)
    pi=signal.find_peaks(abs(a),prominence=.3)[0];pg=signal.find_peaks(abs(b),prominence=.3)[0]
    found=discover(t,a,mask,t,b,mask,pi,pg,cfg)
    assert abs(found[0]['offset_s']-lag)<.002 and found[0]['local_correlation']>.99
    assert not discover(t,a,mask,t,b,mask,pi,pg[:1],cfg)
    invalid=mask.copy();invalid[100:150]=False
    _,ok=p.masked_interp(t,t,a,invalid);assert not ok[100:151].any()
    assert correlation(a,b,np.zeros(len(t),bool)) is None


def main():
    check();cfg,inv,clocks,models,hashes=load_inputs()
    comparison=verified_json(p.ROOT/'outputs_seedless_review_v85','run.json')
    path=p.ROOT/'outputs_seedless_review_v85/clock_comparison.csv'
    manifest=json.loads((path.parent/'artifact_manifest.json').read_text())['sha256'];assert p.digest(path)==manifest[path.name]
    cases={r['id'] for r in clocks if not r['accepted']}
    cases|={r['id'] for r in csv.DictReader(path.open()) if r['delta_vs_new_s'] and abs(float(r['delta_vs_new_s']))>.25}
    assert len(cases)==10
    OUT.mkdir(exist_ok=False)
    p.save_json(OUT/'protocol.json',dict(cases=sorted(cases),settings=cfg,parent_hashes_verified=hashes,
        preregistration_sha256=p.digest(p.ROOT/'research_docs/distributed_seedless_clock_v86_v88.md'),
        discovery='Fresh fold signal peak differences; no inherited candidate lags',validation_accessed=False,test_accessed=False))
    rows=[];inventory=[]
    for clock in clocks:
        ident=clock['id'];r=inv[ident];assert r['partition']=='train'
        inventory.append(dict(id=ident,participant=r['participant'],condition=r['condition'],held_clock_accepted=clock['accepted'],investigated=ident in cases))
        if ident not in cases:continue
        full,gt=arrays(ident);model=models[str(clock['fold'])]
        assert ident in model['held_ids'];terms=model['calibration'][r['setup']]['terms']
        for mode,a,b,bm,pi,pg,info in channels(full,gt,terms,cfg):
            candidates=discover(full['t'],a,full['imu_valid'],gt['t'],b,bm,pi,pg,cfg) if info['motion_eligible'] else []
            rows.append(dict(id=ident,participant=r['participant'],condition=r['condition'],fold=clock['fold'],**info,candidates=candidates,
                reason='candidates_only' if candidates else 'insufficient_motion' if not info['motion_eligible'] else 'insufficient_peaks' if min(len(pi),len(pg))<cfg['min_peak_matches'] else 'no_matched_finite_correlation'))
        print('v86',ident,[(q['channel'],len(q['candidates'])) for q in rows if q['id']==ident],flush=True)
    p.save_json(OUT/'candidates.json',rows);p.write_csv(OUT/'inventory.csv',inventory)
    p.write_csv(OUT/'channels.csv',[{k:v for k,v in q.items() if k!='candidates'} for q in rows])
    p.save_json(OUT/'run.json',dict(trials_preserved=207,cases=10,channels=len(rows),candidate_basins=sum(len(r['candidates']) for r in rows),
        cases_with_candidates=len({r['id'] for r in rows if r['candidates']}),promotion=False,
        trajectory_metrics='unavailable: no predictions',validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
