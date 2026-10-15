"""Rescore v73's four frozen TRAIN prediction cells under v74; no fits."""
import csv
import json
import numpy as np
import pipeline as p
from metric_contract_v74 import metrics,balanced,self_check
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_metric_contract_v75'
SOURCE=p.ROOT/'outputs_clock_calibration_decomposition_v73'


def summaries(rows,groups):
    result=[]
    for values in sorted({tuple(r[k] for k in groups) for r in rows}):
        members=[r for r in rows if tuple(r[k] for k in groups)==values]
        item=dict(zip(groups,values),Participants=len({r['participant_id'] for r in members}),Trials=len(members),
            Failure_Flagged_Trials=sum(bool(r['Failure_Flags']) for r in members),True_Endpoint_Eligible_Trials=sum(r['Endpoint_Supported'] for r in members))
        numeric={key for r in members for key,value in r.items() if value is None or (isinstance(value,(int,float)) and not isinstance(value,bool))}
        for key in sorted(numeric):
            if key in ('trial',):continue
            item[key]=balanced(members,key)
            x=[r[key] for r in members if isinstance(r.get(key),(int,float)) and not isinstance(r[key],bool)]
            item[key+'_Eligible_Trials']=len(x)
            item[key+'_Eligible_Participants']=len({r['participant_id'] for r in members if r.get(key) is not None and isinstance(r[key],(int,float))})
            item[key+'_Trial_SD']=float(np.std(x,ddof=1)) if len(x)>1 else None
            item[key+'_Trial_Median']=float(np.median(x)) if x else None
            item[key+'_Trial_IQR']=float(np.percentile(x,75)-np.percentile(x,25)) if x else None
        result.append(item)
    return result


