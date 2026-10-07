"""Calibration-only conditional fold audit with fixed observed timing/geometry."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,time,copy
from pathlib import Path
import numpy as np
from pipeline import ROOT,calibrate,velocities,metrics,summarize,digest,save_json,write_csv
from trajectory_calibration_v10 import integrate
from participant_folds_experiment_v24 import FOLDS
OUT=ROOT/'outputs_calibration_fold_v37'
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve prior audit')
    OUT.mkdir();cfg=json.loads((ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings'];inherited=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    parent=ROOT/'outputs_motion_endpoint_v16';manifest=json.loads((parent/'artifact_manifest.json').read_text())['sha256'];trials=[]
    for p in sorted((parent/'prepared_training').glob('*.npz')):
        meta=p.with_suffix('.json')
        for path in (p,meta):assert digest(path)==manifest[str(path.relative_to(parent))]
        row=json.loads(meta.read_text())['row'];assert row['partition']=='train'
        with np.load(p) as z:d={k:z[k] for k in ['setup','t','ref_t','raw','imu_valid','gt_xy','gt_heading','gt_v','gt_yaw','gt_valid','label_valid']}
        trials.append((row,d,{}))
    assert len(trials)==473
    save_json(OUT/'protocol.json',dict(hypothesis='Inherited calibration creates optimistic conditional held-training performance; refit empirical axes/scales/bias on fitting people only to falsify size',scope='Calibration-only folds; frozen synchronization, reference geometry/QC and derivative targets inherited. No residual/base neural refit, validation optimization, test, or primary-model promotion.',folds=[sorted(f) for f in FOLDS],fitting='pipeline.calibrate exact current method; labels camera-observed v7; earlier groups always fit',comparators=['inherited_v2_center','all473_observed_center','fold_calibrated_center','fold_calibrated_wheel_yaw'],sensitivity='Fixed held-trial motion, center forward scale ±1%, center yaw scale ±1%, wheel-yaw track width ±10%, radius parameter±10% (expected unused)',calibrator_sha256=digest(ROOT/'pipeline.py'),training_cache_manifest_sha256=digest(parent/'artifact_manifest.json'),inherited_calibration_sha256=digest(ROOT/'outputs_amended_v2/calibration.json')))
    allcal=calibrate(trials,cfg);save_json(OUT/'all473_observed_calibration.json',allcal);print('All473 calibration fit',flush=True)
    records=[];terms=[];counts=[]
    for fold,people in enumerate(FOLDS):
        fitting=[t for t in trials if t[0]['participant'] not in people];held=[t for t in trials if t[0]['participant'] in people];assert not {t[0]['id'] for t in fitting}&{t[0]['id'] for t in held}
        cal=calibrate(fitting,cfg);save_json(OUT/f'fold_{fold}_calibration.json',cal);counts.append(dict(fold=fold,fitting_trials=len(fitting),held_trials=len(held),held_people=sorted(people)))
        for setup in cal:
            for sensor in range(3):
                a,b,c=inherited[setup]['terms'][sensor],allcal[setup]['terms'][sensor],cal[setup]['terms'][sensor]
                terms.append(dict(fold=fold,setup=setup,sensor=sensor,inherited_axis=a['axis'],observed_all_axis=b['axis'],fold_axis=c['axis'],inherited_scale=a['scale'],observed_all_scale=b['scale'],fold_scale=c['scale'],same_axis=b['axis']==c['axis'],same_sign=np.sign(b['scale'])==np.sign(c['scale']),fold_vs_all_scale_percent=100*(c['scale']/b['scale']-1) if b['axis']==c['axis'] else '',inherited_intercept=a['intercept'],observed_all_intercept=b['intercept'],fold_intercept=c['intercept']))
        for row,d,_ in held:
            motions={}
            for name,q in [('inherited_v2_center',inherited),('all473_observed_center',allcal),('fold_calibrated_center',cal)]:
                v=velocities(d,q[row['setup']]);motions[name]=np.c_[v[:,0],np.zeros(len(v)),v[:,1]]
            q=cal[row['setup']];w=[d['raw'][:,f['column']]*f['scale']+f['intercept'] for f in q['terms'][:2]];wheel=motions['fold_calibrated_center'].copy();wheel[:,2]=(w[1]-w[0])/cfg['track_width_m'];motions['fold_calibrated_wheel_yaw']=wheel
            for channel in (0,2):
                for gain in (.99,1.01):
                    m=motions['fold_calibrated_center'].copy();m[:,channel]*=gain;motions[f'center_{"forward" if channel==0 else "yaw"}_gain_{gain}']=m
            for gain in (.9,1.1):
                m=wheel.copy();m[:,2]/=gain;motions[f'wheel_track_gain_{gain}']=m
            # A stored radius change alone has no effect in pipeline.velocities.
            qr=copy.deepcopy(q);qr['wheel_radius_m']*=1.1;assert np.array_equal(velocities(d,q),velocities(d,qr))
            for name,m in motions.items():
                xy,h=integrate(d,m);records.append(dict(candidate=name,fold=fold,id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,cfg)))
        print('Completed calibration fold',fold,flush=True)
    write_csv(OUT/'terms.csv',terms);write_csv(OUT/'trials.csv',records);summary={}
    for name in sorted({r['candidate'] for r in records}):
        rr=[r for r in records if r['candidate']==name];s,p,c=summarize(rr);summary[name]=s
        for suffix,values in [('participants',p),('maneuvers',c)]:write_csv(OUT/f'{name}_{suffix}.csv',values)
    trainids={r['id'] for r,_,_ in trials};v2ids={id for q in inherited.values() for id in q['training_trials']}
    save_json(OUT/'run.json',dict(summary=summary,fold_coverage=counts,training_ids=sorted(trainids),inherited_training_only_ids_count=len(v2ids-trainids),observed_training_only_ids_count=len(trainids-v2ids),all_calibrations_same_trial_ids=v2ids==trainids,axis_changes=sum(not t['same_axis'] for t in terms),sign_changes=sum(not t['same_sign'] for t in terms),radius_parameter_effect='Exactly zero because empirical velocity scale absorbs radius; no independent wheel radius identified',test_accessed=False,validation_accessed=False,full_stack_refit=False,runtime_seconds=time.perf_counter()-start,source_sha256=digest(Path(__file__))))
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
