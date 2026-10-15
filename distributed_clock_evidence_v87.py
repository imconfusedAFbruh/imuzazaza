"""Identical-support distributed evidence for fresh candidate clock pairs."""
import itertools,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pipeline as p
from distributed_clock_candidates_v86 import OUT as CANDIDATES,load_inputs,arrays,channels,correlation
from audit_fold_routes_v59 import verified_json
from native_refit_v81 import OUT as FROZEN

OUT=p.ROOT/'outputs_distributed_clock_evidence_v87'


def compare(t,a,iv,rt,b,bm,lags):
    sampled=[];common=bm.copy()
    for lag in lags:
        x,ok=p.masked_interp(rt+lag,t,a,iv);sampled.append(x);common &=ok
    correlations=[correlation(x,b,common) for x in sampled]
    windows=[]
    for start in np.arange(0,rt[-1],8.):
        good=common & (rt>=start) & (rt<start+8)
        cs=[correlation(x,b,good) for x in sampled]
        if all(c is not None for c in cs):windows.append(dict(start_s=float(start),frames=int(good.sum()),a_correlation=cs[0],b_correlation=cs[1],delta=cs[1]-cs[0]))
    return common,sampled,correlations,windows


def diagnostic_contrast(channels):
    informative=[r for r in channels if r['delta'] is not None and r['motion_eligible']]
    gains=[r for r in informative if r['delta']>=.025]
    if not gains or any(r['delta']<-.025 for r in informative):return False
    return any(r['b_window_wins']>=2 and r['a_window_wins']==0 for r in gains)


def check():
    good=dict(delta=.1,motion_eligible=True,b_window_wins=2,a_window_wins=0)
    assert diagnostic_contrast([good])
    assert not diagnostic_contrast([dict(good,b_window_wins=1)])
    assert not diagnostic_contrast([good,dict(good,delta=-.03)])
    assert not diagnostic_contrast([dict(good,a_window_wins=1)])
    assert not diagnostic_contrast([])


