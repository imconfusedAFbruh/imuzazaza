"""Backfill existing failed-candidate arrays; never regenerate missing models."""
import csv,json
import numpy as np
import pipeline as p
from metric_contract_v74 import metrics,self_check
from backfill_metric_contract_v75 import summaries
from basin_completeness_v91 import verify

OUT=p.ROOT/'outputs_failed_metrics_v95'
DOC=p.ROOT/'research_docs/consistency_backfill_v94_v96.md'
SOURCES=('outputs_combined_physics_v58','outputs_interval_speed_v60','outputs_disagreement_uncertainty_v61',
         'outputs_tilt_safe_speed_v62','outputs_train_error_budget_v63','outputs_wheel_products_v64')


def predictions(z):
    if 'xy' in z.files:return [('baseline',z['xy'],z['heading'],z['motion'])]
    return [(k[:-3],z[k],z[k[:-3]+'_heading'],None) for k in z.files if k.endswith('_xy') and k!='reference_xy']


def main():
    self_check();assert not (p.ROOT/'research_state/STOP').exists()
    assert not (OUT/'run.json').exists(),'Completed output is immutable'
    OUT.mkdir(exist_ok=True)
    source_hashes=sum(verify(p.ROOT/s) for s in SOURCES)
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    state=OUT/'checkpoint.json'
    if state.exists():
        saved=json.loads(state.read_text());assert saved['source_sha256']==p.digest(__file__)
        rows=saved['rows'];completed=set(saved['completed'])
    else:rows=[];completed=set()
    p.save_json(OUT/'protocol.json',dict(preregistration_sha256=p.digest(DOC),source_hashes_verified=source_hashes,
        metric_version='v74',fitting=False,selection=False,endpoints='unavailable: no saved acquisition endpoint proof',
        motion='saved motion only; missing stays null',validation_accessed=False,test_accessed=False))
    availability=[];provenance=[];maximum=0.
    for source in SOURCES:
        folder=p.ROOT/source;files=sorted((folder/'trajectories').glob('*.npz'))
        previous=list(csv.DictReader((folder/'trials.csv').open())) if (folder/'trials.csv').exists() else []
        if 'v58' in source:
            expected={(r['id'],'gain_'+format(float(r['gain']),'g')):r for r in previous}
        elif 'v60' in source:expected={(r['id'],r['method']):r for r in previous}
        elif 'v62' in source or 'v64' in source:expected={(r['id'],r['candidate']):r for r in previous}
        else:expected={}
        available=set()
        for file in files:
            ident=file.stem.rsplit('__',1)[0] if 'v60' in source else file.stem
            r=inv[ident];assert r['partition']=='train'
            provenance.append(dict(source=source,file=str(file.relative_to(p.ROOT)),sha256=p.digest(file)))
            token=source+'/'+file.name
            with np.load(file) as z:
                models=predictions(z);available.update((ident,name) for name,*_ in models)
                if token in completed:continue
                d=dict(t=z['t'],gt_xy=z['reference_xy'],gt_heading=z['reference_heading'],
                    gt_valid=z['valid'] if 'valid' in z.files else z['reference_valid'],recording_endpoint_included=False)
                masks=[]
                for name,xy,h,motion in models:
                    m=metrics(d,xy,h,motion);old=expected[(ident,name)]
                    mask=d['gt_valid']&np.isfinite(xy).all(1);masks.append(mask)
                    direct=float(np.sqrt(np.sum((xy[mask]-d['gt_xy'][mask])**2)/mask.sum()))
                    diff=max(abs(m['ATE_RMSE_m']-float(old['position_rmse_m'])),abs(m['ATE_RMSE_m']-direct));maximum=max(maximum,diff)
                    assert diff<1e-10 and m['Valid_Frame_Count']==int(old['scored_frames'])
                    assert m['Endpoint_Error_mm'] is None
                    if motion is None:assert m['Speed_RMSE_mps'] is None and m['Angular_Velocity_RMSE_degps'] is None
                    rows.append(dict(experiment_id='v95',source=source,model=source+'/'+name,participant_id=r['participant'],
                        recording_id=ident,maneuver=r['condition'],trial=r['repetition'],split='train_oof_retrospective',motion_available=motion is not None,
                        historical_ATE_difference_m=diff,**m))
                assert all(np.array_equal(masks[0],mask) for mask in masks)
            completed.add(token)
            if len(completed)%10==0:
                temp=state.with_suffix('.tmp');p.save_json(temp,dict(source_sha256=p.digest(__file__),completed=sorted(completed),rows=rows));temp.replace(state)
                print('v95 checkpoint',len(completed),'files',len(rows),'rows',flush=True)
        missing=set(expected)-available
        availability.append(dict(source=source,saved_files=len(files),available_model_trials=len(available),historical_model_trials=len(expected),
            missing_prediction_trials=len(missing),missing_models=sorted({name for _,name in missing}),
            reason='No saved trajectories; no regeneration authorized' if not files else 'Missing models remain unavailable' if missing else 'All saved position/heading candidates scored',
            motion_available='v60' in source))
    assert len(rows)==2898
    maximum=max(r['historical_ATE_difference_m'] for r in rows)
    p.save_json(OUT/'trial_metrics.json',rows);p.write_csv(OUT/'trial_metrics.csv',rows)
    for name,groups in [('summary',('model',)),('participant_summary',('model','participant_id')),('maneuver_summary',('model','maneuver'))]:p.write_csv(OUT/(name+'.csv'),summaries(rows,groups))
    p.save_json(OUT/'availability.json',availability);p.save_json(OUT/'source_manifest.json',provenance)
    p.save_json(OUT/'run.json',dict(rows=len(rows),models=len({r['model'] for r in rows}),trials=207,
        maximum_historical_ATE_difference_m=maximum,true_endpoint_eligible=0,motion_available_rows=sum(r['motion_available'] for r in rows),
        unavailable_prediction_models='v60 four nonzero candidates; v61 all; v63 all',promotion=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},
        source_sha256=p.digest(__file__),metric_code_sha256=p.digest(p.ROOT/'metric_contract_v74.py')))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
