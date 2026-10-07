"""Reference-assisted residual affine-clock diagnostic; never a position fit.

All accepted train and validation caches; test forbidden. Select method using
blocked signal correlation on training before reading validation caches.
Existing device->PC affine fits and inherited C3D offset remain unchanged.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,time,csv
from pathlib import Path
import numpy as np
from scipy import signal,optimize
import pipeline as p
from observed_sync_experiment import observed_feature

OUT=p.ROOT/'outputs_affine_clock_v36'
SOURCE=p.ROOT/'outputs_observed_reference_v7'
WINDOW=8.; GRID=np.arange(-.100,.10001,.002)

def corr(a,b):
    return float(np.corrcoef(a,b)[0,1]) if len(a)>30 and min(np.std(a),np.std(b))>1e-8 else float('nan')

def signals(d,cal,mode):
    if mode=='signed_yaw':
        q=cal[2]; imu=d['raw'][:,q['column']]*q['scale']+q['intercept']; ref=d['gt_yaw']
    else:
        wheel=[d['raw'][:,q['column']]*q['scale']+q['intercept'] for q in cal[:2]]
        imu=np.abs((wheel[0]+wheel[1])/2);ref=np.abs(d['gt_v'])
    a=p.smooth_standard(imu,100.)
    b,bvalid=observed_feature(ref,d['label_valid'],100.)
    return a,b,bvalid

def local_windows(d,cal,mode):
    t=d['t'];a,b,rm=signals(d,cal,mode);iv=d['imu_valid'];bad=np.r_[0,np.cumsum(~iv)]
    records=[]
    for i,start in enumerate(np.arange(0,t[-1]-WINDOW+.001,WINDOW)):
        lo=np.clip(np.searchsorted(t,t-.1)-1,0,len(t)-1);hi=np.clip(np.searchsorted(t,t+.1),0,len(t)-1)
        ok=(t>=start)&(t<start+WINDOW)&rm&(t>=t[0]+.1)&(t<=t[-1]-.1)&(bad[hi+1]==bad[lo])
        # A fixed support mask across every candidate prevents overlap gains.
        if ok.sum()<200 or np.std(b[ok])<.15:continue
        rt=t[ok];scores=np.array([corr(np.interp(rt+lag,t,a),b[ok]) for lag in GRID]);j=int(np.nanargmax(scores));lag=float(GRID[j]);c=float(scores[j])
        if c<.6:continue
        plateau=GRID[scores>=c-.002]
        records.append(dict(index=i,center_s=float(start+WINDOW/2),lag_s=lag,correlation=c,
                            inherited_correlation=corr(a[ok],b[ok]),frames=int(ok.sum()),
                            width_corr_drop002_ms=float((plateau.max()-plateau.min())*1000),boundary=j in (0,len(GRID)-1)))
    return records,(a,b,rm)

def model(w,kind):
    if not w:return 0.,0.,False
    x=np.array([q['center_s'] for q in w]);y=np.array([q['lag_s'] for q in w])
    intercept=float(np.median(y));slope=0.;accepted=False
    if kind!='offset' and len(w)>=3 and np.ptp(x)>=16:
        fit=optimize.least_squares(lambda q:q[0]+q[1]*x-y,[intercept,0.],loss='soft_l1',f_scale=.01,bounds=([-.1,-.002],[.1,.002]))
        intercept,slope=map(float,fit.x);accepted=True
        if kind=='guarded_affine':
            # Predeclared identifiability gate. Leave-one-window estimates must
            # retain slope sign and fit residual <=10ms, and no search boundary.
            slopes=[]
            for j in range(len(w)):
                m=np.arange(len(w))!=j
                slopes.append(float(np.polyfit(x[m],y[m],1)[0]))
            residual=np.median(np.abs(intercept+slope*x-y))
            accepted=(not any(q['boundary'] for q in w) and residual<=.010 and min(slopes)*max(slopes)>0 and abs(slope)<.0019)
            if not accepted:intercept,slope=float(np.median(y)),0.
    return intercept,slope,accepted

def held_score(d,arrays,w,intercept,slope):
    a,b,rm=arrays;t=d['t'];iv=d['imu_valid'];changes=[]
    for q in w:
        use=(t>=q['center_s']-WINDOW/2)&(t<q['center_s']+WINDOW/2)&rm
        query=t+intercept+slope*t
        # Same support for baseline/candidate, bounded shifts and valid brackets.
        k=np.clip(np.searchsorted(t,query),1,len(t)-1)
        ok=use&iv&iv[k]&iv[k-1]&(query>=t[0])&(query<=t[-1])
        if ok.sum()<200:continue
        base=corr(a[ok],b[ok]);candidate=corr(np.interp(query[ok],t,a),b[ok])
        if np.isfinite(base+candidate):changes.append(candidate-base)
    return float(np.mean(changes)) if changes else float('nan')

def native(row,meta):
    z=p.ezc3d.c3d(str(p.ROOT/row['c3d']));header=z['header']['points'];params=z['parameters'];names=[]
    for group,items in params.items():
        for name in items:
            if any(term in name.upper() for term in ('TIME','START','TRIGGER','SYNC')):names.append(group+':'+name)
    raw=np.loadtxt(p.ROOT/row['imu'],delimiter=',',skiprows=1,usecols=(1,3,4,13),converters={1:lambda x:{'L':0,'R':1,'C':2}[x.decode() if isinstance(x,bytes) else x]})
    output=[]
    for code,label in enumerate(('L','R','C')):
        s=raw[raw[:,0]==code];dt=np.diff(s[:,1])/1e6;pc=np.diff(s[:,2])/1e9
        output.append(dict(id=row['id'],partition=row['partition'],sensor=label,device_hz=1/np.median(dt),
                           dt_p05_ms=float(np.quantile(dt,.05)*1000),dt_p95_ms=float(np.quantile(dt,.95)*1000),dt_max_ms=float(max(dt)*1000),
                           intervals_gt20ms=int((dt>.020).sum()),nonmonotonic=int((dt<=0).sum()),missing_before=int(s[:,3].sum()),
                           pc_repeated_fraction=float((pc==0).mean()),clock_scale=meta['streams'][code]['clock_scale'],
                           clock_residual_ms=meta['streams'][code]['clock_residual_ms']))
    return output,dict(id=row['id'],partition=row['partition'],point_rate=float(params['POINT']['RATE']['value'][0]),
                      header_rate=float(header['frame_rate']),first_frame=int(header['first_frame']),last_frame=int(header['last_frame']),
                      timing_parameters=';'.join(names),analog_channels=int(z['data']['analogs'].shape[1]))

def run_partition(partition,accepted,inventory,cfg,manifest,selected=None):
    trials=[];windows=[];streams=[];headers=[]
    for n,q in enumerate(accepted):
        row=inventory[q['id']]
        if row['partition']!=partition or partition=='test':raise RuntimeError('Wrong split')
        path=SOURCE/'cache'/f"{row['id']}.npz";mp=path.with_suffix('.json')
        for file in (path,mp):
            if p.digest(file)!=manifest['sha256'][str(file.relative_to(SOURCE))]:raise RuntimeError('Cache changed')
        with np.load(path) as z:d={k:z[k] for k in z.files}
        meta=json.loads(mp.read_text());mode=meta['synchronization']['source'];cal=cfg['sync_terms'][row['setup']]
        if mode not in ('signed_yaw','calibrated_speed'):raise RuntimeError(mode)
        w,arrays=local_windows(d,cal,mode)
        for r in w:windows.append(dict(id=row['id'],partition=partition,participant=row['participant'],condition=row['condition'],source=mode,**r))
        # Alternating nonoverlapping8s blocks. Two-way cross-fit; short trials
        # remain recorded with insufficient-identifiability status.
        for kind in ('offset','affine','guarded_affine'):
            scores=[]
            for parity in (0,1):
                fit=[r for r in w if r['index']%2==parity];held=[r for r in w if r['index']%2!=parity]
                if len(fit)<1 or len(held)<1:continue
                inter,slope,gate=model(fit,kind);scores.append(held_score(d,arrays,held,inter,slope))
            inter,slope,gate=model(w,kind)
            trials.append(dict(id=row['id'],partition=partition,participant=row['participant'],condition=row['condition'],date=row['date'],source=mode,method=kind,
                               windows=len(w),duration_s=float(d['t'][-1]),heldout_correlation_delta=float(np.nanmean(scores)) if any(np.isfinite(scores)) else None,
                               residual_offset_ms=inter*1000,residual_skew_ppm=slope*1e6,end_clock_change_ms=slope*d['t'][-1]*1000,affine_gate=gate,
                               # Query t'=t+inter+slope*t means C3D clock a=1/(1+slope), b=-inter/(1+slope) relative to inherited clock.
                               a_relative=1/(1+slope),b_relative_s=-inter/(1+slope),selected=kind==selected))
        ss,hh=native(row,meta);streams.extend(ss);headers.append(hh)
        if (n+1)%25==0:print(partition,n+1,flush=True)
    return trials,windows,streams,headers

def aggregate(rows,field='method'):
    results=[]
    for method in sorted({r[field] for r in rows}):
        rr=[r for r in rows if r[field]==method and r['heldout_correlation_delta'] is not None]
        person=[np.mean([r['heldout_correlation_delta'] for r in rr if r['participant']==person]) for person in sorted({r['participant'] for r in rr})]
        results.append(dict(method=method,trials=len(rr),participants=len(person),equal_person_correlation_delta=float(np.mean(person)) if person else None))
    return results

def main():
    started=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve sealed experiments')
    OUT.mkdir();run=json.loads((SOURCE/'run.json').read_text());cfg=run['settings'];manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())
    inventory={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    qc=list(csv.DictReader((SOURCE/'qc.csv').open(newline='')))
    save=lambda name,x:p.save_json(OUT/name,x)
    save('protocol.json',dict(hypothesis='Residual stream-to-C3D drift remains after device->PC affine fit and single C3D offset',window_s=WINDOW,lag_bounds_s=[-.1,.1],step_s=.002,
                             methods=['offset','affine','guarded_affine'],skew_bounds_ppm=[-2000,2000],selection='Training equal-person heldout correlation delta, two-way alternating8s block crossfit',
                             no_position_objective=True,no_trajectory_changed=True,reference_assisted=True,deployable_without_C3D=False,test_accessed=False))
    train=run_partition('train',[r for r in qc if r['partition']=='train' and r['status']=='accepted'],inventory,cfg,manifest)
    summary=aggregate(train[0]);selected=max(summary,key=lambda r:r['equal_person_correlation_delta'])['method'];save('selection.json',dict(selected=selected,training=summary,selected_before_validation=True))
    validation=run_partition('validation',[r for r in qc if r['partition']=='validation' and r['status']=='accepted'],inventory,cfg,manifest,selected)
    for name,i in [('clock_trials.csv',0),('clock_windows.csv',1),('native_streams.csv',2),('c3d_metadata.csv',3)]:p.write_csv(OUT/name,train[i]+validation[i])
    save('run.json',dict(selected=selected,training=summary,validation=aggregate(validation[0]),training_trials=473,validation_trials=71,test_accessed=False,no_model_changed=True,
                         runtime_seconds=time.perf_counter()-started,source_sha256=p.digest(Path(__file__))))
    report=['# Affine clock diagnostic v36','', 'Reference-assisted signal alignment only; no prediction trajectory, initial pose, model, or reported100.702mm RMSE was changed. Device-to-PC affine clock fitting already exists. This experiment tests residual clock effects relative to the inherited single-lag C3D clock.', '', 'Method selected on training blocked holdout correlations before validation. All473 training and71 validation native IMU/C3D timing metadata included. No test data.', '', '| Split | Method | Identifiable trials | Equal-person heldout correlation change |','|---|---|---:|---:|']
    for split,ss in [('train',summary),('validation',aggregate(validation[0]))]:
        report += [f"| {split} | {r['method']} | {r['trials']} | {r['equal_person_correlation_delta']:.8f} |" for r in ss]
    report += ['',f'Training-selected method: **{selected}**. Correlation differences do not establish independent timing accuracy or improvement in synchronized position RMSE.', '', 'Eight-second windows reject low-motion/low-correlation support. Short trials lack residual skew identifiability. Full-record slopes are descriptive reference-assisted estimates, not truth: mounting, slip, derivative filters and signal-shape mismatch can mimic changing lag. Local correlation-drop widths are objective flatness, not confidence intervals. Alternating blocked holdouts share only boundary filter effects; no overlapping windows.', '', 'Timing recommendation: preserve device timestamps, estimate each device-to-receiver affine clock robustly, then estimate C3D offset/skew from independent shared trigger/timecode or multiple distributed motion events with uncertainty. Motion correlation remains offline evaluative synchronization; C3D is unavailable at deployment.', '', 'Primary technical documentation: [C3D POINT:RATE](https://www.c3d.org/HTML/Documents/pointrate1.htm); [C3D EVENT:TIMES](https://www.c3d.org/HTML/Documents/eventtimes1.htm); [Qualisys external periodic timebase](https://docs.qualisys.com/qtm/content/system_hardware/using_external_timebase_for_synchronization.htm); [Qualisys external trigger delay](https://docs.qualisys.com/qtm/content/system_hardware/how_to_use_external_trigger.htm). C3D fixed frame rate does not prove external IMU synchronization. Qualisys recommends Sync out because externally triggered starts have a minimum20ms delay. A shared periodic timebase prevents relative capture-clock drift.', '']
    (OUT/'report.md').write_text('\n'.join(report),encoding='utf-8');save('artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
