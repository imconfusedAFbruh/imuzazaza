"""Observed-only peak synchronization and training bootstrap calibration v9."""
import json
import time
from pathlib import Path

import numpy as np
import torch
from scipy import signal

import pipeline as p
from observed_reference_experiment import observed_markers
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from planar_experiment import integrate_planar


def observed_feature(values, mask, hz):
    """Smooth observed segments separately; never fill optical gaps."""
    result = np.full(len(values), np.nan)
    sos = signal.butter(2, 2., fs=hz, output='sos')
    for a, b in p.runs(mask & np.isfinite(values)):
        if b-a >= 20:
            result[a:b] = signal.sosfiltfilt(sos, values[a:b])
    valid = np.isfinite(result)
    if valid.any():
        result[valid] = (result[valid]-np.mean(result[valid]))/max(np.std(result[valid]),1e-8)
    return result, valid


def segment_peaks(values, mask, hz, cfg):
    indices = []
    for a, b in p.runs(mask & np.isfinite(values)):
        found = signal.find_peaks(values[a:b], prominence=cfg['peak_prominence'],
                                 distance=hz*cfg['peak_distance_s'])[0]+a
        indices.extend(found.tolist())
    return np.asarray(indices,dtype=int)


def synchronize_observed(t, raw, imu_valid, gt, cfg, setup=None):
    """Same coarse acceptance gates; observed-segment optical feature smoothing."""
    if gt['derivative_valid'].sum()<100:
        raise p.TrialRejected('reference','Insufficient observed derivative labels',gt.get('diagnostics'))
    terms = cfg['sync_terms'][setup]
    wheel = [raw[:,f['column']]*f['scale']+f['intercept'] for f in terms[:2]]
    c=terms[2]
    choices = [('signed_yaw',raw[:,c['column']]*c['scale']+c['intercept'],gt['yaw']),
               ('calibrated_speed',np.abs((wheel[0]+wheel[1])/2),np.abs(gt['speed']))]
    diagnostics=[]
    for mode, imu, ref in choices:
        mask=gt['derivative_valid'] & np.isfinite(ref)
        if mask.sum()<100 or np.nanstd(ref[mask])<(.025 if 'yaw' in mode else .03):
            diagnostics.append(dict(source=mode,reason='insufficient_motion',valid_frames=int(mask.sum())))
            continue
        a=p.smooth_standard(imu,cfg['hz'])
        b,ref_mask=observed_feature(ref,mask,gt['hz'])
        ap,bp=(np.abs(a),np.abs(b)) if mode=='signed_yaw' else (a,b)
        pi=signal.find_peaks(ap,prominence=cfg['peak_prominence'],distance=cfg['hz']*cfg['peak_distance_s'])[0]
        pi=pi[imu_valid[pi]];pg=segment_peaks(bp,ref_mask,gt['hz'],cfg)
        if min(len(pi),len(pg))<cfg['min_peak_matches']:
            diagnostics.append(dict(source=mode,reason='insufficient_peaks',imu_peaks=len(pi),reference_peaks=len(pg)))
            continue
        pi=pi[np.argsort(ap[pi])[-100:]];pg=pg[np.argsort(bp[pg])[-100:]]
        offsets=(t[pi,None]-gt['t'][pg][None,:]).ravel()
        offsets=offsets[np.abs(offsets)<=cfg['max_lag_s']]
        if not len(offsets):
            continue
        bins=np.unique(np.round(offsets/.025)*.025)
        stride=max(1,round(gt['hz']/20))
        rt,rb,rm=gt['t'][::stride],b[::stride],ref_mask[::stride]
        scores=[]
        for lag in bins:
            query=rt+lag;idx=np.clip(np.searchsorted(t,query),0,len(t)-1)
            ok=rm & imu_valid[idx] & (query>=t[0]) & (query<=t[-1])
            if ok.sum()<60:
                continue
            corr=float(np.corrcoef(np.interp(query[ok],t,a),rb[ok])[0,1])
            residuals=p.match_peaks(t[pi],gt['t'][pg]+lag,cfg['peak_tolerance_s'])
            if np.isfinite(corr) and len(residuals)>=cfg['min_peak_matches']:
                scores.append((corr,float(lag),len(residuals)))
        if not scores:
            continue
        scores.sort(reverse=True);best=scores[0]
        runner=next((s for s in scores[1:] if abs(s[1]-best[1])>.5),None)
        ambiguous=runner is not None and best[0]-runner[0]<cfg['ambiguity_margin']
        if best[0]<cfg['min_sync_corr'] or ambiguous:
            diagnostics.append(dict(source=mode,reason='ambiguous_offset' if ambiguous else 'low_correlation',
                                    best_correlation=best[0],best_offset_s=best[1],matched_peaks=best[2]))
            continue
        lag=best[1];radius=cfg['sync_refinement_radius_s'];step=cfg['sync_refinement_step_s']
        lo,hi=max(-cfg['max_lag_s'],lag-radius),min(cfg['max_lag_s'],lag+radius)
        lower=np.clip(np.searchsorted(t,gt['t']+lo)-1,0,len(t)-1)
        upper=np.clip(np.searchsorted(t,gt['t']+hi),0,len(t)-1)
        bad=np.r_[0,np.cumsum(~imu_valid)]
        valid=ref_mask & (gt['t']+lo>=t[0]) & (gt['t']+hi<=t[-1]) & (bad[upper+1]==bad[lower])
        result=dict(offset_s=lag,correlation=best[0],matched_peaks=best[2],source=mode,
                    runner_up_correlation=runner[0] if runner else None,search_diagnostics=diagnostics,
                    observed_reference_peaks=len(pg),observed_feature_frames=int(ref_mask.sum()),
                    coarse_offset_s=lag,refinement_step_s=step,refinement_radius_s=radius,
                    refinement_frames=int(valid.sum()),reference_smoothing='separate observed derivative segments')
        residuals=p.match_peaks(t[pi],gt['t'][pg]+lag,cfg['peak_tolerance_s'])
        result['peak_timing_median_abs_s']=float(np.median(np.abs(residuals)))
        if valid.sum()<3*gt['hz']:
            return dict(result,refinement_status='kept_coarse_insufficient_common_support')
        rt,rb=gt['t'][valid],b[valid]
        def score(offset):
            rs=p.match_peaks(t[pi],gt['t'][pg]+offset,cfg['peak_tolerance_s'])
            corr=float(np.corrcoef(np.interp(rt+offset,t,a),rb)[0,1])
            return (corr,rs) if len(rs)>=cfg['min_peak_matches'] and np.isfinite(corr) else (-np.inf,[])
        initial,_=score(lag);best_lag,best_corr=lag,initial;evaluations=1
        for grid_step,center,width in ((.001,lag,radius),(step,None,.001)):
            center=best_lag if center is None else center
            grid=np.arange(np.ceil(max(lo,center-width)/grid_step),np.floor(min(hi,center+width)/grid_step)+1)*grid_step
            for candidate in grid:
                corr,_=score(float(candidate));evaluations+=1
                if corr>best_corr:
                    best_lag,best_corr=float(candidate),corr
        if best_corr<cfg['min_sync_corr'] or not np.isfinite(best_corr):
            return dict(result,refinement_status='kept_coarse_full_rate_gate',refinement_evaluations=evaluations)
        _,residuals=score(best_lag)
        return dict(result,offset_s=best_lag,correlation=best_corr,matched_peaks=len(residuals),
                    peak_timing_median_abs_s=float(np.median(np.abs(residuals))),
                    coarse_full_rate_correlation=initial,refinement_delta_s=best_lag-lag,
                    refinement_evaluations=evaluations,refinement_status='refined')
    raise p.TrialRejected('synchronization','No accepted unique observed peak alignment',dict(channels=diagnostics))


