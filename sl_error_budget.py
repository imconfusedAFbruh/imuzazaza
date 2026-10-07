"""SL-only diagnostic for the next experiment; no deployable oracle or tuning."""
import json
from pathlib import Path

import numpy as np
import torch

from pipeline import ROOT, digest, metrics, summarize, save_json, write_csv
from planar_experiment import integrate_planar, lateral_labels
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge


def main():
    source,out=ROOT/'outputs_observed_reference_v7',ROOT/'outputs_sl_error_budget_v9'
    if out.exists():raise RuntimeError('Preserve existing diagnostic')
    cfg=json.loads((source/'run.json').read_text())['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    torch.set_num_threads(4);predict=load_observed_ridge();out.mkdir()
    groups={name:[] for name in ('selected','oracle_forward_on_valid_labels','oracle_lateral_on_valid_labels',
                'oracle_yaw_on_valid_labels','oracle_all_on_valid_labels')}
    diagnostic=[]
    for row,data,_ in observed_rows(source,cfg,'validation',manifest):
        if row['condition']!='SL':continue
        motion=predict(data)
        lateral,lateral_valid=lateral_labels(data)
        truth=np.c_[data['gt_v'],lateral,data['gt_yaw']]
        label_mask=data['label_valid']&lateral_valid&np.isfinite(truth).all(axis=1)
        scores={}
        for name,channels in [('selected',()),('oracle_forward_on_valid_labels',(0,)),
                             ('oracle_lateral_on_valid_labels',(1,)),('oracle_yaw_on_valid_labels',(2,)),
                             ('oracle_all_on_valid_labels',(0,1,2))]:
            candidate=motion.copy()
            for channel in channels:candidate[label_mask,channel]=truth[label_mask,channel]
            xy,heading=integrate_planar(data['t'],candidate,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
            score=metrics(data,xy,heading,cfg)
            groups[name].append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**score))
            scores[name]=score['position_rmse_m']
            if name=='selected':base_xy,base_heading,base_score=xy,heading,score
        mask=data['gt_valid']&np.isfinite(base_xy).all(axis=1)
        angle_error=np.arctan2(np.sin(base_heading[mask]-data['gt_heading'][mask]),np.cos(base_heading[mask]-data['gt_heading'][mask]))
        slope=np.polyfit(data['t'][mask],angle_error,1)[0]
        rate_error=motion[label_mask]-truth[label_mask]
        end=np.flatnonzero(mask)[-1]
        diagnostic.append(dict(id=row['id'],participant=row['participant'],duration_s=float(data['t'][-1]),
             observed_fraction=float(data['gt_valid'].mean()),oracle_label_fraction=float(label_mask.mean()),
             heading_error_linear_trend_deg_s=float(np.rad2deg(slope)),
             final_observed_heading_error_deg=float(np.rad2deg(angle_error[-1])),
             final_observed_position_error_m=float(np.linalg.norm(base_xy[end]-data['gt_xy'][end])),
             forward_bias_mps=float(np.mean(rate_error[:,0])),forward_rmse_mps=float(np.sqrt(np.mean(rate_error[:,0]**2))),
             lateral_bias_mps=float(np.mean(rate_error[:,1])),lateral_rmse_mps=float(np.sqrt(np.mean(rate_error[:,1]**2))),
             yaw_bias_deg_s=float(np.rad2deg(np.mean(rate_error[:,2]))),yaw_rmse_deg_s=float(np.rad2deg(np.sqrt(np.mean(rate_error[:,2]**2)))),
             whole_rmse_m=base_score['position_rmse_m'],relative_1m_rmse_m=base_score['relative_1m_rmse_m'],
             relative_1m_segments=base_score['relative_1m_segments'],oracle_scores=scores))
    summary={name:summarize(rows)[0] for name,rows in groups.items()}
    save_json(out/'diagnostics.json',dict(summary=summary,trials=diagnostic,test_evaluated=False,
         interpretation='Non-deployable partial-label oracles replace channels only on valid observed derivative/lateral labels. '
                        'All candidates retain predicted motion elsewhere and share the full observed scoring frames and original initial pose. '
                        'This is sensitivity to available reference channels, not a physical accuracy floor or an achievable model.',
         provenance={str(f.relative_to(ROOT)):digest(f) for f in [Path(__file__),source/'artifact_manifest.json',
             ROOT/'outputs_observed_ridge_v8/selection.json',ROOT/'observed_ridge_inference.py']}))
    write_csv(out/'trials.csv',[{k:v for k,v in r.items() if k!='oracle_scores'} for r in diagnostic])
    print(json.dumps(dict(summary=summary,median_oracle_label_fraction=float(np.median([r['oracle_label_fraction'] for r in diagnostic])),
       median_duration_s=float(np.median([r['duration_s'] for r in diagnostic])),
       median_heading_trend_abs_deg_s=float(np.median([abs(r['heading_error_linear_trend_deg_s']) for r in diagnostic])),
       median_relative_1m_rmse_m=float(np.median([r['relative_1m_rmse_m'] for r in diagnostic if r['relative_1m_rmse_m']!=''])),
       median_final_observed_error_m=float(np.median([r['final_observed_position_error_m'] for r in diagnostic]))),indent=2))


if __name__=='__main__':main()
