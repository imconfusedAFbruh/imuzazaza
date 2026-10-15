"""Frozen-event lag feasibility and optical-run accounting; no clock selection."""
import json
import numpy as np
import pipeline as p
from audit_fold_routes_v59 import verified_json
from distributed_clock_candidates_v86 import OUT as CANDIDATES
from distributed_clock_evidence_v87 import OUT as EVIDENCE
from seedless_clock_v83 import OUT as REFERENCE

OUT=p.ROOT/'outputs_clock_observability_v89'


def probes(a,b,bound,tolerance):
    edges=(a[:,None]-b[None,:]).ravel()
    points=np.unique(np.r_[-bound,bound,edges-tolerance,edges+tolerance])
    points=points[(points>=-bound)&(points<=bound)]
    return np.unique(np.r_[points,(points[:-1]+points[1:])/2])


def feasible(a,b,bound,tolerance):
    if not len(a) or not len(b):return 0
    # Include closed boundaries robustly against subtraction roundoff.
    return max(len(p.match_peaks(a,b+lag,tolerance+1e-12)) for lag in probes(a,b,bound,tolerance))


def accounting(mask):
    lengths=[int(b-a) for a,b in p.runs(mask)]
    return dict(runs=len(lengths),frames=int(mask.sum()),
                short_run_frames=sum(n for n in lengths if n<20),
                longest_run_frames=max(lengths,default=0))


def check():
    assert feasible(np.array([1.,3.]),np.array([0.,2.]),5.,.2)==2
    assert feasible(np.array([1.,4.]),np.array([0.,1.]),5.,.2)==1
    assert feasible(np.array([]),np.array([1.]),5.,.2)==0
    assert feasible(np.array([5.2]),np.array([0.]),5.,.2)==1
    assert accounting(np.r_[np.ones(19,bool),False,np.ones(20,bool)])==dict(runs=2,frames=39,short_run_frames=19,longest_run_frames=20)
    json.dumps(accounting(np.r_[np.ones(19,bool),False,np.ones(20,bool)]))


def main():
    check();hashes=0
    for folder in (CANDIDATES,EVIDENCE,REFERENCE):
        for rel,sha in json.loads((folder/'artifact_manifest.json').read_text())['sha256'].items():
            assert p.digest(folder/rel)==sha;hashes+=1
    cfg=verified_json(CANDIDATES,'protocol.json')['settings']
    candidates=verified_json(CANDIDATES,'candidates.json');rows=[];runs=[]
    for q in candidates:
        ident=q['id'];mode=q['channel']
        with np.load(EVIDENCE/'signals'/(ident+'.npz')) as z:
            pg=z[mode+'_pg'];a=z['t'][z[mode+'_pi']];b=z['rt'][pg];feature=z[mode+'_bm']
        with np.load(REFERENCE/'references'/(ident+'.npz')) as z:
            ref=z['yaw'] if mode=='signed_yaw' else np.abs(z['speed'])
            mask=z['derivative_valid']&np.isfinite(ref)
        source=accounting(mask);filtered=accounting(feature)
        assert filtered['frames']==source['frames']-source['short_run_frames']
        assert len(a)==q['imu_peaks'] and len(b)==q['reference_peaks']
        maximum=feasible(a,b,cfg['max_lag_s'],cfg['peak_tolerance_s'])
        reason=('insufficient_motion' if not q['motion_eligible'] else
                'too_few_peaks' if min(len(a),len(b))<cfg['min_peak_matches'] else
                'incompatible_event_timing' if maximum<cfg['min_peak_matches'] else
                'events_feasible_candidates_present' if q['candidates'] else
                'events_feasible_coarse_search_empty')
        rows.append(dict(id=ident,participant=q['participant'],condition=q['condition'],channel=mode,
                         motion_eligible=q['motion_eligible'],reference_spread=q['reference_spread'],
                         imu_peaks=len(a),reference_peaks=len(b),maximum_matches=maximum,
                         derivative_frames=source['frames'],short_run_frames=source['short_run_frames'],
                         feature_frames=filtered['frames'],observed_runs=filtered['runs'],
                         longest_observed_run_s=filtered['longest_run_frames']/cfg['hz'],diagnosis=reason))
        for start,end in p.runs(feature):
            runs.append(dict(id=ident,channel=mode,start_frame=start,end_frame_exclusive=end,frames=end-start,
                             peaks=int(((pg>=start)&(pg<end)).sum())))
    assert len(rows)==20 and len({q['id'] for q in rows})==10
    OUT.mkdir(exist_ok=False);p.write_csv(OUT/'channels.csv',rows);p.write_csv(OUT/'observed_runs.csv',runs)
    p.save_json(OUT/'run.json',dict(parent_hashes_verified=hashes,channels=20,cases=10,trials_preserved=207,
        diagnoses={reason:sum(q['diagnosis']==reason for q in rows) for reason in sorted({q['diagnosis'] for q in rows})},
        short_run_frames=sum(q['short_run_frames'] for q in rows),
        event_definition='existing peaks; exact feasible matching counts, not lag selection',
        preregistration_sha256=p.digest(p.ROOT/'research_docs/clock_observability_v89_v90.md'),
        promotion=False,validation_accessed=False,test_accessed=False,trajectory_metrics='unavailable: no predictions'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
