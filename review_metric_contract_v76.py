"""Verify the saved primary/secondary comparisons and make review artifacts."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pipeline as p
from metric_contract_v74 import self_check
from backfill_metric_contract_v75 import SOURCE,OUT as PRIMARY,summaries
from processed_reference_audit_v76 import OUT


def main():
    self_check()
    a=json.loads((PRIMARY/'trial_metrics.json').read_text())
    b=json.loads((OUT/'trial_metrics.json').read_text())
    assert len(a)==len(b)==828
    audit=list(csv.DictReader((OUT/'reference_audit.csv').open()))
    for r in audit:
        assert p.digest(p.ROOT/r['source_c3d'])==r['source_sha256']
        with np.load(OUT/'reference_flags'/(r['recording_id']+'.npz')) as z:
            assert np.all(z['sample_class'][z['original_primary_mask']]=='observed')
            added=z['secondary_mask']&~z['original_primary_mask']
            assert np.all(z['sample_class'][added]=='stored_processed')
            assert int(added.sum())==int(r['added_processed_frames'])
            assert np.all((z['decoded_residual'][added]==0).any(1))
    sa=summaries(a,('model',));sb=summaries(b,('model',))
    for name,groups in [('summary.csv',('model',)),('maneuver_summary.csv',('model','maneuver')),('participant_summary.csv',('model','participant_id'))]:
        p.write_csv(OUT/name,summaries(b,groups))
    dashboard=[]
    keys=['ATE_RMSE_mm','Position_MAE_mm','RMSE_X_mm','RMSE_Y_mm','Endpoint_Error_mm','Endpoint_Drift_pct','Last_Supported_Endpoint_Error_mm','Last_Supported_Normalized_Endpoint_pct','RTE_1s_mm','RTE_5s_mm','RTE_10s_mm','Yaw_RMSE_deg','Speed_RMSE_mps','Angular_Velocity_RMSE_degps','Position_P95_mm','Route_RMSE_mm','Route_P95_mm','Sampled_Hausdorff_mm','Maximum_Run_Frechet_mm','Within_Run_Arc_Length_RMSE_mm','Path_Length_Error_mm','C3D_Coverage_pct']
    for x,y in zip(sa,sb):
        assert x['model']==y['model']
        for key in keys:
            v,w=x.get(key),y.get(key)
            dashboard.append(dict(model=x['model'],Metric=key,Original_Observed=v,Observed_Plus_Processed=w,Change=w-v if v is not None and w is not None else None,
                Original_Eligible_Trials=x.get(key+'_Eligible_Trials',0),Secondary_Eligible_Trials=y.get(key+'_Eligible_Trials',0),Decision='diagnostic only: different reference support, identical estimator'))
    p.write_csv(OUT/'dashboard.csv',dashboard)
    paired=[]
    baseline={(r['model'],r['participant_id']):r for r in summaries(a,('model','participant_id'))}
    for r in summaries(b,('model','participant_id')):
        x=baseline[r['model'],r['participant_id']]
        paired.append(dict(model=r['model'],participant_id=r['participant_id'],Original_ATE_mm=x['ATE_RMSE_mm'],Secondary_ATE_mm=r['ATE_RMSE_mm'],Change_mm=r['ATE_RMSE_mm']-x['ATE_RMSE_mm']))
    p.write_csv(OUT/'paired_participant_differences.csv',paired)
    ident='2026-09-25__10x5__10x5_Trial1_No.13'
    with np.load(SOURCE/'common_trajectories'/(ident+'.npz')) as z,np.load(OUT/'reference_flags'/(ident+'.npz')) as f:
        fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
        for mask,color,label in [(f['sample_class']=='stored_processed','0.6','Stored processed (secondary)'),(f['original_primary_mask'],'black','Observed C3D (primary)')]:
            xy=np.where(mask[:,None],f['reference_xy_m'],np.nan)
            axes[0].plot(*xy.T,color=color,lw=1,label=label)
            axes[1].plot(z['time_s'],np.where(mask,np.rad2deg(np.unwrap(f['reference_heading_rad'])),np.nan),color=color,lw=1,label=label)
        axes[0].plot(*z['new_model_new_clock_xy_m'].T,color='red',lw=1,label='IMU')
        axes[1].plot(z['time_s'],np.rad2deg(np.unwrap(z['new_model_new_clock_heading_rad'])),color='red',lw=1,label='IMU')
        axes[0].set(xlabel='World X (m)',ylabel='World Y (m)',title='XY trajectory');axes[0].set_aspect('equal',adjustable='box')
        axes[1].set(xlabel='Time (s)',ylabel='Unwrapped yaw (degrees)',title='Yaw vs time')
        for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8)
        fig.suptitle(ident+' | same estimator, no alignment; processed provenance unknown',fontsize=10)
        fig.savefig(OUT/'reference_comparison.png',dpi=150);plt.close(fig)
    p.save_json(OUT/'verification.json',dict(metric_tests='passed',primary_sample_class_checks=207,processed_addition_checks=207,source_hash_checks=207,
        matched_recording_models=828,training_only=True,promotion=False,uncertainty='Descriptive participant/trial distributions only; no independent-frame confidence intervals'))
    for folder in (PRIMARY,OUT):
        p.save_json(folder/'artifact_manifest.json',dict(sha256={str(f.relative_to(folder)):p.digest(f) for f in folder.rglob('*') if f.is_file() and f.name!='artifact_manifest.json'},
            metric_code_sha256=p.digest(p.ROOT/'metric_contract_v74.py'),review_code_sha256=p.digest(__file__)))
    print('828 paired metrics and 207 original/processed provenance masks verified; figure saved')


if __name__=='__main__':main()
