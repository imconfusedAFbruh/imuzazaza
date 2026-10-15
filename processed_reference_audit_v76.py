"""Secondary stored-processed reference audit on TRAIN predictions only."""
import json
import numpy as np
import pipeline as p
from metric_contract_v74 import metrics
from backfill_metric_contract_v75 import SOURCE,summaries

OUT=p.ROOT/'outputs_processed_reference_v76'


def main():
    OUT.mkdir(exist_ok=False);(OUT/'reference_flags').mkdir()
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text()); cfg=protocol['old_clock_settings']
    parent_manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    p.save_json(OUT/'protocol.json',dict(hypothesis='Stored processed reference increases support but may alter reported errors without estimator improvement',
        configurations=['original observed primary unchanged','observed plus stored residual-zero secondary'],no_fitting=True,no_new_interpolation=True,
        provenance='Residual-zero stored XYZ; reconstruction/filtering algorithm and uncertainty unknown. Lower confidence, never a replacement for primary reference.',
        validation_accessed=False,test_accessed=False,training_use=False))
    rows=[];audit=[]
    files=sorted((SOURCE/'common_trajectories').glob('*.npz')); assert len(files)==207
    for count,file in enumerate(files,1):
        ident=file.stem;r=inv[ident];assert r['partition']=='train'
        assert p.digest(file)==parent_manifest[str(file.relative_to(SOURCE))]
        c=p.ezc3d.c3d(str(p.ROOT/r['c3d'])); point=c['parameters']['POINT']; names=[s.strip() for s in point['LABELS']['value']]
        ix=[names.index(k) for k in ('L_FAL','R_FAL')]; unit=point['UNITS']['value'][0].strip().lower();scale={'mm':.001,'cm':.01,'m':1.}[unit]
        xyz=c['data']['points'][:3,ix,:].transpose(2,1,0)*scale;res=c['data']['meta_points']['residuals'][0,ix,:].T
        available=np.isfinite(xyz).all((1,2))&(np.linalg.norm(xyz,axis=2)>1e-8).all(1)&(res>=0).all(1)
        observed=available&(res>0).all(1);processed=available&(res==0).any(1)
        masks=c['data']['meta_points'].get('camera_masks')
        if masks is not None:
            support=np.asarray(masks)[:,ix,:].any(0).T
            if support.any():observed &= support.all(1)
        uncertain_camera=available&~observed&~processed
        sep=np.linalg.norm(xyz[:,0]-xyz[:,1],axis=1);policy=cfg['reference_geometry']['setups'][r['setup']];bands=np.zeros(len(xyz),bool)
        for band in policy['bands']:bands|=(sep>=band['lower_m'])&(sep<=band['upper_m'])
        rigid=np.abs(sep-np.median(sep[observed]))<=policy['rigidity_tolerance_m']
        quality=bands&rigid;observed &= quality;processed &= quality
        hz=float(c['header']['points']['frame_rate']);full_end=(len(xyz)-1)/hz
        with np.load(file) as z:
            indexes=np.rint(z['native_c3d_time_s']*hz).astype(int)
            assert np.max(np.abs(indexes/hz-z['native_c3d_time_s']))<1e-8
            assert indexes.min()>=0 and indexes.max()<len(xyz)
            obs,proc=observed[indexes],processed[indexes];valid=z['reference_valid']|proc
            xy=xyz[indexes,:,:2].mean(1);lat=xyz[indexes,0,:2]-xyz[indexes,1,:2];h=np.arctan2(-lat[:,0],lat[:,1])
            primary=z['reference_valid']
            assert np.max(np.abs(xy[primary]-z['reference_xy_m'][primary]))<1e-9
            assert not np.any(primary&proc)
            xy[primary]=z['reference_xy_m'][primary];h[primary]=z['reference_heading_rad'][primary]
            flag=np.full(len(valid),'invalid',dtype='U32');flag[obs]='observed';flag[proc]='stored_processed';flag[uncertain_camera[indexes]]='unverified_camera_support'
            np.savez_compressed(OUT/'reference_flags'/(ident+'.npz'),native_c3d_time_s=z['native_c3d_time_s'],sample_class=flag,original_primary_mask=primary,secondary_mask=valid,
                reference_xy_m=xy,reference_heading_rad=h,decoded_residual=res[indexes])
            audit.append(dict(recording_id=ident,participant_id=r['participant'],maneuver=r['condition'],source_c3d=r['c3d'],source_sha256=p.digest(p.ROOT/r['c3d']),
                frames=len(valid),primary_frames=int(primary.sum()),added_processed_frames=int((valid&~primary).sum()),
                uncertain_camera_frames=int(uncertain_camera[indexes].sum()),invalid_frames=int((~available[indexes]).sum()),processing_method='unknown stored residual-zero coordinates',
                native_endpoint_included=bool(abs(z['native_c3d_time_s'][-1]-full_end)<1e-8)))
            d=dict(t=z['time_s'],gt_xy=xy,gt_heading=h,gt_valid=valid,
                recording_endpoint_included=bool(abs(z['native_c3d_time_s'][-1]-full_end)<1e-8 and obs[-1]))
            for model in sorted(k[:-5] for k in z.files if k.endswith('_xy_m') and k!='reference_xy_m'):
                result=metrics(d,z[model+'_xy_m'],z[model+'_heading_rad'],z[model+'_motion'])
                rows.append(dict(experiment_id='v76_secondary_reference',model=model,participant_id=r['participant'],recording_id=ident,maneuver=r['condition'],trial=r['repetition'],
                    split='train_oof_retrospective',reference_track='observed_plus_stored_processed_secondary',processing_method='unknown',**result))
        if count%25==0:print(count,flush=True)
    assert len(rows)==828
    p.write_csv(OUT/'trial_metrics.csv',rows);p.save_json(OUT/'trial_metrics.json',rows);p.write_csv(OUT/'reference_audit.csv',audit)
    summary=summaries(rows,('model',));p.write_csv(OUT/'summary.csv',summary);p.write_csv(OUT/'maneuver_summary.csv',summaries(rows,('model','maneuver')))
    p.write_csv(OUT/'participant_summary.csv',summaries(rows,('model','participant_id')))
    p.save_json(OUT/'run.json',dict(trials=207,primary_frames=sum(r['primary_frames'] for r in audit),added_stored_processed_frames=sum(r['added_processed_frames'] for r in audit),
        filename_processed_count=len(list((p.ROOT/'c3d').rglob('*processed*.c3d'))),summary=[{k:s[k] for k in ['model','ATE_RMSE_mm','Position_MAE_mm','C3D_Coverage_pct']} for s in summary],
        estimator_changed=False,training_use=False,promotion=False,processing_provenance_verified=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps({s['model']:s['ATE_RMSE_mm'] for s in summary},indent=2))


if __name__=='__main__':main()
