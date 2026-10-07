"""Training-only adjudication of large observed-clock basin changes.

Same old training calibration, full original streams and observed native C3D
derivatives; no trajectory-position objective, no validation/test access.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,csv,time
from pathlib import Path
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pipeline as p
from observed_reference_experiment import observed_markers
from observed_sync_experiment import observed_feature,segment_peaks

OUT=p.ROOT/'outputs_clock_alias_v40'
def corr(a,b):
    return float(np.corrcoef(a,b)[0,1]) if len(a)>=60 and min(np.std(a),np.std(b))>.04 else None
def evaluate(t,a,iv,rt,b,mask,lag):
    x,ok=p.masked_interp(rt+lag,t,a,iv)
    good=mask&ok&np.isfinite(b)
    return corr(x[good],b[good]),int(good.sum()),x,good
def peaks(t,x,mask,hz):
    return t[segment_peaks(x,mask,hz,dict(peak_prominence=.35,peak_distance_s=.4))]
def event_info(ip,rp,lag):
    if min(len(ip),len(rp))<2:return dict(imu_peaks=len(ip),ref_peaks=len(rp))
    # Ordinal first/last differences prohibit quietly renumbering repeated events.
    n=min(2,len(ip),len(rp))
    first=float(np.median(ip[:n]-rp[:n]-lag));last=float(np.median(ip[-n:]-rp[-n:]-lag))
    distance=np.abs(ip[:,None]-(rp[None,:]+lag));nearest=distance.min(axis=1)
    return dict(imu_peaks=len(ip),ref_peaks=len(rp),first_ordinal_error_s=first,last_ordinal_error_s=last,
                nearest_peak_median_s=float(np.median(nearest)),imu_peak_matched_fraction=float(np.mean(nearest<=.2)),
                reference_peak_matched_fraction=float(np.mean(distance.min(axis=0)<=.2)))

def main():
    started=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve output')
    OUT.mkdir();(OUT/'figures').mkdir()
    cfg=json.loads((p.ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings']
    inventory={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    changes=list(csv.DictReader((p.ROOT/'outputs_clock_refit_v38/clock_changes.csv').open()))
    train=[q for q in changes if q['partition']=='train']
    candidates=[q for q in train if abs(float(q['offset_delta_s']))>.25]
    protocol=dict(training_records_screened=len(train),large_changes=len(candidates),threshold_s=.25,
        calibration='same outputs_observed_reference_v7 training sync_terms for both candidate clocks',
        fixed_common_support='intersection of native observed derivative support and all old/new ±100ms candidate sensor brackets',
        grid_step_s=.005,basin_radius_s=.1,window_s=8,
        proposed_gate='Large change requires identifiable speed or signed-yaw channel correlation gain >=.025, no independent informative channel regression >.025, and distributed windows/ordinal edge events supporting same basin. Missing evidence is ambiguous; repeated-motion alias cannot be accepted on selected-channel global correlation alone.',
        no_position_objective=True,validation_accessed=False,test_accessed=False)
    p.save_json(OUT/'protocol.json',protocol)
    results=[];windows=[];curves=[];events=[]
    p.read_markers=observed_markers
    for q in candidates:
        row=inventory[q['id']]
        if row['partition']!='train':raise RuntimeError('Wrong split')
        t,raw,iv=p.sample_streams(p.imu_streams(p.ROOT/row['imu']),cfg)
        gt=p.reference(p.ROOT/row['c3d'],cfg,row['setup']);rt=gt['t']
        cal=cfg['sync_terms'][row['setup']];wheel=[raw[:,c['column']]*c['scale']+c['intercept'] for c in cal[:2]]
        old,new=float(q['old_offset_s']),float(q['new_offset_s']);lags=np.r_[old+np.arange(-.1,.1001,.005),new+np.arange(-.1,.1001,.005)]
        fig,axs=plt.subplots(2,3,figsize=(15,7));records=[]
        for j,(mode,imu,ref) in enumerate([('signed_yaw',raw[:,cal[2]['column']]*cal[2]['scale']+cal[2]['intercept'],gt['yaw']),('speed',np.abs((wheel[0]+wheel[1])/2),np.abs(gt['speed']))]):
            a=p.smooth_standard(imu,cfg['hz']);b,bm=observed_feature(ref,gt['derivative_valid'],gt['hz']);common=bm.copy()
            for lag in lags:
                _,ok=p.masked_interp(rt+lag,t,a,iv);common &=ok
            rr=dict(id=row['id'],participant=row['participant'],condition=row['condition'],channel=mode,old_offset_s=old,new_offset_s=new,offset_delta_s=new-old,common_frames=int(common.sum()),reference_feature_frames=int(bm.sum()))
            scores=[]
            for k,lag in enumerate(lags):
                c,n,_,_=evaluate(t,a,iv,rt,b,common,lag);scores.append(c if c is not None else np.nan)
                curves.append(dict(id=row['id'],channel=mode,basin='old' if k<41 else 'new',offset_s=float(lag),correlation=c,frames=n))
            for basin,lag in [('old',old),('new',new)]:
                c,n,x,good=evaluate(t,a,iv,rt,b,common,lag);rr[basin+'_correlation']=c
                use=scores[:41] if basin=='old' else scores[41:];grid=lags[:41] if basin=='old' else lags[41:]
                if np.isfinite(use).any():
                    k=int(np.nanargmax(use));mx=float(use[k]);plateau=grid[np.array(use)>=mx-.002]
                    rr[basin+'_best_correlation']=mx;rr[basin+'_best_offset_s']=float(grid[k]);rr[basin+'_plateau_width_s']=float(np.ptp(plateau));rr[basin+'_boundary']=k in (0,40)
                axs[j,0].plot(rt,np.where(good,x,np.nan),label=basin+' IMU',alpha=.65)
            rr['correlation_delta']=rr['new_correlation']-rr['old_correlation'] if rr['new_correlation'] is not None and rr['old_correlation'] is not None else None
            # Global event lists reflect full acquisition overlap, not changed crop.
            ip=peaks(t,np.abs(a) if mode=='signed_yaw' else a,iv,cfg['hz']);rp=peaks(rt,np.abs(b) if mode=='signed_yaw' else b,bm,gt['hz'])
            for basin,lag in [('old',old),('new',new)]:events.append(dict(id=row['id'],channel=mode,basin=basin,**event_info(ip,rp,lag)))
            for center in np.arange(4,rt[-1]-3.99,8):
                ok=common&(rt>=center-4)&(rt<center+4)
                co,_,_,_=evaluate(t,a,iv,rt,b,ok,old);cn,_,_,_=evaluate(t,a,iv,rt,b,ok,new)
                if co is None or cn is None:continue
                windows.append(dict(id=row['id'],channel=mode,center_s=float(center),frames=int(ok.sum()),old_correlation=co,new_correlation=cn,delta=cn-co))
            w=[x for x in windows if x['id']==row['id'] and x['channel']==mode]
            rr['windows']=len(w);rr['new_window_wins']=sum(x['delta']>=.025 for x in w);rr['old_window_wins']=sum(x['delta']<=-.025 for x in w)
            records.append(rr);results.append(rr)
            axs[j,0].plot(rt,np.where(common,b,np.nan),color='black',label='observed C3D');axs[j,0].set(title=mode+' same-support signals',xlabel='Native C3D time (s)');axs[j,0].legend(fontsize=7)
            axs[j,1].plot(lags[:41],scores[:41],label='old');axs[j,1].plot(lags[41:],scores[41:],label='new');axs[j,1].set(title='Fixed-support basin correlation',xlabel='IMU time minus C3D time (s)');axs[j,1].legend()
            axs[j,2].plot([x['center_s'] for x in w],[x['delta'] for x in w],'o-');axs[j,2].axhline(0,color='black');axs[j,2].set(title='New minus old window correlation',xlabel='8s window center (s)')
        for ax in axs.ravel():ax.grid(alpha=.2)
        fig.suptitle(row['id']+'; training only; no position objective');fig.tight_layout();fig.savefig(OUT/'figures'/f"{row['id']}.png",dpi=140);plt.close(fig)
        print(row['id'],[(r['channel'],r['correlation_delta'],r['new_window_wins'],r['old_window_wins']) for r in records],flush=True)
    for name,data in [('channels.csv',results),('windows.csv',windows),('basin_curves.csv',curves),('ordinal_events.csv',events)]:p.write_csv(OUT/name,data)
    p.save_json(OUT/'run.json',dict(**protocol,runtime_seconds=time.perf_counter()-started,source_sha256=p.digest(Path(__file__))))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file() and f.name!='artifact_manifest.json'}))
if __name__=='__main__':main()
