"""Image-led SL channel diagnosis; no fitting or test access."""
import json
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,save_json,write_csv,metrics,summarize,digest
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from long_horizon_inference import load_endpoint_ensemble
from planar_experiment import lateral_labels,integrate_planar

def main():
    out=ROOT/'outputs_trajectory_image_diagnosis_extended_v10'
    if out.exists(): raise RuntimeError('Preserve completed diagnosis')
    out.mkdir();torch.set_num_threads(4)
    source=ROOT/'outputs_observed_reference_v7'
    cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text())
    predictors={'ridge':load_observed_ridge(),'endpoint':load_endpoint_ensemble()}
    diagnostics=[];scores=[]
    for partition in ('train','validation'):
        for row,data,_ in observed_rows(source,cfg,partition,manifest):
            if row['condition']!='SL' or row['date'] not in ('2026-09-24','2026-09-25'):continue
            sensor={k:data[k] for k in ('setup','t','raw','imu_valid')}
            motion={k:p(sensor) for k,p in predictors.items()}
            lat,lv=lateral_labels(data);truth=np.c_[data['gt_v'],lat,data['gt_yaw']]
            label=data['label_valid']&lv&np.isfinite(truth).all(1)
            variants=dict(motion)
            for name,channels in [('endpoint_forward',(0,)),('endpoint_lateral',(1,)),('endpoint_yaw',(2,)),('endpoint_forward_yaw',(0,2))]:
                variants[name]=motion['ridge'].copy();variants[name][:,channels]=motion['endpoint'][:,channels]
            for name,m in variants.items():
                xy,h=integrate_planar(data['t'],m,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
                score=metrics(data,xy,h,cfg)
                scores.append(dict(id=row['id'],date=row['date'],participant=row['participant'],partition=partition,condition='SL',model=name,**score))
                if name not in predictors:continue
                pose=data['gt_valid']&np.isfinite(xy).all(1);t=data['t'][pose]
                he=np.arctan2(np.sin(h[pose]-data['gt_heading'][pose]),np.cos(h[pose]-data['gt_heading'][pose]));err=np.linalg.norm(xy[pose]-data['gt_xy'][pose],axis=1)
                rate=m[label]-truth[label]
                delta=motion['endpoint'][:,2]-motion['ridge'][:,2]
                dt=np.diff(data['t']);mid=(delta[:-1]+delta[1:])/2
                supported=label[:-1]&label[1:]
                diagnostics.append(dict(id=row['id'],date=row['date'],participant=row['participant'],partition=partition,model=name,pose_support=float(pose.mean()),derivative_support=float(label.mean()),forward_bias_mps=float(rate[:,0].mean()),forward_rmse_mps=float(np.sqrt(np.mean(rate[:,0]**2))),lateral_bias_mps=float(rate[:,1].mean()),yaw_bias_deg_s=float(np.rad2deg(rate[:,2].mean())),yaw_rmse_deg_s=float(np.rad2deg(np.sqrt(np.mean(rate[:,2]**2)))),heading_trend_deg_s=float(np.rad2deg(np.polyfit(t,he,1)[0])),first_third_rmse_m=float(np.sqrt(np.mean(err[t<=t[0]+(t[-1]-t[0])/3]**2))),last_third_rmse_m=float(np.sqrt(np.mean(err[t>=t[0]+2*(t[-1]-t[0])/3]**2))),last_heading_error_deg=float(np.rad2deg(he[-1])),endpoint_minus_ridge_yaw_integral_supported_deg=float(np.rad2deg(np.sum((mid*dt)[supported]))),endpoint_minus_ridge_yaw_integral_unsupported_deg=float(np.rad2deg(np.sum((mid*dt)[~supported])))))
    write_csv(out/'diagnostics.csv',diagnostics);write_csv(out/'channel_variants.csv',scores)
    groups=[]
    for partition in ('train','validation'):
        for date in ('2026-09-24','2026-09-25'):
            for name in variants:
                rows=[r for r in scores if r['partition']==partition and r['date']==date and r['model']==name]
                summary=summarize(rows)[0]
                diag=[r for r in diagnostics if r['partition']==partition and r['date']==date and r['model']==name]
                means={k:float(np.mean([r[k] for r in diag])) for k in ('forward_bias_mps','forward_rmse_mps','lateral_bias_mps','yaw_bias_deg_s','yaw_rmse_deg_s','heading_trend_deg_s','first_third_rmse_m','last_third_rmse_m','pose_support','derivative_support')} if diag else {}
                groups.append(dict(partition=partition,date=date,model=name,**summary,**means))
    save_json(out/'summary.json',dict(groups=groups,test_evaluated=False,interpretation='Channel substitutions diagnose model differences, not independently selected deployable models. Label error statistics are on observed derivative support only.',provenance={str(Path(__file__).relative_to(ROOT)):digest(Path(__file__)),str(source.relative_to(ROOT)/'artifact_manifest.json'):digest(source/'artifact_manifest.json')}))
    print(json.dumps(groups,indent=2))
if __name__=='__main__':main()
