"""Independent bracket/covariance arithmetic for sealed distributed diagnostics."""
import csv,json
import numpy as np
import pipeline as p
from distributed_clock_candidates_v86 import OUT as CANDIDATES,check as candidate_check
from distributed_clock_evidence_v87 import OUT as EVIDENCE,check as contrast_check
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_distributed_clock_review_v88'


def independent_sample(query,t,a,valid):
    hi=np.searchsorted(t,query).clip(1,len(t)-1);lo=hi-1
    mask=(query>=t[0])&(query<=t[-1])&valid[hi]&valid[lo]&(t[hi]-t[lo]<=1.5*np.median(np.diff(t)))
    fraction=(query-t[lo])/(t[hi]-t[lo])
    return a[lo]+fraction*(a[hi]-a[lo]),mask


def independent_corr(a,b,mask):
    mask=mask&np.isfinite(a)&np.isfinite(b)
    if mask.sum()<60 or min(np.std(a[mask]),np.std(b[mask]))<=.04:return None
    x=a[mask]-a[mask].mean();y=b[mask]-b[mask].mean()
    return float(np.dot(x,y)/np.sqrt(np.dot(x,x)*np.dot(y,y)))


def main():
    candidate_check();contrast_check();hashes=0
    for name in ('outputs_seedless_clock_v83','outputs_fold_seedless_clock_v84','outputs_native_projection_v80','outputs_native_refit_v81',CANDIDATES.name,EVIDENCE.name):
        folder=p.ROOT/name
        for rel,sha in json.loads((folder/'artifact_manifest.json').read_text())['sha256'].items():assert p.digest(folder/rel)==sha;hashes+=1
    channelrows=list(csv.DictReader((EVIDENCE/'channels.csv').open()));windowrows=list(csv.DictReader((EVIDENCE/'windows.csv').open()));maximum=0.;checked=0
    signals={}
    for path in (EVIDENCE/'signals').glob('*.npz'):
        with np.load(path) as z:signals[path.stem]={k:z[k] for k in z.files}
    for row in channelrows:
        z=signals[row['id']];mode=row['channel'];la,lb=float(row['a_offset_s']),float(row['b_offset_s']);b=z[mode+'_b']
        a,ma=independent_sample(z['rt']+la,z['t'],z[mode+'_a'],z['imu_valid']);c,mc=independent_sample(z['rt']+lb,z['t'],z[mode+'_a'],z['imu_valid'])
        mask=z[mode+'_bm']&ma&mc;assert mask.sum()==int(row['common_frames'])
        for name,values in [('a',a),('b',c)]:
            score=independent_corr(values,b,mask);saved=row[name+'_correlation']
            assert (score is None)==(saved=='')
            if score is not None:maximum=max(maximum,abs(score-float(saved)));assert abs(score-float(saved))<1e-10
        expected=[]
        for start in np.arange(0,z['rt'][-1],8.):
            good=mask&(z['rt']>=start)&(z['rt']<start+8)
            cs=[independent_corr(x,b,good) for x in (a,c)]
            if all(s is not None for s in cs):expected.append((start,int(good.sum()),cs))
        saved=[q for q in windowrows if q['id']==row['id'] and q['channel']==mode and q['a_offset_s']==row['a_offset_s'] and q['b_offset_s']==row['b_offset_s']]
        assert len(saved)==len(expected)==int(row['windows'])
        for q,(start,frames,cs) in zip(saved,expected):
            assert start==float(q['start_s']) and frames==int(q['frames'])
            for name,score in zip(('a','b'),cs):maximum=max(maximum,abs(score-float(q[name+'_correlation'])));assert abs(score-float(q[name+'_correlation']))<1e-10
            checked+=1
    candidates=verified_json(CANDIDATES,'candidates.json');boundaries=[]
    for q in candidates:
        for candidate in q['candidates']:
            if abs(abs(candidate['offset_s']-candidate['coarse_offset_s'])-.025)<1e-9:
                boundaries.append(dict(id=q['id'],channel=q['channel'],offset_s=candidate['offset_s'],coarse_offset_s=candidate['coarse_offset_s']))
    assert len(channelrows)==60 and checked==276 and len(signals)==10
    OUT.mkdir(exist_ok=False);p.write_csv(OUT/'refinement_boundaries.csv',boundaries)
    p.save_json(OUT/'run.json',dict(parent_artifact_hashes_verified=hashes,independent_channel_checks=60,independent_window_checks=checked,
        maximum_correlation_difference=maximum,refinement_boundaries=len(boundaries),synthetic_checks='known lag, one-peak exclusion, missing brackets, distributed contrast and veto pass',
        concern='Local-refinement boundaries and peak-poor channels prohibit exact clock acceptance; no-ATE evidence rejects alias relative to a fresh candidate, not independent timing truth',
        promotion=False,validation_accessed=False,test_accessed=False,trajectory_metrics='unavailable: no predictions'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