def main():
    check();cfg,inv,clocks,models,hashes=load_inputs()
    rows=verified_json(CANDIDATES,'candidates.json');clockmap={q['id']:q for q in clocks}
    fm=json.loads((FROZEN/'artifact_manifest.json').read_text())['sha256']
    OUT.mkdir(exist_ok=False);(OUT/'signals').mkdir();(OUT/'figures').mkdir()
    evidence=[];windows=[];pairs=[];supports=[];cases=[]
    for ident in sorted({q['id'] for q in rows}):
        r=inv[ident];clock=clockmap[ident];full,gt=arrays(ident)
        terms=models[str(clock['fold'])]['calibration'][r['setup']]['terms']
        candidates=[c['offset_s'] for q in rows if q['id']==ident for c in q['candidates']]
        if clock['accepted']:candidates.append(clock['offset_s'])
        lags=sorted(set(round(c,6) for c in candidates))
        source=FROZEN/'common_trajectories'/(ident+'.npz')
        assert p.digest(source)==fm[str(source.relative_to(FROZEN))]
        with np.load(source) as z:frozen_times=z['native_c3d_time_s'];frozen_support=z['imu_valid'];scored=frozen_support&z['reference_valid']
        for lag in lags:
            _,ok=p.masked_interp(frozen_times+lag,full['t'],full['raw'][:,15],full['imu_valid'])
            supports.append(dict(id=ident,offset_s=lag,frozen_imu_support_lost_frames=int((frozen_support&~ok).sum()),
                frozen_scored_support_lost_frames=int((scored&~ok).sum()),frozen_scored_frames=int(scored.sum())))
        signals=list(channels(full,gt,terms,cfg));saved=dict(t=full['t'],imu_valid=full['imu_valid'],rt=gt['t'])
        for mode,a,b,bm,pi,pg,info in signals:saved.update({mode+'_a':a,mode+'_b':b,mode+'_bm':bm,mode+'_pi':pi,mode+'_pg':pg})
        np.savez_compressed(OUT/'signals'/(ident+'.npz'),**saved)
        for la,lb in itertools.combinations(lags,2):
            channelrows=[]
            for mode,a,b,bm,pi,pg,info in signals:
                common,sampled,cs,ws=compare(full['t'],a,full['imu_valid'],gt['t'],b,bm,(la,lb))
                row=dict(id=ident,participant=r['participant'],condition=r['condition'],channel=mode,a_offset_s=la,b_offset_s=lb,
                    common_frames=int(common.sum()),motion_eligible=info['motion_eligible'],a_correlation=cs[0],b_correlation=cs[1],
                    delta=cs[1]-cs[0] if all(c is not None for c in cs) else None,
                    windows=len(ws),a_window_wins=sum(w['delta']<=-.025 for w in ws),b_window_wins=sum(w['delta']>=.025 for w in ws))
                # Restrict both event lists to the pair's observed common support.
                refpeaks=pg[common[pg]]
                for name,lag in [('a',la),('b',lb)]:
                    query=full['t'][pi]-lag
                    ix=np.searchsorted(gt['t'],query).clip(0,len(gt['t'])-1)
                    keep=(query>=gt['t'][0])&(query<=gt['t'][-1])&common[ix]
                    residuals=p.match_peaks(full['t'][pi[keep]],gt['t'][refpeaks]+lag,cfg['peak_tolerance_s'])
                    row[name+'_matched_peaks']=len(residuals)
                    row[name+'_peak_median_abs_s']=float(np.median(abs(np.asarray(residuals)))) if residuals else None
                evidence.append(row);channelrows.append(row)
                windows.extend([dict(id=ident,channel=mode,a_offset_s=la,b_offset_s=lb,**w) for w in ws])
            reverse=[dict(q,delta=-q['delta'] if q['delta'] is not None else None,a_window_wins=q['b_window_wins'],b_window_wins=q['a_window_wins']) for q in channelrows]
            pairs.append(dict(id=ident,a_offset_s=la,b_offset_s=lb,b_over_a_diagnostic_contrast=diagnostic_contrast(channelrows),a_over_b_diagnostic_contrast=diagnostic_contrast(reverse)))
        cases.append(dict(id=ident,participant=r['participant'],condition=r['condition'],v84_accepted=clock['accepted'],candidates=len(lags),
            candidate_pairs=len(lags)*(len(lags)-1)//2,diagnostic_contrasts=sum(q['a_over_b_diagnostic_contrast'] or q['b_over_a_diagnostic_contrast'] for q in pairs if q['id']==ident),
            decision='diagnostic only; no clock accepted or overwritten'))
        if clock['accepted'] and len(lags)>1:
            fig,axs=plt.subplots(2,1,figsize=(12,6))
            for ax,(mode,a,b,bm,pi,pg,info) in zip(axs,signals):
                ax.plot(gt['t'],np.where(bm,b,np.nan),'k',label='observed C3D')
                for lag in lags:
                    x,ok=p.masked_interp(gt['t']+lag,full['t'],a,full['imu_valid'])
                    ax.plot(gt['t'],np.where(bm&ok,x,np.nan),alpha=.5,label=f'IMU lag {lag:+.4f}s')
                ax.set_title(mode+' candidate overlays (pairwise scores use identical support)');ax.legend(fontsize=7);ax.grid(alpha=.2)
            fig.suptitle(ident+'; TRAIN diagnostic only');fig.tight_layout();fig.savefig(OUT/'figures'/(ident+'.png'),dpi=130);plt.close(fig)
        print('v87',ident,cases[-1],flush=True)
    p.write_csv(OUT/'channels.csv',evidence);p.write_csv(OUT/'windows.csv',windows);p.write_csv(OUT/'pairs.csv',pairs);p.write_csv(OUT/'support.csv',supports);p.write_csv(OUT/'cases.csv',cases)
    for key in ('participant','condition'):
        p.write_csv(OUT/(key+'_coverage.csv'),[{key:v,'investigated_cases':sum(q[key]==v for q in cases),
            'candidate_cases':sum(q[key]==v and q['candidates']>0 for q in cases),'v84_rejected':sum(q[key]==v and not q['v84_accepted'] for q in cases)} for v in sorted({q[key] for q in cases})])
    p.save_json(OUT/'run.json',dict(trials_preserved=207,cases=10,pairs=len(pairs),channel_comparisons=len(evidence),windows=len(windows),
        cases_with_candidates=sum(q['candidates']>0 for q in cases),cases_with_distributed_contrast=sum(q['diagnostic_contrasts']>0 for q in cases),
        v84_accepted_unchanged=199,v84_rejected_unchanged=8,promotion=False,
        trajectory_metrics='All unavailable: no predictions; retained v34 and v81 unchanged',
        decision='Diagnostic evidence only; all-207 reliable clock gate remains unmet',validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
