"""Matched-clock native versus cropped yaw preprocessing, fixed TRAIN folds."""
import json
import numpy as np
import pipeline as p
from projected_yaw_folds_v52 import proxy
from native_projection_v80 import OUT as SENSOR,snap_grid
from audit_fold_routes_v59 import verified_json
from clock_arbitrated_refit_v42 import OLD,NEW,load_cache
from planar_experiment import integrate_planar
from metric_contract_v74 import metrics,self_check
from backfill_metric_contract_v75 import SOURCE,summaries

OUT=p.ROOT/'outputs_native_refit_v81'


def main():
    self_check();OUT.mkdir(exist_ok=False);(OUT/'common_trajectories').mkdir()
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())
    gates=verified_json(SENSOR,'protocol.json')['prospective_gates']
    parents=verified_json(p.ROOT/'outputs_paired_clock_refit_v72','models.json')
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    frozen_metrics=verified_json(p.ROOT/'outputs_metric_contract_v75','trial_metrics.json')
    rows=[dict(r,experiment_id='v81_matched_crop_control') for r in frozen_metrics if r['model'] in ('old_model_old_clock','new_model_new_clock')]
    p.save_json(OUT/'protocol.json',dict(hypothesis='Crop-independent sensor projection improves matched-clock held-person ATE without participant/tail regressions',
        configurations=['native_old_clock','native_new_clock'],weight=1.,cutoff_hz=.3,search=False,gates=gates,
        fitting='Reuse hash-verified v72 fold-only physical calibration: identical raw and labels, so unchanged fit; refit projected yaw scale/intercept from full-sensor projection on original same fold labels',
        controls='Saved v73 old/old and new/new predictions on identical clocks, native C3D support and initial optical pose',
        strict_preprocessing=False,validation_accessed=False,test_accessed=False))
    sensor_manifest=json.loads((SENSOR/'artifact_manifest.json').read_text())['sha256']
    frozen_manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    data={}
    for ident in sorted({r['recording_id'] for r in rows}):
        assert inv[ident]['partition']=='train'
        path=SENSOR/'sensors'/(ident+'.npz');assert p.digest(path)==sensor_manifest[str(path.relative_to(SENSOR))]
        meta=verified_json(SENSOR,str(path.with_suffix('.json').relative_to(SENSOR)))
        with np.load(path) as z:full={k:z[k] for k in z.files}
        old,_=load_cache(OLD,ident,manifests[OLD]);src=OLD if ident in protocol['fallback_old_clock_ids'] else NEW
        new,_=load_cache(src,ident,manifests[src]);data[ident]=(full,meta,old,new)
    fitted={};forward_max=0.
    for fold,pair in parents.items():
        fitted[fold]={};projections={}
        for index,(clock,key) in enumerate([('old','original_clock'),('new','arbitrated_clock')]):
            q=pair[key];cal=q['calibration'];yaw={}
            assert not ({inv[i]['participant'] for i in q['fit_ids']}&{inv[i]['participant'] for i in q['held_ids']})
            for setup,c in cal.items():
                assert set(c['training_trials'])<=set(q['fit_ids'])
                xs=[];ys=[]
                for ident in q['fit_ids']+q['held_ids']:
                    if inv[ident]['setup']!=setup:continue
                    full,meta,*cached=data[ident];projection=proxy(full,c);projections[(clock,ident)]=projection
                    if ident in q['held_ids']:continue
                    d=cached[index];ix=full[clock+'_indices'];mask=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_yaw'])
                    pick=np.flatnonzero(mask)[::5];xs.append(projection[ix[pick]]);ys.append(d['gt_yaw'][pick])
                yaw[setup]=p.robust_line(np.concatenate(xs),np.concatenate(ys))
            fitted[fold][clock]=dict(calibration=cal,yaw=yaw,fit_ids=q['fit_ids'],held_ids=q['held_ids'])
        for ident in pair['original_clock']['held_ids']:
            row=inv[ident];full,meta,old,new=data[ident]
            source=SOURCE/'common_trajectories'/(ident+'.npz');assert p.digest(source)==frozen_manifest[str(source.relative_to(SOURCE))]
            with np.load(source) as z:arrays={k:z[k] for k in ('time_s','native_c3d_time_s','reference_xy_m','reference_heading_rad','reference_valid','imu_valid')};controls={clock:z[name+'_motion'] for clock,name in [('old','old_model_old_clock'),('new','new_model_new_clock')]}
            d=dict(t=arrays['time_s'],gt_xy=arrays['reference_xy_m'],gt_heading=arrays['reference_heading_rad'],gt_valid=arrays['reference_valid'],recording_endpoint_included=False)
            for clock in ('old','new'):
                q=fitted[fold][clock];c=q['calibration'][row['setup']];y=q['yaw'][row['setup']]
                native_motion=np.c_[p.velocities(full,c)[:,0],np.zeros(len(full['t'])),projections[(clock,ident)]*y['scale']+y['intercept']]
                sensor_times=snap_grid(full['t'],arrays['native_c3d_time_s']+meta['offsets'][clock]);support=arrays['imu_valid'];channels=[]
                for j in range(3):
                    values,ok=p.masked_interp(sensor_times,full['t'],native_motion[:,j],full['imu_valid'])
                    assert ok[support].all();channels.append(values)
                motion=np.c_[tuple(channels)];forward_max=max(forward_max,float(np.nanmax(abs(motion[:,0]-controls[clock][:,0]))))
                assert np.nanmax(abs(motion[:,0]-controls[clock][:,0]))<1e-7
                xy,h=integrate_planar(d['t'],motion,d['gt_xy'][0],d['gt_heading'][0],support)
                method='native_'+clock+'_clock';result=metrics(d,xy,h,motion)
                base=next(r for r in rows if r['recording_id']==ident and r['model']==('old_model_old_clock' if clock=='old' else 'new_model_new_clock'))
                assert result['Valid_Frame_Count']==base['Valid_Frame_Count'] and np.array_equal(xy[0],d['gt_xy'][0]) and h[0]==d['gt_heading'][0]
                error=xy[d['gt_valid']]-d['gt_xy'][d['gt_valid']]
                assert abs(result['ATE_RMSE_m']-float(np.sqrt(np.sum(error*error)/len(error))))<1e-12
                rows.append(dict(experiment_id='v81_native_refit',model=method,participant_id=row['participant'],recording_id=ident,maneuver=row['condition'],trial=row['repetition'],split='train_oof_retrospective',**result))
                arrays[method+'_xy_m']=xy;arrays[method+'_heading_rad']=h;arrays[method+'_motion']=motion
            np.savez_compressed(OUT/'common_trajectories'/(ident+'.npz'),**arrays)
        p.save_json(OUT/'models.json',fitted)
        p.save_json(OUT/'checkpoint_metrics.json',rows)
        print('v81 completed fold',fold,flush=True)
    assert len(rows)==828
    p.save_json(OUT/'trial_metrics.json',rows);p.write_csv(OUT/'trial_metrics.csv',rows)
    ss=summaries(rows,('model',));pp=summaries(rows,('model','participant_id'));mm=summaries(rows,('model','maneuver'))
    p.write_csv(OUT/'summary.csv',ss);p.write_csv(OUT/'participant_summary.csv',pp);p.write_csv(OUT/'maneuver_summary.csv',mm)
    decisions=[]
    for clock,control in [('old','old_model_old_clock'),('new','new_model_new_clock')]:
        method='native_'+clock+'_clock';base=next(r for r in ss if r['model']==control);candidate=next(r for r in ss if r['model']==method)
        def ratios(table,key):
            return {r[key]:r['ATE_RMSE_mm']/next(b['ATE_RMSE_mm'] for b in table if b['model']==control and b[key]==r[key]) for r in table if r['model']==method}
        pr,mr=ratios(pp,'participant_id'),ratios(mm,'maneuver')
        tails={k:candidate[k]/base[k] if base[k] else None for k in ['Position_P95_mm','Route_RMSE_mm','Last_Supported_Endpoint_Error_mm','RTE_10s_mm']}
        new_failures={k:sum(r[k]>1000 and next(b[k] for b in rows if b['model']==control and b['recording_id']==r['recording_id'])<=1000 for r in rows if r['model']==method) for k in ['ATE_RMSE_mm','Last_Supported_Endpoint_Error_mm']}
        passes=candidate['ATE_RMSE_mm']<base['ATE_RMSE_mm'] and max(pr.values())<=1.05 and max(mr.values())<=1.05 and max(tails.values())<=1.05 and not any(new_failures.values())
        decisions.append(dict(model=method,control=control,baseline_ATE_mm=base['ATE_RMSE_mm'],candidate_ATE_mm=candidate['ATE_RMSE_mm'],participant_ratios=pr,maneuver_ratios=mr,tail_ratios=tails,new_catastrophic_trials=new_failures,passes_diagnostic_gates=passes,
            decision='diagnostic only; strict evaluator nesting and independent comparison still unresolved' if passes else 'rejected by prespecified matched-control gates'))
    keys=['model','ATE_RMSE_mm','Position_MAE_mm','RMSE_X_mm','RMSE_Y_mm','Last_Supported_Endpoint_Error_mm','RTE_1s_mm','RTE_5s_mm','RTE_10s_mm','Yaw_RMSE_deg','Speed_RMSE_mps','Angular_Velocity_RMSE_degps','Position_P95_mm','Route_RMSE_mm','Path_Length_Error_mm','C3D_Coverage_pct']
    p.save_json(OUT/'run.json',dict(rows=len(rows),trials=207,summary=[{k:r.get(k) for k in keys} for r in ss],decisions=decisions,max_forward_control_difference_mps=forward_max,promotion=False,validation_accessed=False,test_accessed=False,strict_preprocessing=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__),metric_code_sha256=p.digest(p.ROOT/'metric_contract_v74.py')))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