def common_score(row, old, oldmeta, new, newmeta, gt, predict, old_cal, new_cal, cfg):
    """Score native optical timestamps; both paths share one observed initial pose."""
    oldlag,newlag=[m['synchronization']['offset_s'] for m in (oldmeta,newmeta)]
    offsets=[d['ref_t'][0]+lag for d,lag in ((old,oldlag),(new,newlag))]
    lo=max(old['ref_t'][0],new['ref_t'][0]);hi=min(old['ref_t'][-1],new['ref_t'][-1])
    native=np.flatnonzero((gt['t']>=lo)&(gt['t']<=hi))
    if len(native)<20:
        raise ValueError('Too little common clock overlap')
    oldmotion,newmotion=predict(old),predict(new)
    motions={'ridge_control':(old,oldlag,offsets[0],oldmotion),
             'ridge_observed_alignment':(new,newlag,offsets[1],newmotion),
             'physics_bootstrap_alignment':(new,newlag,offsets[1],np.c_[p.velocities(new,old_cal[row['setup']])[:,0],np.zeros(len(new['t'])),p.velocities(new,old_cal[row['setup']])[:,1]]),
             'physics_refit_alignment':(new,newlag,offsets[1],np.c_[p.velocities(new,new_cal[row['setup']])[:,0],np.zeros(len(new['t'])),p.velocities(new,new_cal[row['setup']])[:,1]])}
    rt=gt['t'][native]; sampled={};imu=np.ones(len(native),bool)
    for name,(data,lag,absolute_start,motion) in motions.items():
        query=rt+lag-absolute_start
        channels=[]
        for column in range(3):
            values,valid=p.masked_interp(query,data['t'],motion[:,column],data['imu_valid'])
            channels.append(values);imu &= valid
        sampled[name]=np.c_[tuple(channels)]
    observed=gt['valid'][native]
    first=np.flatnonzero(observed & imu)
    if not len(first):
        raise ValueError('No common observed initial pose')
    start=int(first[0]);native=native[start:];rt=rt[start:];imu=imu[start:];observed=observed[start:]
    data=dict(t=rt-rt[0],gt_xy=gt['xy'][native],gt_heading=gt['heading'][native],gt_valid=observed,imu_valid=imu)
    records={}
    for name,motion in sampled.items():
        xy,heading=integrate_planar(data['t'],motion[start:],data['gt_xy'][0],data['gt_heading'][0],imu)
        records[name]=dict(id=row['id'],participant=row['participant'],condition=row['condition'],
                           **p.metrics(data,xy,heading,cfg))
    if len({r['scored_frames'] for r in records.values()})!=1:
        raise RuntimeError('Common score masks differ')
    return records,dict(id=row['id'],common_initial_c3d_s=float(rt[0]),common_last_c3d_s=float(rt[-1]),
                         common_observed_frames=int(observed.sum()),common_scored_frames=records['ridge_control']['scored_frames'],
                         common_total_frames=len(rt),reference_interpolated=False,initial_pose_shared=True)


