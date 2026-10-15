"""Full simple-estimator fold refit under two frozen clocks, TRAIN207 only."""
import json
import numpy as np
import pipeline as p
from clock_arbitrated_refit_v42 import OLD, NEW, load_cache, common
from projected_yaw_folds_v52 import proxy
from participant_folds_experiment_v24 import FOLDS
from research_metrics_v59 import trajectory_metrics, aggregate
from reference_gap_accounting_v67 import relative_errors

OUT=p.ROOT/'outputs_paired_clock_refit_v72'


def main():
    OUT.mkdir(exist_ok=False); (OUT/'common_trajectories').mkdir()
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text()); cfg=protocol['old_clock_settings']
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    ids=[i for i in protocol['training_ids'] if inv[i]['participant'] in set.union(*FOLDS)]
    assert len(ids)==207 and all(inv[i]['partition']=='train' for i in ids)
    p.save_json(OUT/'protocol.json',dict(family='2 original-versus-arbitrated clock refit',configurations=['original clock','arbitrated clock'],
        parameters='Fixed v52 projected yaw weight1, physics forward speed, robust train-only yaw scale/intercept; no tuning or inherited neural model',
        scope='Entire simple predictive estimator refitted inside each fold; NOT a refit of historical v34 neural/base/residual pipeline',
        limitation='Reference geometry/QC, cached clocks and arbitration remain fixed historical evaluator dependencies; not fully nested preprocessing',
        common_support='Native C3D observed reference, shared pose and common IMU support; accepted207 retained',
        training_ids=ids,folds=[sorted(f) for f in FOLDS],validation_accessed=False,test_accessed=False))
    manifests={s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    data={}
    for ident in ids:
        old,_=load_cache(OLD,ident,manifests[OLD]); src=OLD if ident in protocol['fallback_old_clock_ids'] else NEW
        new,_=load_cache(src,ident,manifests[src]); data[ident]=(old,new)
    rows=[]; coverage=[]; models={}
    for fold,held_people in enumerate(FOLDS):
        fitting=[i for i in ids if inv[i]['participant'] not in held_people]; held=[i for i in ids if inv[i]['participant'] in held_people]
        assert not set(fitting)&set(held); pair_models={}
        for index,name in enumerate(('original_clock','arbitrated_clock')):
            cal=p.calibrate([(inv[i],data[i][index],{}) for i in fitting],cfg); yaw={}
            for setup in cal:
                xx=[]; yy=[]
                for i in fitting:
                    if inv[i]['setup']!=setup: continue
                    d=data[i][index]; mask=d['label_valid'] & d['imu_valid'] & np.isfinite(d['gt_yaw'])
                    ix=np.flatnonzero(mask)[::5]; xx.append(proxy(d,cal[setup])[ix]); yy.append(d['gt_yaw'][ix])
                yaw[setup]=p.robust_line(np.concatenate(xx),np.concatenate(yy))
            assert all(set(c['training_trials'])<=set(fitting) for c in cal.values())
            pair_models[name]=dict(calibration=cal,yaw=yaw,fit_ids=fitting,held_ids=held)
        models[str(fold)]=pair_models
        for ident in held:
            row=inv[ident]; motions={}
            for index,name in enumerate(('original_clock','arbitrated_clock')):
                d=data[ident][index]; q=pair_models[name]; cal=q['calibration'][row['setup']]; y=q['yaw'][row['setup']]
                motion=np.c_[p.velocities(d,cal)[:,0],np.zeros(len(d['t'])),proxy(d,cal)*y['scale']+y['intercept']]
                motions[name]=(d,motion)
            _,cov=common(row,*data[ident],motions,cfg,OUT); coverage.append(cov)
            with np.load(OUT/'common_trajectories'/(ident+'.npz')) as z:
                d=dict(t=z['time_s'],gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'])
                support=[]
                for name in motions:
                    xy,h=z[name+'_xy_m'],z[name+'_heading_rad']; metric=trajectory_metrics(d,xy,h)
                    mask=d['gt_valid'] & np.isfinite(xy).all(axis=1); support.append(mask)
                    error=np.linalg.norm(xy[mask]-d['gt_xy'][mask],axis=1)
                    rows.append(dict(id=ident,participant=row['participant'],condition=row['condition'],fold=fold,method=name,
                        position_mae_m=float(error.mean()),position_p95_m=float(np.percentile(error,95)),reference_coverage=float(mask.mean()),
                        **relative_errors(d,xy),**metric))
                assert np.array_equal(*support)
        print('Completed fold',fold,flush=True)
    assert len(rows)==414
    p.save_json(OUT/'models.json',models); p.write_csv(OUT/'trials.csv',rows); p.write_csv(OUT/'coverage.csv',coverage)
    for keys,name in [(('method',),'summary'),(('method','participant'),'participants'),(('method','condition'),'maneuvers')]:
        p.write_csv(OUT/(name+'.csv'),aggregate(rows,keys))
    summaries=aggregate(rows,('method',)); people=aggregate(rows,('method','participant')); maneuvers=aggregate(rows,('method','condition'))
    def ratios(items,key):
        base={r[key]:r['position_rmse_m'] for r in items if r['method']=='original_clock'}
        return {r[key]:r['position_rmse_m']/base[r[key]] for r in items if r['method']=='arbitrated_clock'}
    pr,mr=ratios(people,'participant'),ratios(maneuvers,'condition')
    p.save_json(OUT/'run.json',dict(summary=summaries,participant_ratios=pr,maneuver_ratios=mr,worst_participant_ratio=max(pr.values()),worst_maneuver_ratio=max(mr.values()),
        selection=False,promotion=False,strict_preprocessing=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps(summaries,indent=2))


if __name__=='__main__': main()