def main():
    self_check()
    resume=(OUT/'trial_metrics.json').exists()
    if not resume:OUT.mkdir(exist_ok=False)
    parent=verified_json(SOURCE,'run.json');manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    previous=list(csv.DictReader((SOURCE/'trials.csv').open()))
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    methods=sorted({r['method'] for r in previous})
    p.save_json(OUT/'protocol.json',dict(hypothesis='Complete metrics reveal tail/endpoint/velocity tradeoffs concealed by ATE alone',models=methods,
        source=str(SOURCE),new_fitting=False,metric_version='v74',primary_aggregation='Arithmetic mean of participant means of trial ATE RMSE; no frame pooling',
        secondary_aggregation='Same hierarchy over available trials; eligible trials/people reported; SD/median/IQR descriptive trial distribution',
        uncertainty='Participant paired descriptive differences; repeated folds/historical exposure preclude independent frame confidence intervals',
        endpoint='Genuine original C3D acquisition final sample must be included and scored; otherwise separately labelled last-supported',
        rte='1/5/10s every1s on contiguous matched support; rotate BOTH displacement vectors with reference start heading',
        velocity='Horizontal speed magnitude from saved model local forward/lateral motion versus reference XY gradient then6Hz Butterworth2, per-run0.15s edge exclusion',
        loa='Per-trial descriptive correlated-frame LoA; no inferential confidence intervals',validation_accessed=False,test_accessed=False))
    rows=json.loads((OUT/'trial_metrics.json').read_text()) if resume else [];maximum=0.
    for count,ident in enumerate([] if resume else sorted({r['id'] for r in previous}),1):
        row=inv[ident];assert row['partition']=='train'
        path=SOURCE/'common_trajectories'/(ident+'.npz');assert p.digest(path)==manifest[str(path.relative_to(SOURCE))]
        original=p.ezc3d.c3d(str(p.ROOT/row['c3d'])); hz=float(original['header']['points']['frame_rate'])
        end=(original['data']['points'].shape[2]-1)/hz
        with np.load(path) as z:
            d=dict(t=z['time_s'],gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'],
                recording_endpoint_included=bool(abs(float(z['native_c3d_time_s'][-1])-end)<1e-8))
            counts=[]
            for method in methods:
                result=metrics(d,z[method+'_xy_m'],z[method+'_heading_rad'],z[method+'_motion'])
                expected=next(r for r in previous if r['id']==ident and r['method']==method)
                diff=abs(result['ATE_RMSE_m']-float(expected['position_rmse_m']));maximum=max(maximum,diff)
                assert diff<1e-10 and result['Valid_Frame_Count']==int(expected['scored_frames'])
                counts.append(result['Valid_Frame_Count'])
                rows.append(dict(experiment_id='v75_metric_backfill',model=method,participant_id=row['participant'],recording_id=ident,
                    maneuver=row['condition'],trial=row['repetition'],split='train_oof_retrospective',**result))
            assert len(set(counts))==1
        if count%25==0:print(count,flush=True)
    assert len(rows)==828
    if resume:
        for row in rows:
            expected=next(r for r in previous if r['id']==row['recording_id'] and r['method']==row['model'])
            diff=abs(row['ATE_RMSE_m']-float(expected['position_rmse_m']));maximum=max(maximum,diff)
            assert diff<1e-10 and row['Valid_Frame_Count']==int(expected['scored_frames'])
    p.write_csv(OUT/'trial_metrics.csv',rows);p.save_json(OUT/'trial_metrics.json',rows)
    summary=summaries(rows,('model',));p.write_csv(OUT/'summary.csv',summary)
    p.write_csv(OUT/'maneuver_summary.csv',summaries(rows,('model','maneuver')))
    people=summaries(rows,('model','participant_id'));p.write_csv(OUT/'participant_summary.csv',people)
    for s in summary:assert abs(s['ATE_RMSE_m']-parent['summary'][s['model']]['equal_participant_mean_position_rmse_m'])<1e-10
    baseline=next(r for r in summary if r['model']=='old_model_old_clock');dashboard=[]
    keys=['ATE_RMSE_mm','Position_MAE_mm','RMSE_X_mm','RMSE_Y_mm','Endpoint_Error_mm','Endpoint_Drift_pct','Last_Supported_Endpoint_Error_mm','Last_Supported_Normalized_Endpoint_pct','RTE_1s_mm','RTE_5s_mm','RTE_10s_mm','Yaw_RMSE_deg','Speed_RMSE_mps','Angular_Velocity_RMSE_degps','Position_P95_mm','Route_RMSE_mm','Route_P95_mm','Sampled_Hausdorff_mm','Maximum_Run_Frechet_mm','Within_Run_Arc_Length_RMSE_mm','Path_Length_Error_mm','C3D_Coverage_pct','Failure_Flagged_Trials']
    for candidate in summary:
        if candidate['model']==baseline['model']:continue
        for key in keys:
            a,b=baseline.get(key),candidate.get(key)
            dashboard.append(dict(model=candidate['model'],Metric=key,Baseline=a,Candidate=b,Change=b-a if a is not None and b is not None else None,
                Decision='historical rejected comparison; no new promotion',Baseline_Eligible_Trials=baseline.get(key+'_Eligible_Trials',len(rows)//4),Candidate_Eligible_Trials=candidate.get(key+'_Eligible_Trials',len(rows)//4)))
    p.write_csv(OUT/'dashboard.csv',dashboard)
    paired=[]
    for r in people:
        b=next(s for s in people if s['model']==baseline['model'] and s['participant_id']==r['participant_id'])
        paired.append(dict(model=r['model'],participant_id=r['participant_id'],ATE_Difference_mm=r['ATE_RMSE_mm']-b['ATE_RMSE_mm'],ATE_Ratio=r['ATE_RMSE_mm']/b['ATE_RMSE_mm']))
    p.write_csv(OUT/'paired_participant_differences.csv',paired)
    p.save_json(OUT/'run.json',dict(rows=len(rows),trials=207,models=4,maximum_historical_ATE_difference_m=maximum,
        true_endpoint_eligible_recordings=sum(r['Endpoint_Supported'] for r in rows if r['model']==baseline['model']),
        summary=[{key:s.get(key) for key in ['model']+keys} for s in summary],promotion=False,test_accessed=False,validation_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__),metric_code_sha256=p.digest(p.ROOT/'metric_contract_v74.py')))
    print(json.dumps(dict(rows=len(rows),maximum_ATE_difference=maximum,summary=[{k:s[k] for k in ['model','ATE_RMSE_mm','Speed_RMSE_mps','Angular_Velocity_RMSE_degps']} for s in summary]),indent=2))


if __name__=='__main__':main()
