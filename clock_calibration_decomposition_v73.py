"""Fixed-model 2x2 timing/calibration diagnostic, no additional fitting."""
import json
import numpy as np
import pipeline as p
from paired_clock_refit_v72 import OLD,NEW,load_cache,common,proxy
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_clock_calibration_decomposition_v73'


def motion(sensor,model,setup):
    # Explicit input boundary: optical values cannot reach motion prediction.
    d={k:sensor[k] for k in ('raw','imu_valid')}
    cal=model['calibration'][setup]; y=model['yaw'][setup]
    return np.c_[p.velocities(d,cal)[:,0],np.zeros(len(d['raw'])),proxy(d,cal)*y['scale']+y['intercept']]


def main():
    OUT.mkdir(exist_ok=False); (OUT/'common_trajectories').mkdir()
    parent=p.ROOT/'outputs_paired_clock_refit_v72'; models=verified_json(parent,'models.json')
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text()); cfg=protocol['old_clock_settings']
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    p.save_json(OUT/'protocol.json',dict(family='2 fixed fitted-model diagnostic',new_fitting=False,selection=False,
        question='Do participant regressions come from clock mapping or from fitted motion calibration?',
        cells='old model/old clock, old model/new clock, new model/old clock, new model/new clock; no search and no promotion',
        reference='Same frozen native mask/initial pose as v72; no optical motion prediction inputs',validation_accessed=False,test_accessed=False))
    rows=[]; poisoned=0; maximum=0.
    parent_manifest=json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    for fold,q in models.items():
        assert q['original_clock']['fit_ids']==q['arbitrated_clock']['fit_ids']
        for ident in q['original_clock']['held_ids']:
            r=inv[ident]; assert r['partition']=='train' and ident not in q['original_clock']['fit_ids']
            old,_=load_cache(OLD,ident,manifests[OLD]); src=OLD if ident in protocol['fallback_old_clock_ids'] else NEW
            new,_=load_cache(src,ident,manifests[src]); motions={}
            for clock,d in [('old',old),('new',new)]:
                for fitted,key in [('old','original_clock'),('new','arbitrated_clock')]:
                    m=motion(d,q[key],r['setup'])
                    poison=dict(d,gt_xy=np.full_like(d['gt_xy'],999),gt_yaw=np.full_like(d['gt_yaw'],999),gt_heading=np.full_like(d['gt_heading'],999),label_valid=~d['label_valid'],gt_valid=~d['gt_valid'])
                    assert np.array_equal(m,motion(poison,q[key],r['setup'])); poisoned+=1
                    motions[f'{fitted}_model_{clock}_clock']=(d,m)
            rr,_=common(r,old,new,motions,cfg,OUT)
            rows.extend(rr)
            f=parent/'common_trajectories'/(ident+'.npz'); assert p.digest(f)==parent_manifest[str(f.relative_to(parent))]
            with np.load(f) as before,np.load(OUT/'common_trajectories'/(ident+'.npz')) as after:
                assert np.array_equal(before['reference_valid'],after['reference_valid'])
                for previous,current in [('original_clock','old_model_old_clock'),('arbitrated_clock','new_model_new_clock')]:
                    maximum=max(maximum,float(np.nanmax(np.abs(before[previous+'_xy_m']-after[current+'_xy_m']))))
    assert len(rows)==828 and maximum<1e-10
    p.write_csv(OUT/'trials.csv',rows); summaries={}; people={}
    for method in sorted({r['method'] for r in rows}):
        s,pp,mm=p.summarize([r for r in rows if r['method']==method]); summaries[method]=s; people[method]=pp
        p.write_csv(OUT/(method+'_participants.csv'),pp); p.write_csv(OUT/(method+'_maneuvers.csv'),mm)
    p.save_json(OUT/'run.json',dict(summary=summaries,poisoned_motion_checks=poisoned,max_diagonal_prediction_difference_m=maximum,
        new_fitting=False,selection=False,promotion=False,test_accessed=False,validation_accessed=False))
    # Visualize selected regression and improvement cases using the main new-clock method.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    (OUT/'figures').mkdir()
    cases=[r for r in rows if r['method']=='new_model_new_clock' and r['participant'] in ('No.13','No.17','No.15') and r['condition'] in ('PS','10x5','ST')]
    for r in cases:
        with np.load(OUT/'common_trajectories'/(r['id']+'.npz')) as z:
            ref=z['reference_xy_m'].copy(); ref[~z['reference_valid']]=np.nan
            fig,axes=plt.subplots(1,2,figsize=(10,4)); pos=z['new_model_new_clock_xy_m']
            axes[0].plot(ref[:,0],ref[:,1],'k',label='C3D'); axes[0].plot(pos[:,0],pos[:,1],'r',label='IMU'); axes[0].axis('equal'); axes[0].set(xlabel='X (m)',ylabel='Y (m)')
            for h,col,label in [(z['reference_heading_rad'],'k','C3D'),(z['new_model_new_clock_heading_rad'],'r','IMU')]:
                h=np.rad2deg(np.angle(np.exp(1j*(h-z['reference_heading_rad'][0])))); h=h.copy()
                if col=='k': h[~z['reference_valid']]=np.nan
                h[np.r_[False,np.abs(np.diff(h))>180]]=np.nan
                axes[1].plot(z['time_s'],h,col,label=label)
            axes[1].set(xlabel='Time (s)',ylabel='Wrapped relative yaw (deg)')
            for ax in axes: ax.grid(alpha=.2); ax.legend()
            fig.suptitle(r['id']); fig.tight_layout(); fig.savefig(OUT/'figures'/(r['id']+'.png'),dpi=130); plt.close(fig)
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps({k:v['equal_participant_mean_position_rmse_m'] for k,v in summaries.items()},indent=2))


if __name__=='__main__': main()