def main():
    started=time.perf_counter();torch.set_num_threads(4)
    source,out=p.ROOT/'outputs_observed_reference_v7',p.ROOT/'outputs_observed_sync_v9'
    if out.exists():
        raise RuntimeError('Preserve existing run')
    manifest=json.loads((source/'artifact_manifest.json').read_text());run=json.loads((source/'run.json').read_text())
    for name,sha in manifest['sha256'].items():
        if p.digest(source/name)!=sha:raise RuntimeError(f'Observed source changed: {name}')
    for name,sha in run['provenance'].items():
        if p.digest(p.ROOT/name)!=sha:raise RuntimeError(f'Observed dependency changed: {name}')
    oldcfg=run['settings'];training=list(observed_rows(source,oldcfg,'train',manifest))
    bootstrap=p.calibrate(training,oldcfg)
    cfg=dict(oldcfg,sync_terms={setup:cal['terms'] for setup,cal in bootstrap.items()},
             reference_protocol='v9 observed-only bootstrap calibration and peak alignment',
             synchronization_protocol='unchanged coarse gates; no-gap optical smoothing; fixed-support native local refinement')
    out.mkdir();p.save_json(out/'bootstrap_calibration.json',bootstrap)
    accepted_train=[];accepted_val=[];old_val={};qc=[];alignment=[]
    old_read,old_sync=p.read_markers,p.synchronize
    train_people=set()
    try:
        p.read_markers=observed_markers;p.synchronize=synchronize_observed
        for partition in ('train','validation'):
            originals=training if partition=='train' else observed_rows(source,oldcfg,partition,manifest)
            for row,old,oldmeta in originals:
                if partition=='train':train_people.add(row['participant'])
                elif row['participant'] in train_people:raise RuntimeError('Participant overlap')
                record={k:row[k] for k in ('id','partition','participant','condition')}
                try:
                    data,meta=p.prepare(row,p.ROOT,out,cfg)
                    record.update(status='accepted',old_offset_s=oldmeta['synchronization']['offset_s'],
                         new_offset_s=meta['synchronization']['offset_s'],offset_delta_s=meta['synchronization']['offset_s']-oldmeta['synchronization']['offset_s'],
                         old_observed_frames=int(old['gt_valid'].sum()),new_observed_frames=int(data['gt_valid'].sum()))
                    alignment.append(dict(record,old=oldmeta['synchronization'],new=meta['synchronization']))
                    if partition=='train':accepted_train.append((row,data,meta))
                    else:
                        accepted_val.append((row,data,meta));old_val[row['id']]=(old,oldmeta)
                except p.TrialRejected as error:
                    record.update(status='excluded',stage=error.stage,reason=str(error),diagnostics=error.diagnostics)
                except ValueError as error:
                    if str(error) not in ('Insufficient valid derivative labels','No valid initial reference pose'):raise
                    record.update(status='excluded',stage='reference',reason=str(error))
                qc.append(record)
                if len(qc)%50==0:print(f'{len(qc)} aligned: {len(accepted_train)} train/{len(accepted_val)} validation',flush=True)
    finally:
        p.read_markers=old_read;p.synchronize=old_sync
    newcal=p.calibrate(accepted_train,cfg);p.save_json(out/'calibration.json',newcal)
    predict=load_observed_ridge();results={name:[] for name in ('ridge_control','ridge_observed_alignment','physics_bootstrap_alignment','physics_refit_alignment')}
    common=[];full=[];common_failures=[]
    try:
        p.read_markers=observed_markers
        for row,data,meta in accepted_val:
            motion=predict(data)
            xy,heading=integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
            full.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**p.metrics(data,xy,heading,cfg)))
            gt=p.reference(p.ROOT/row['c3d'],cfg,row['setup']);old,oldmeta=old_val[row['id']]
            try:
                records,coverage=common_score(row,old,oldmeta,data,meta,gt,predict,bootstrap,newcal,cfg)
                for name,record in records.items():results[name].append(record)
                common.append(coverage)
            except ValueError as error:
                common_failures.append(dict(id=row['id'],reason=str(error)))
    finally:p.read_markers=old_read
    summaries={}
    for name,records in list(results.items())+[('ridge_new_full_overlap',full)]:
        summary,people,conditions=p.summarize(records);summaries[name]=summary
        for suffix,items in [('trials',records),('participants',people),('maneuvers',conditions)]:p.write_csv(out/f'{name}_{suffix}.csv',items)
        print(f'{name}: {summary["equal_participant_mean_position_rmse_m"]*1000:.3f} mm ({len(records)} trials)',flush=True)
    p.write_csv(out/'qc.csv',[{k:v for k,v in r.items() if k!='diagnostics'} for r in qc]);p.save_json(out/'qc_diagnostics.json',qc)
    p.save_json(out/'alignment.json',alignment);p.save_json(out/'common_coverage.json',dict(records=common,failures=common_failures))
    files=[Path(__file__),source/'artifact_manifest.json',p.ROOT/'observed_ridge_inference.py',p.ROOT/'observed_training_experiment.py',
           p.ROOT/'observed_reference_experiment.py',p.ROOT/'outputs_observed_ridge_v8/artifact_manifest.json',
           out/'bootstrap_calibration.json',out/'calibration.json']
    provenance=dict(run['provenance'],**{str(f.relative_to(p.ROOT)):p.digest(f) for f in files})
    p.save_json(out/'run.json',dict(settings=cfg,training_trials=len(accepted_train),validation_trials=len(accepted_val),
         test_evaluated=False,provenance=provenance,scope='Previously v7 accepted development recordings; unchanged peak gates; optical gaps not filled',
         scoring='Native C3D timestamps, shared observed initial pose, matched observation and reconstruction masks; separate changed-overlap coverage'))
    deltas=[r['offset_delta_s'] for r in qc if r['partition']=='validation' and r['status']=='accepted']
    p.save_json(out/'comparison.json',dict(candidates=summaries,test_evaluated=False,common_failures=common_failures,
        original_v8_control_rmse_m=.11689783228546191,validation_median_absolute_clock_change_ms=float(np.median(np.abs(deltas))*1000),
        runtime_seconds=time.perf_counter()-started,calibration_effect='physics bootstrap vs refit on identical new clocks/common timestamps',
        caveat='Alignment diagnostics do not establish actual timing accuracy. Reused validation is exploratory.'))
    lines=['# Observed-only synchronization and calibration v9','',
        f'Bootstrap: 473 camera-supported training recordings. Accepted after observed-only alignment: {len(accepted_train)} training / {len(accepted_val)} validation out of 473 / 71. No test signals opened.','',
        'Coarse correlation, unique chronological peak matches and ambiguity gates retain their frozen thresholds. Optical feature smoothing runs separately within observed derivative segments. Native refinement searches at 1 ms then 0.1 ms within 25 ms of the accepted coarse basin; position error never selects clocks.','',
        'The historical full v8 ridge control is 116.898 mm. The matched comparison below uses exact native optical timestamps and one identical observed initial pose for every method. No optical interpolation, fitted rotation or optical resets. Changes in accepted recordings and overlap are reported separately.','',
        '| Candidate | RMSE (mm) | Recordings |','|---|---:|---:|']
    lines += [f'| {name} | {s["equal_participant_mean_position_rmse_m"]*1000:.3f} | {s["trials"]} |' for name,s in summaries.items()]
    lines += ['',f'Median absolute validation clock adjustment: {np.median(np.abs(deltas))*1000:.3f} ms. Clock grid resolution and correlation/peak residuals are not independent timing accuracy measurements.',
        '', 'Physics bootstrap versus physics refit isolates training calibration changes under the same new alignment. Frozen ridge parameters retain their original physical calibration; no normalization or model weights were refitted for this clock experiment. Coverage, ambiguity/exclusion details, participant and maneuver tables, sealed caches and training calibration artifacts accompany this report. Reused validation remains exploratory.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    p.save_json(out/'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):p.digest(f) for f in out.rglob('*') if f.is_file()}))


if __name__=='__main__':main()
