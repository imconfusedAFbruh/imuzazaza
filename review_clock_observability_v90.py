"""Independent event dynamic programming and source/run reproduction for v89."""
import csv,json
import numpy as np
from scipy import signal
import pipeline as p
from audit_fold_routes_v59 import verified_json
from clock_observability_v89 import OUT as AUDIT,check
from distributed_clock_candidates_v86 import OUT as CANDIDATES,load_inputs,arrays
from distributed_clock_evidence_v87 import OUT as EVIDENCE

OUT=p.ROOT/'outputs_clock_observability_review_v90'


def spans(mask):
    edges=np.diff(np.r_[False,mask,False].astype(int))
    return list(zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))


def maximum_matching(a,b,bound,tolerance):
    if not len(a) or not len(b):return 0
    points={-bound,bound}
    for x in a:
        for y in b:
            for edge in (x-y-tolerance,x-y+tolerance):
                if -bound<=edge<=bound:points.add(float(edge))
    points=sorted(points);trials=points+[(x+y)/2 for x,y in zip(points,points[1:])]
    maximum=0
    for lag in trials:
        dp=np.zeros((len(a)+1,len(b)+1),int)
        for i,x in enumerate(a,1):
            for j,y in enumerate(b,1):
                dp[i,j]=max(dp[i-1,j],dp[i,j-1])
                if abs(x-y-lag)<=tolerance+1e-12:dp[i,j]=max(dp[i,j],dp[i-1,j-1]+1)
        maximum=max(maximum,int(dp[-1,-1]))
    return maximum


def main():
    check()
    assert maximum_matching(np.array([1.,3.]),np.array([0.,2.]),5.,.2)==2
    assert maximum_matching(np.array([1.,4.]),np.array([0.,1.]),5.,.2)==1
    assert maximum_matching(np.array([5.2]),np.array([0.]),5.,.2)==1
    assert maximum_matching(np.array([]),np.array([0.]),5.,.2)==0
    cfg,inv,clocks,models,hashes=load_inputs()
    for folder in (AUDIT,EVIDENCE,CANDIDATES):
        manifest=json.loads((folder/'artifact_manifest.json').read_text())
        for rel,sha in manifest['sha256'].items():assert p.digest(folder/rel)==sha;hashes+=1
    rows=list(csv.DictReader((AUDIT/'channels.csv').open()));maximum_difference=0.;checks=[]
    for row in rows:
        ident=row['id'];mode=row['channel'];full,gt=arrays(ident)
        assert inv[ident]['partition']=='train'
        clock=next(q for q in clocks if q['id']==ident)
        terms=models[str(clock['fold'])]['calibration'][inv[ident]['setup']]['terms']
        if mode=='signed_yaw':
            q=terms[2];imu=full['raw'][:,q['column']]*q['scale']+q['intercept'];ref=gt['yaw']
        else:
            wheels=[full['raw'][:,q['column']]*q['scale']+q['intercept'] for q in terms[:2]]
            imu=np.abs((wheels[0]+wheels[1])/2);ref=np.abs(gt['speed'])
        a=signal.sosfiltfilt(signal.butter(2,2.,fs=cfg['hz'],output='sos'),imu)
        a=(a-a.mean())/max(a.std(),1e-8)
        mask=gt['derivative_valid']&np.isfinite(ref);b=np.full(len(ref),np.nan)
        lengths=[int(end-start) for start,end in spans(mask)]
        for start,end in spans(mask):
            if end-start>=20:b[start:end]=signal.sosfiltfilt(signal.butter(2,2.,fs=float(gt['hz']),output='sos'),ref[start:end])
        bm=np.isfinite(b);b[bm]=(b[bm]-b[bm].mean())/max(b[bm].std(),1e-8)
        with np.load(EVIDENCE/'signals'/(ident+'.npz')) as z:
            assert np.array_equal(bm,z[mode+'_bm'])
            assert np.array_equal(full['t'],z['t']) and np.array_equal(gt['t'],z['rt'])
            for actual,saved in ((a,z[mode+'_a']),(b[bm],z[mode+'_b'][bm])):
                delta=float(np.max(np.abs(actual-saved)));maximum_difference=max(maximum_difference,delta);assert delta<1e-12
            peaks=[]
            for values,valid,hz in ((np.abs(a) if mode=='signed_yaw' else a,full['imu_valid'],cfg['hz']),
                                    (np.abs(b) if mode=='signed_yaw' else b,bm,float(gt['hz']))):
                selected=[]
                for start,end in spans(valid&np.isfinite(values)):
                    selected.extend((signal.find_peaks(values[start:end],prominence=cfg['peak_prominence'],distance=hz*cfg['peak_distance_s'])[0]+start).tolist())
                peaks.append(np.array(selected,dtype=int))
            assert np.array_equal(peaks[0],z[mode+'_pi']) and np.array_equal(peaks[1],z[mode+'_pg'])
        count=maximum_matching(full['t'][peaks[0]],gt['t'][peaks[1]],cfg['max_lag_s'],cfg['peak_tolerance_s'])
        assert count==int(row['maximum_matches'])
        assert int(mask.sum())==int(row['derivative_frames'])
        assert sum(n for n in lengths if n<20)==int(row['short_run_frames'])
        assert int(bm.sum())==int(row['feature_frames'])
        assert len(spans(bm))==int(row['observed_runs'])
        assert max((end-start for start,end in spans(bm)),default=0)/cfg['hz']==float(row['longest_observed_run_s'])
        checks.append(dict(id=ident,channel=mode,independent_maximum_matches=count,peak_provenance='exact',run_accounting='exact'))
    inventory=list(csv.DictReader((CANDIDATES/'inventory.csv').open()))
    assert len(inventory)==207 and sum(q['participant']=='No.20' for q in inventory)==15
    assert len(rows)==20 and sum(q['accepted'] for q in clocks)==199
    OUT.mkdir(exist_ok=False);p.write_csv(OUT/'checks.csv',checks)
    p.save_json(OUT/'run.json',dict(parent_hashes_verified=hashes,independent_channels=20,maximum_feature_difference=maximum_difference,
        event_maxima='20/20 dynamic-programming maxima agree',run_and_peak_provenance='20/20 exact',
        trials_preserved=207,no20_preserved=15,accepted_clocks_unchanged=199,rejected_clocks_unchanged=8,
        review='same-context independent arithmetic; no separate-agent or external timing review',
        promotion=False,validation_accessed=False,test_accessed=False,trajectory_metrics='unavailable: no predictions'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
