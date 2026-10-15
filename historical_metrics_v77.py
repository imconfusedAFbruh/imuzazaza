"""Extend sealed historical metrics without fitting or selecting models."""
import csv,json
import numpy as np
import pipeline as p
from metric_contract_v74 import metrics,self_check
from backfill_metric_contract_v75 import summaries

OUT=p.ROOT/'outputs_historical_metrics_v77'


def main():
    self_check();OUT.mkdir(exist_ok=False)
    configs=[('outputs_dynamic_blend_v34','trajectories',['original_v21','selected_blend']),
             ('outputs_clock_arbitrated_v42','common_trajectories',['old_clock_v21','old_clock_blend','new_clock_frozen_v21','new_clock_frozen_blend','new_clock_refit_v21','new_clock_refit_blend']),
             ('outputs_recovered_training_v32','trajectories',['original_v21','stored_endpoints','stored_endpoints_and_rates'])]
    p.save_json(OUT/'protocol.json',dict(hypothesis='Historical ATE reproduces with unchanged support; expanded metrics expose previously unavailable tradeoffs',
        sources=configs,scope='Sealed already-exposed validation artifacts; audit only, no model selection',fitting=False,test_accessed=False,
        endpoint='Conservatively unavailable: acquisition endpoint inclusion not established in saved artifacts',metric_version='v74',budget='one deterministic audit, no parameter search',promotion=False))
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())};rows=[];maximum=0.;provenance=[]
    for source,sub,models in configs:
        folder=p.ROOT/source;manifest=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
        expected=list(csv.DictReader((folder/'common_native_trials.csv').open())) if sub=='common_trajectories' else [dict(r,method=model) for model in models for r in csv.DictReader((folder/(model+'_trials.csv')).open())]
        files=sorted((folder/sub).glob('*.npz'));assert len(files)==71
        for file in files:
            assert p.digest(file)==manifest[str(file.relative_to(folder))];r=inv[file.stem];assert r['partition']=='validation'
            provenance.append(dict(source=source,recording_id=file.stem,path=str(file),sha256=p.digest(file)))
            with np.load(file) as z:
                d=dict(t=z['time_s'],gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'],recording_endpoint_included=False)
                for model in models:
                    xy,h=z[model+'_xy_m'],z[model+'_heading_rad'];m=metrics(d,xy,h,z[model+'_motion'])
                    m['Endpoint_Missing_Reason']='saved artifact does not establish genuine acquisition endpoint inclusion'
                    old=next(q for q in expected if q['id']==file.stem and q['method']==model)
                    mask=d['gt_valid']&np.isfinite(xy).all(1)
                    independent=float(np.sqrt(np.sum((xy[mask]-d['gt_xy'][mask])**2)/mask.sum()))
                    maximum=max(maximum,abs(m['ATE_RMSE_m']-float(old['position_rmse_m'])),abs(m['ATE_RMSE_m']-independent))
                    assert maximum<1e-10 and m['Valid_Frame_Count']==int(old['scored_frames'])
                    rows.append(dict(experiment_id='v77',source=source,model=source+'/'+model,participant_id=r['participant'],recording_id=r['id'],maneuver=r['condition'],trial=r['repetition'],split='historical_exposed_validation_audit',**m))
        print(source,'complete',flush=True)
    assert len(rows)==781
    p.write_csv(OUT/'trial_metrics.csv',rows);p.save_json(OUT/'trial_metrics.json',rows)
    for name,groups in [('summary',('model',)),('maneuver_summary',('model','maneuver')),('participant_summary',('model','participant_id'))]:p.write_csv(OUT/(name+'.csv'),summaries(rows,groups))
    p.save_json(OUT/'source_manifest.json',provenance)
    p.save_json(OUT/'run.json',dict(rows=len(rows),maximum_ATE_difference_m=maximum,promotion=False,test_accessed=False,validation_access='sealed previously exposed predictions, no fitting/selection',summary=[{k:r[k] for k in ('model','ATE_RMSE_mm','Route_RMSE_mm','Last_Supported_Endpoint_Error_mm','RTE_5s_mm','Speed_RMSE_mps')} for r in summaries(rows,('model',))]))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__),metric_code_sha256=p.digest(p.ROOT/'metric_contract_v74.py')))
    print('781 rows independently reproduced; max difference',maximum,flush=True)


if __name__=='__main__':main()
