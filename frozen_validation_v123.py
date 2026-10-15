"""One authorized frozen v121/v34 comparison. No fitting or candidate search."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import csv
import datetime
import json
from pathlib import Path
import sys
import time
import numpy as np
import pipeline as p

OUT=p.ROOT/'outputs_frozen_validation_v123_exact'
MODEL_SHA='6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b'
GUARD_KEYS=('Position_P95_mm','Last_Supported_Endpoint_Error_mm','heading_rmse_deg')
# v36 historical XY/aggregate thresholds; additional motion/startup thresholds
# from v44/v121. Heading and per-trial checks are newly fixed before evaluation.
TOL=dict(xy_m=1e-8,aggregate_m=1e-9,motion=1e-7,startup=1e-10,
         heading_rad=1e-8,trial_atol=1e-9,trial_rtol=1e-10)


def ratio(candidate,baseline):
    if not np.isfinite([candidate,baseline]).all() or min(candidate,baseline)<0:
        raise ValueError('Nonfinite or negative guard value')
    return candidate/baseline if baseline else (1. if candidate==0 else None)


def decision(base,candidate):
    def indexed(rows):
        indexed={r['id']:r for r in rows}
        if not rows or len(indexed)!=len(rows):raise ValueError('Empty/duplicate IDs')
        for r in rows:
            for key in ('position_rmse_m',*GUARD_KEYS):ratio(r[key],r[key])
        return indexed
    bb,cc=indexed(base),indexed(candidate)
    if bb.keys()!=cc.keys():raise ValueError('Missing recording')
    for ident,b in bb.items():
        if any(b[k]!=cc[ident][k] for k in ('participant','condition','scored_frames')):
            raise ValueError('Changed identity or frame counts')
    bs,bp,bm=p.summarize(base);cs,cp,cm=p.summarize(candidate)
    pr={r['participant']:ratio(r['mean_trial_position_rmse_m'],
        next(b['mean_trial_position_rmse_m'] for b in bp if b['participant']==r['participant'])) for r in cp}
    mr={r['condition']:ratio(r['equal_participant_mean_position_rmse_m'],
        next(b['equal_participant_mean_position_rmse_m'] for b in bm if b['condition']==r['condition'])) for r in cm}
    def balanced(rows,key):
        return float(np.mean([np.mean([r[key] for r in rows if r['participant']==person])
                              for person in sorted({r['participant'] for r in rows})]))
    gr={key:ratio(balanced(candidate,key),balanced(base,key)) for key in GUARD_KEYS}
    failures=[name for group in (pr,mr,gr) for name,value in group.items() if value is None or value>1.05]
    lower=cs['equal_participant_mean_position_rmse_m']<bs['equal_participant_mean_position_rmse_m']
    if not lower:failures.append('mean_ATE_not_lower')
    return dict(eligible=not failures,failed_guards=failures,baseline=bs,candidate=cs,
                participant_ratios=pr,maneuver_ratios=mr,guard_ratios=gr,
                zero_baseline_policy='no increase; null ratio means failed positive-over-zero')


def check_support(reference,base_xy,base_h,xy,h,motion):
    n=len(reference)
    if xy.shape!=(n,2) or h.shape!=(n,) or motion.shape!=(n,3):
        raise ValueError('Changed prediction shape')
    # Exact masks include unscored portions too; never silently intersect masks.
    if not np.array_equal(np.isfinite(base_xy),np.isfinite(xy)):
        raise ValueError('Position support changed')
    if not np.array_equal(np.isfinite(base_h),np.isfinite(h)):
        raise ValueError('Heading support changed')
    mask=reference & np.isfinite(base_xy).all(1)
    if not np.isfinite(motion[mask]).all() or not np.isfinite(h[mask]).all():
        raise ValueError('Nonfinite candidate on baseline support')
    return mask


def stop_check():
    for root in (p.ROOT,Path('D:/project/WheelAthelse')):
        if (root/'research_state/STOP').exists():raise RuntimeError('STOP marker')


def delta(actual,expected,tolerance,label):
    if actual.shape!=expected.shape or not np.array_equal(np.isnan(actual),np.isnan(expected)):
        raise ValueError(label+' shape/NaN support mismatch')
    if not np.array_equal(np.isfinite(actual),np.isfinite(expected)):
        raise ValueError(label+' finite support mismatch')
    good=np.isfinite(expected)
    maximum=float(np.max(np.abs(actual[good]-expected[good]))) if good.any() else 0.
    if maximum>tolerance:raise ValueError(f'{label} difference {maximum} > {tolerance}')
    return maximum


def historical_metrics_match(actual,saved):
    for key,value in actual.items():
        target=saved[key]
        if isinstance(value,bool):
            if str(value)!=target:raise ValueError('Historical boolean mismatch: '+key)
        elif isinstance(value,(float,int)):
            if not np.isclose(value,float(target),atol=TOL['trial_atol'],rtol=TOL['trial_rtol']):
                raise ValueError('Historical trial metric mismatch: '+key)
        elif str(value)!=target:raise ValueError('Historical trial field mismatch: '+key)


def main():
    start=time.perf_counter();stop_check()
    # Always run synthetic contract tests before opening any validation artifact.
    import unittest
    suite=unittest.defaultTestLoader.loadTestsFromName('test_frozen_validation_v123')
    if not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful():
        raise RuntimeError('Synthetic validation contract failed')
    import torch
    from observed_training_experiment import observed_rows
    from dynamic_blend_inference_v34 import load_dynamic_blend,integrate_motion
    from reservoir_inference_v121 import load_reservoir_model
    from stationary_gravity_inference_v14 import initialize_startup
    from metric_contract_v74 import metrics as extended_metrics
    # v33 created the saved motions with four Torch threads. v36's two-thread
    # loader audit has tiny historical FP residuals; match the producing run.
    torch.set_num_threads(4)
    if torch.cuda.is_available():raise RuntimeError('CPU required')
    if p.digest(p.ROOT/'models/reservoir_path_v121_completed/model.json')!=MODEL_SHA:
        raise RuntimeError('Frozen candidate changed')
    OUT.mkdir(exist_ok=False);(OUT/'predictions').mkdir();(OUT/'baseline').mkdir()
    inputs={}
    def pin(path):
        path=Path(path);name=str(path.relative_to(p.ROOT));sha=p.digest(path)
        if name in inputs and inputs[name]!=sha:raise ValueError('Input changed during evaluation: '+name)
        inputs[name]=sha
        return sha
    def seal(folder,name):
        manifest_path=folder/'artifact_manifest.json';pin(manifest_path)
        manifest=json.loads(manifest_path.read_text())['sha256'];path=folder/name
        if pin(path)!=manifest[name]:raise ValueError('Changed sealed input: '+str(path))
        return path
    source=p.ROOT/'outputs_observed_reference_v7';parent=p.ROOT/'outputs_dynamic_blend_v34'
    cfg=json.loads(seal(source,'run.json').read_text())['settings'];seal(source,'qc.csv')
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    saved_rows=list(csv.DictReader(seal(parent,'selected_blend_trials.csv').open(newline='')))
    expected={r['id']:r for r in saved_rows}
    if len(expected)!=71 or len(saved_rows)!=71:raise ValueError('Expected exactly 71 unique v34 IDs')
    cal_path=p.ROOT/'outputs_amended_v2/calibration.json';pin(cal_path);cal=json.loads(cal_path.read_text())
    init_path=seal(p.ROOT/'outputs_stationary_gravity_v14','initialization.json')
    oldstates={r['id']:r for r in json.loads(init_path.read_text())['records']}
    for name in ('inventory.json','input_identity_audit.json'):pin(p.ROOT/'outputs_amended_v2'/name)
    # Pin actual nested inference artifacts, not just their manifest files.
    nested={
        'outputs_dynamic_blend_v34':('model.json','selection.json'),
        'outputs_nonlinear_endpoint_v21':('model.json','run.json'),
        'outputs_dynamic_tilt_v33':('tilt_0.3_model.json',),
        'outputs_observed_ridge_v8':('selection.json','linear_artifacts.npz','normalization.json'),
    }
    for folder,names in nested.items():
        for name in names:
            path=seal(p.ROOT/folder,name)
            if name in ('run.json','selection.json'):
                for dependency in json.loads(path.read_text()).get('provenance',{}):pin(p.ROOT/dependency)
    for name in ('outputs_amended_v2/normalization.json','outputs_amended_v2/tcn32.pt',
                 'outputs_planar_neural_v4/normalization.json','outputs_planar_neural_v4/all_three.pt'):
        pin(p.ROOT/name)
    baseline_predict=load_dynamic_blend()
    # Validates frozen candidate artifacts/dependencies, but does not predict yet.
    candidate_predict=load_reservoir_model()
    model=json.loads((p.ROOT/'models/reservoir_path_v121_completed/model.json').read_text())
    for name in model['dependencies']:pin(p.ROOT/name)
    for f in (p.ROOT/'models/reservoir_path_v121_completed').iterdir():
        if f.is_file():pin(f)
    # Record every locally loaded Python dependency, plus protocol/test source.
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            # PyTorch exposes virtual modules with relative __file__ values
            # such as _ops.py; these are not local source files.
            if path.is_relative_to(p.ROOT) and path.suffix=='.py' and path.is_file():pin(path)
    for name in ('frozen_validation_v123.py','test_frozen_validation_v123.py',
                 'research_docs/frozen_validation_decision_v121.md','research_docs/frozen_validation_v123.md'):
        pin(p.ROOT/name)
    p.save_json(OUT/'protocol.json',dict(candidate_sha256=MODEL_SHA,tolerances=TOL,
        validation_ids=sorted(expected),authorization='User: Authorize the frozen v121 validation comparison',
        candidate='v121 penalty10 frozen full TRAIN',control='v34 weight0.75',
        test_accessed=False,refitting=False,retuning=False,source_and_initial_input_hashes=inputs.copy(),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    entries=[];base=[];checks=[];seen=set()
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        stop_check();ident=row['id']
        if ident not in expected or ident in seen:raise ValueError('Unexpected/duplicate validation ID')
        seen.add(ident)
        if any(row[k]!=expected[ident][k] for k in ('participant','condition')):
            raise ValueError('Historical identity mismatch')
        for suffix in ('.npz','.json'):pin(source/'cache'/(ident+suffix))
        for kind in ('imu','c3d'):pin(p.ROOT/row[kind])
        tt,raw,valid=p.sample_streams(p.imu_streams(p.ROOT/row['imu']),cfg)
        state=initialize_startup(dict(t=tt,raw=raw,imu_valid=valid),cal[row['setup']])
        previous=oldstates[ident]
        state_checks={key:delta(np.asarray(state[key]),np.asarray(previous[key]),TOL['startup'],key)
                      for key in ('gravity','gyro_bias')}
        if state['eligible']!=previous['eligible']:raise ValueError('Startup eligibility changed')
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};sensor['initialization']=state
        motion=baseline_predict(sensor)
        xy,h=integrate_motion(d['t'],motion,d['gt_xy'][0],d['gt_heading'][0],d['imu_valid'])
        historical=seal(parent,str(Path('trajectories')/(ident+'.npz')))
        with np.load(historical) as z:
            for current,old in (('t','time_s'),('gt_xy','reference_xy_m'),('gt_heading','reference_heading_rad'),
                                ('gt_valid','reference_valid'),('imu_valid','imu_valid')):
                if not np.array_equal(d[current],z[old],equal_nan=True):raise ValueError('Historical reference mismatch: '+current)
            check=dict(id=ident,**state_checks,
                motion_delta=delta(motion,z['selected_blend_motion'],TOL['motion'],'motion'),
                xy_delta_m=delta(xy,z['selected_blend_xy_m'],TOL['xy_m'],'xy'),
                heading_delta_rad=delta(h,z['selected_blend_heading_rad'],TOL['heading_rad'],'heading'))
            support=check_support(d['gt_valid'],z['selected_blend_xy_m'],z['selected_blend_heading_rad'],xy,h,motion)
        core=p.metrics(d,xy,h,cfg);historical_metrics_match(core,expected[ident])
        record=dict(id=ident,participant=row['participant'],condition=row['condition'],**core)
        base.append(record);checks.append(check)
        np.savez_compressed(OUT/'baseline'/(ident+'.npz'),motion=motion,xy=xy,heading=h,support=support)
        entries.append((row,d,sensor,motion,xy,h))
        p.save_json(OUT/'checkpoint.json',dict(stage='baseline_reproduction',baseline_count=len(base),candidate_count=0))
        if len(base)%10==0:print('Baseline reproduced',len(base),'/71',flush=True)
    if seen!=set(expected):raise ValueError('Missing validation records')
    summary=p.summarize(base)[0]
    if abs(summary['equal_participant_mean_position_rmse_m']-.1007021193993738)>TOL['aggregate_m']:
        raise ValueError('Historical aggregate mismatch')
    p.save_json(OUT/'baseline_reproduction.json',dict(summary=summary,checks=checks,exact_reference_and_support=True))
    p.save_json(OUT/'input_hashes.json',inputs)
    print('All 71 baselines passed; starting one frozen candidate evaluation',flush=True)
    candidate=[]
    for i,(row,d,sensor,bmotion,bxy,bh) in enumerate(entries):
        stop_check();ident=row['id'];motion=candidate_predict(sensor)
        xy,h=integrate_motion(d['t'],motion,d['gt_xy'][0],d['gt_heading'][0],d['imu_valid'])
        support=check_support(d['gt_valid'],bxy,bh,xy,h,motion)
        base[i].update(extended_metrics(d,bxy,bh,bmotion))
        candidate.append(dict(id=ident,participant=row['participant'],condition=row['condition'],
                              **p.metrics(d,xy,h,cfg),**extended_metrics(d,xy,h,motion)))
        arrays={key:d[key] for key in ('t','gt_xy','gt_heading','gt_valid','imu_valid')}
        arrays.update(baseline_motion=bmotion,baseline_xy=bxy,baseline_heading=bh,
                      candidate_motion=motion,candidate_xy=xy,candidate_heading=h,scored_support=support)
        np.savez_compressed(OUT/'predictions'/(ident+'.npz'),**arrays)
        p.write_csv(OUT/'baseline_trials.csv',base[:i+1]);p.write_csv(OUT/'candidate_trials.csv',candidate)
        p.save_json(OUT/'checkpoint.json',dict(stage='candidate_evaluation',baseline_count=71,candidate_count=i+1))
        if (i+1)%10==0:print('Candidate evaluated',i+1,'/71',flush=True)
    result=decision(base,candidate)
    for name,rows in (('baseline',base),('candidate',candidate)):
        _,people,maneuvers=p.summarize(rows)
        p.write_csv(OUT/(name+'_participants.csv'),people);p.write_csv(OUT/(name+'_maneuvers.csv'),maneuvers)
    # Detect changes to all pinned inputs during execution before accepting results.
    for name,sha in inputs.items():
        if p.digest(p.ROOT/name)!=sha:raise ValueError('Input changed during run: '+name)
    p.save_json(OUT/'run.json',dict(decision=result,validation_trials=71,validation_accessed=True,
        test_accessed=False,refitting=False,retuning=False,promotion=False,complete_support=True,
        runtime_seconds=time.perf_counter()-start,review_status='pending',
        interpretation='Previously exposed development validation; not a blind final test'))
    p.save_json(OUT/'checkpoint.json',dict(stage='complete',baseline_count=71,candidate_count=71))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f)
        for f in OUT.rglob('*') if f.is_file() and f.name!='artifact_manifest.json'}))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    existed_before=OUT.exists()
    try: main()
    except BaseException as exc:
        if not existed_before and OUT.exists() and not (OUT/'run.json').exists():
            p.save_json(OUT/'failure.json',dict(error=repr(exc),candidate_not_accepted=True,
                instruction='Preserve this attempt; diagnose without retuning or loosening thresholds'))
        raise
