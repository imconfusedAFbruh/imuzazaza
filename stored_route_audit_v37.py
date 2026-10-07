"""Weak-secondary stored-reference geometry. Does not alter primary scores."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import csv,json,time
import numpy as np
from pathlib import Path
from scipy.spatial.distance import cdist
from route_metrics_audit_v36 import route,pieces,length,sample_piece,frechet,aggregates,METRICS
from pipeline import ROOT,runs,digest,save_json,write_csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=ROOT/'outputs_stored_route_v37';SOURCE=ROOT/'outputs_recovered_training_v32';PRED=ROOT/'outputs_dynamic_blend_v34'

def frechet_fast(p,q):
    """Discrete Fréchet via monotone grid reachability and distance bisection.

    Vectorized reachable row propagates from a previous-row anchor until the
    next unavailable cell. No trajectory transforms. Numerical tolerance1e-8m.
    """
    d=cdist(p,q);idx=np.arange(len(q));low=max(d[0,0],d[-1,-1]);high=d.max()
    def reachable(limit):
        previous=np.zeros(len(q),bool)
        for i,row in enumerate(d):
            allow=row<=limit
            if i==0:
                if not allow[0]:return False
                previous=np.logical_and.accumulate(allow)
            else:
                permitted=previous|np.r_[False,previous[:-1]]
                anchors=np.maximum.accumulate(np.where(allow&permitted,idx,-1))
                barrier=np.maximum.accumulate(np.where(~allow,idx,-1))
                previous=allow&(anchors>barrier)
                if not previous.any():return False
        return bool(previous[-1])
    if reachable(low):return float(low)
    while high-low>1e-8:
        middle=(high+low)/2
        if reachable(middle):high=middle
        else:low=middle
    return float(high)

def ordered(ref,pred):
    coarse=[];fine=[];num=0.;den=0.
    for r,p in zip(ref,pred):
        coarse.append(frechet_fast(sample_piece(r,.05),sample_piece(p,.05)))
        fine.append(frechet_fast(sample_piece(r,.025),sample_piece(p,.025)))
        n=max(2,int(np.ceil(max(length(r),length(p))/.01))+1)
        def normalized(x):
            s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(x,axis=0),axis=1))]
            if s[-1]<=1e-12:return np.repeat(x[:1],n,axis=0)
            keep=np.r_[True,np.diff(s)>1e-12];t=np.linspace(0,s[-1],n)
            return np.c_[np.interp(t,s[keep],x[keep,0]),np.interp(t,s[keep],x[keep,1])]
        e=np.linalg.norm(normalized(r)-normalized(p),axis=1);num+=float(np.sum(e*e));den+=len(e)
    return dict(supported_run_frechet_max_m=max(fine),supported_run_frechet_coarse_max_m=max(coarse),supported_run_frechet_max_abs_refinement_m=float(np.max(np.abs(np.asarray(fine)-coarse))),supported_run_arc_correspondence_rmse_m=float(np.sqrt(num/den)),supported_runs=len(ref))

def plots(meta,a,b,output):
    start=a['original_v21_xy_m'][0];obs=a['reference_valid'];valid=b['stored_reference_valid'];proc=b['stored_processed_valid'];ref=b['stored_reference_xy_m'];t=a['time_s']
    fig,axs=plt.subplots(1,3,figsize=(13,4.2));rr=a['reference_xy_m'].copy();rr[~obs]=np.nan;axs[0].plot(*(rr-start).T,color='black',lw=1.4,label='Directly observed')
    weak=ref.copy();weak[~valid]=np.nan;axs[0].plot(*(weak-start).T,color='#997634',ls=':',lw=1.1,label='Stored reference incl. processed')
    for model,color,label in [('original_v21','#809ab9','Original v21'),('selected_blend','#e77535','Tilt blend .75')]:
        xy=a[model+'_xy_m'];axs[0].plot(*(xy-start).T,color=color,lw=1,label=label)
        e=np.linalg.norm(xy-ref,axis=1)*1000;e[~valid]=np.nan;axs[1].plot(t,e,color=color,lw=1,label=label)
    axs[2].plot(t,obs.astype(float),color='black',label='Observed');axs[2].plot(t,proc.astype(float)*.8,color='#997634',label='Stored processed');axs[2].plot(t,valid.astype(float)*.6,color='#187fa0',label='Geometry accepted');axs[2].set(ylim=(-.05,1.15),xlabel='Time (s)',ylabel='Support indicator',title='Reference provenance');axs[2].legend(fontsize=7)
    axs[0].set_aspect('equal',adjustable='datalim');axs[0].set(xlabel='X from original initial position (m)',ylabel='Y (m)',title='Weak secondary reference; no alignment');axs[0].legend(fontsize=6)
    axs[1].set(xlabel='Time (s)',ylabel='Secondary position error (mm)',title='Stored supported values incl. processed')
    for ax in axs:ax.grid(alpha=.2)
    fig.suptitle(meta['id']+'\nPrimary observed-only scores remain unchanged',fontsize=10);fig.tight_layout();fig.savefig(output,dpi=120);plt.close(fig)

def main():
    if OUT.exists():raise RuntimeError('Preserve sealed output')
    OUT.mkdir();(OUT/'figures').mkdir();began=time.perf_counter()
    # Validate exact recurrence independently on random short curves before audit.
    rng=np.random.default_rng(37);checks=[]
    for _ in range(8):
        p=rng.normal(size=(rng.integers(2,18),2));q=rng.normal(size=(rng.integers(2,18),2));checks.append(abs(frechet(p,q)-frechet_fast(p,q)))
    if max(checks)>1e-8:raise RuntimeError('Reachability implementation mismatch')
    sm=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256'];pm=json.loads((PRED/'artifact_manifest.json').read_text())['sha256']
    meta=list(csv.DictReader((PRED/'selected_blend_trials.csv').open()));records=[]
    for i,row in enumerate(meta):
        def load(folder,manifest):
            path=folder/'trajectories'/(row['id']+'.npz')
            if digest(path)!=manifest[str(path.relative_to(folder))]:raise RuntimeError('Cache changed')
            with np.load(path) as z:return {k:z[k] for k in z.files}
        a=load(PRED,pm);b=load(SOURCE,sm)
        for key in ['time_s','reference_valid','imu_valid','reference_xy_m','original_v21_xy_m']:
            if not np.array_equal(a[key],b[key],equal_nan=True):raise RuntimeError('Clock/support/control mismatch '+key)
        mask=b['stored_reference_valid']&np.isfinite(b['stored_reference_xy_m']).all(1)&np.isfinite(a['selected_blend_xy_m']).all(1)&np.isfinite(a['original_v21_xy_m']).all(1)
        if np.any(a['reference_valid'] & ~mask):raise RuntimeError('Original observed support lost')
        ref=pieces(b['stored_reference_xy_m'],mask);rl=sum(map(length,ref))
        for model in ['original_v21','selected_blend']:
            xy=a[model+'_xy_m'];pred=pieces(xy,mask);v=route(ref,pred,.01);o=ordered(ref,pred)
            rec=dict(id=row['id'],participant=row['participant'],condition=row['condition'],model=model,
                position_rmse_m=float(np.sqrt(np.mean(np.sum((xy[mask]-b['stored_reference_xy_m'][mask])**2,axis=1)))),
                reference_kind='weak stored including processed',stored_supported_frames=int(mask.sum()),stored_coverage=float(mask.mean()),direct_observed_frames=int(a['reference_valid'].sum()),added_processed_frames=int((mask&~a['reference_valid']).sum()),
                supported_reference_path_m=rl,supported_prediction_path_m=sum(map(length,pred)),supported_last_endpoint_error_m=float(np.linalg.norm(xy[mask][-1]-b['stored_reference_xy_m'][mask][-1])),
                true_recording_endpoint_supported=bool(mask[-1]),supported_pathlength_signed_error_m=sum(map(length,pred))-rl,supported_pathlength_absolute_error_m=abs(sum(map(length,pred))-rl),
                fully_continuous_recording=bool(mask.all()),full_recording_discrete_frechet_m=o['supported_run_frechet_max_m'] if mask.all() else '',full_recording_arc_correspondence_rmse_m=o['supported_run_arc_correspondence_rmse_m'] if mask.all() else '',**v,**o)
            records.append(rec)
        plots(row,a,b,OUT/'figures'/(row['id']+'.png'));print(i+1,row['id'],'runs',len(ref),flush=True)
    for name,values in [('trials',records),('summary',aggregates(records,['model'])),('participants',aggregates(records,['model','participant'])),('maneuvers',aggregates(records,['model','condition']))]:write_csv(OUT/(name+'.csv'),values)
    primary=list(csv.DictReader((ROOT/'outputs_route_metrics_v36/trials.csv').open()));paired=[]
    for r in records:
        old=next(x for x in primary if x['id']==r['id'] and x['model']==r['model']);p=dict(id=r['id'],participant=r['participant'],condition=r['condition'],model=r['model'],observed_runs=int(old['supported_runs']),stored_runs=r['supported_runs'],observed_coverage=float(old['observed_fraction']),stored_coverage=r['stored_coverage'])
        for key in METRICS:p[key+'_observed']=float(old[key]);p[key+'_stored']=r[key];p[key+'_stored_minus_observed']=r[key]-float(old[key])
        paired.append(p)
    write_csv(OUT/'support_comparison.csv',paired)
    save_json(OUT/'run.json',dict(summary=aggregates(records,['model']),models_fixed=True,test_accessed=False,primary_scores_unchanged=True,source_script_sha256=digest(Path(__file__)),source_model_sha256=digest(PRED/'model.json'),runtime_seconds=time.perf_counter()-began,frechet_sanity_max_error_m=max(checks),
        hypothesis='Stored processed geometry may restore route continuity and reveal global ordering that observed-fragment proximity hides.',
        source='Preserved v32 stored_reference_xy_m/stored_reference_valid at identical frozen timegrid. v32 source rejects negative residual/nonfinite native coordinates and geometry-invalid spans; existing bounded clockgrid resampling only, no new interpolation/recovery.',
        convention='Same v36 exact point-to-polyline distance;10mm spatial queries, equal bidirectional weight. Hausdorff sampled approximation.25/50mm resampled discreteFrechet via reachability to1e-8m numerical tolerance. Ordered comparisons full-recording only if every original cache-grid frame is supported; otherwise max over uninterrupted stored-supported runs. No alignment or resets.',
        reference_uncertainty='Processed residual0 positions are weak source values, not directly camera-observed or independently verified. Added support is not automatically improved truth.',
        complete_recordings=sum(r['fully_continuous_recording'] for r in records if r['model']=='selected_blend')))
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(aggregates(records,['model']),indent=2),flush=True)

if __name__=='__main__':main()
