"""Independent-formula artifact/support review of v81, without new fitting."""
import json
import numpy as np
import pipeline as p
from native_refit_v81 import OUT as SOURCE
from backfill_metric_contract_v75 import SOURCE as BASELINE
from audit_fold_routes_v59 import verified_json
from planar_experiment import integrate_planar

OUT=p.ROOT/'outputs_native_review_v82'


def main():
    OUT.mkdir(exist_ok=False)
    rows=verified_json(SOURCE,'trial_metrics.json');run=verified_json(SOURCE,'run.json');models=verified_json(SOURCE,'models.json')
    maximum=0.;integration_maximum=0.;counts=0;checks=[]
    manifests={folder:json.loads((folder/'artifact_manifest.json').read_text())['sha256'] for folder in (SOURCE,BASELINE)}
    for fold,pair in models.items():
        for clock,q in pair.items():
            assert not set(q['fit_ids'])&set(q['held_ids'])
            assert all(set(c['training_trials'])<=set(q['fit_ids']) for c in q['calibration'].values())
    for f in sorted((SOURCE/'common_trajectories').glob('*.npz')):
        old=BASELINE/'common_trajectories'/f.name
        for folder,path in [(SOURCE,f),(BASELINE,old)]:assert p.digest(path)==manifests[folder][str(path.relative_to(folder))]
        with np.load(f) as z,np.load(old) as before:
            for key in ('time_s','native_c3d_time_s','reference_xy_m','reference_heading_rad','reference_valid','imu_valid'):assert np.array_equal(z[key],before[key])
            for clock in ('old','new'):
                method='native_'+clock+'_clock';xy=z[method+'_xy_m'];h=z[method+'_heading_rad'];m=z[method+'_motion']
                good=z['reference_valid']&np.isfinite(xy).all(1);delta=xy[good]-z['reference_xy_m'][good]
                ate=1000*np.sqrt((delta[:,0]@delta[:,0]+delta[:,1]@delta[:,1])/good.sum())
                row=next(r for r in rows if r['model']==method and r['recording_id']==f.stem)
                maximum=max(maximum,abs(float(ate)-row['ATE_RMSE_mm']));assert good.sum()==row['Valid_Frame_Count']
                rebuilt,rh=integrate_planar(z['time_s'],m,z['reference_xy_m'][0],z['reference_heading_rad'][0],z['imu_valid'])
                integration_maximum=max(integration_maximum,float(np.nanmax(abs(rebuilt-xy))));assert np.array_equal(rh,h,equal_nan=True)
                counts+=1
    assert counts==414 and maximum<1e-8 and integration_maximum==0
    for summary in run['summary']:
        method=summary['model'];people={r['participant_id'] for r in rows if r['model']==method}
        mean=sum(sum(r['ATE_RMSE_mm'] for r in rows if r['model']==method and r['participant_id']==person)/sum(r['model']==method and r['participant_id']==person for r in rows) for person in people)/len(people)
        assert abs(mean-summary['ATE_RMSE_mm'])<1e-9
        checks.append(dict(model=method,independent_balanced_ATE_mm=mean,participants=len(people),trials=sum(r['model']==method for r in rows)))
    p.write_csv(OUT/'independent_aggregates.csv',checks)
    # Prespecified regression cases: slope filter exception and long phase case.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for ident in ['2026-09-25__ST__ST_Trial2_No.13','2026-09-25__10x5__10x5_Trial1_No.13']:
        f=SOURCE/'common_trajectories'/(ident+'.npz')
        if not f.exists():raise RuntimeError('Required diagnostic case absent: '+ident)
        with np.load(f) as z,np.load(BASELINE/'common_trajectories'/f.name) as b:
            fig,axes=plt.subplots(1,2,figsize=(11,4));ref=z['reference_xy_m'].copy();ref[~z['reference_valid']]=np.nan
            for a,color,label in [(ref,'k','observed C3D'),(z['native_new_clock_xy_m'],'r','native IMU'),(b['new_model_new_clock_xy_m'],'#999999','cropped IMU control')]:axes[0].plot(a[:,0],a[:,1],color=color,label=label)
            for a,color,label in [(z['reference_heading_rad'],'k','observed C3D'),(z['native_new_clock_heading_rad'],'r','native IMU'),(b['new_model_new_clock_heading_rad'],'#999999','cropped IMU control')]:
                h=np.rad2deg(np.angle(np.exp(1j*(a-z['reference_heading_rad'][0]))));h=h.copy()
                if color=='k':h[~z['reference_valid']]=np.nan
                h[np.r_[False,abs(np.diff(h))>180]]=np.nan;axes[1].plot(z['time_s'],h,color=color,label=label)
            axes[0].axis('equal');axes[0].set(xlabel='X (m)',ylabel='Y (m)');axes[1].set(xlabel='time (s)',ylabel='relative yaw (degrees)')
            for ax in axes:ax.legend(fontsize=8);ax.grid(alpha=.2)
            fig.suptitle(ident+' | conditional TRAIN diagnostic');fig.tight_layout();fig.savefig(OUT/(ident+'.png'),dpi=150);plt.close(fig)
    p.save_json(OUT/'run.json',dict(prediction_checks=counts,maximum_independent_ATE_difference_mm=maximum,maximum_reintegrated_XY_difference_m=integration_maximum,
        support_and_pose_unchanged=True,fold_fit_ID_checks=True,summary=checks,decisions=run['decisions'],promotion=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
