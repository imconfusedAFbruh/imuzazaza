"""Short center-acceleration speed bridge on IMU-only braking disagreement.

Conditional v21 correction refitted inside the training participant fold.
No processed derivative labels, optical inference signals, or test data.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import json
import time
import sys
import csv
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from pipeline import ROOT, digest, save_json, write_csv, runs, metrics, summarize
from nonlinear_endpoint_experiment_v21 import load_train, bounds, adapted, nonlinear_features, FOLD
from motion_endpoint_experiment_v16 import normal_system, fit
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from controlled_motion_experiment_v25 import predict_affine, sensor
from trajectory_calibration_v10 import integrate

OUT = ROOT/'outputs_braking_bridge_v34'
BLENDS = (0., .25, .5)
MAX_BRIDGE_S = 1.
ANCHOR_LOOKBACK_S = .15
ACC_ALPHA = .1
GATE_QUANTILES = dict(deceleration=.65, wheel_body_mismatch=.70, wheel_asymmetry=.80)


def trailing(x, valid, width=5):
    out = np.asarray(x, dtype=float).copy()
    for a, b in runs(valid):
        xx = np.asarray(x[a:b], dtype=float)
        prefix = np.r_[0., np.cumsum(xx)]
        ids = np.arange(len(xx)); left = np.maximum(ids-width+1, 0)
        out[a:b] = (prefix[ids+1]-prefix[left])/(ids-left+1)
    return out


def derivative(x, t, valid, lookback=8):
    out = np.zeros(len(x))
    for a, b in runs(valid):
        ids = np.arange(a, b); prior = np.maximum(ids-lookback, a)
        dt = t[ids]-t[prior]
        out[ids] = np.divide(x[ids]-x[prior], dt, out=np.zeros(len(ids)), where=dt>0)
    return trailing(out, valid)


def observed_acceleration(e):
    d = e['data']; target = np.full(len(d['t']), np.nan)
    for a, b in runs(e['label']):
        if b-a < 20:
            continue
        y = np.gradient(d['gt_v'][a:b], d['t'][a:b])
        target[a+5:b-5] = y[5:-5]
    return target


def acceleration_features(e):
    # Existing startup-gravity-aligned center channels at context zero.
    # Their physical SI/mounting calibration is still not independently verified.
    f = e['linear'][:, 30:36].astype(float)
    return np.c_[f, np.linalg.norm(f[:, :3], axis=1), np.linalg.norm(f[:, 3:], axis=1), f[:, 3:]**2]


def refit_base(entries):
    clips = bounds(entries)
    fits = fit(normal_system(adapted(entries, 'physical_products', clips)), .1, 1.)
    return dict(fits=fits, feature_clip=clips)


def prepare(entries, base, cal):
    out = []
    for e in entries:
        d = e['data']; c = cal[e['setup']]; m = predict_affine(e, base, gain=.5)
        wheel = np.c_[*[d['raw'][:, q['column']]*q['scale']+q['intercept'] for q in c['terms'][:2]]]
        # Existing signed wheel calibrations and chassis yaw give two implied
        # midpoint speeds under the no-slip hypothesis.
        implied = np.c_[wheel[:, 0]+.5*c['track_width_m']*m[:, 2], wheel[:, 1]-.5*c['track_width_m']*m[:, 2]]
        midpoint = trailing(wheel.mean(1), d['imu_valid'])
        dv = derivative(midpoint, d['t'], d['imu_valid'])
        individual_dv = np.c_[*[derivative(implied[:, j], d['t'], d['imu_valid']) for j in (0, 1)]]
        asymmetry = trailing(np.abs(implied[:, 0]-implied[:, 1]), d['imu_valid'])
        out.append(dict(e, base_motion=m, accel_x=acceleration_features(e), wheel_midpoint=midpoint,
                        wheel_dv=dv, individual_wheel_dv=individual_dv, wheel_asymmetry=asymmetry))
    return out


def fit_acceleration(entries):
    models = {}
    for setup in sorted({e['setup'] for e in entries}):
        es = [e for e in entries if e['setup'] == setup]
        xx = []; yy = []; groups = []
        for e in es:
            target = observed_acceleration(e); ids = np.flatnonzero(np.isfinite(target))[::5]
            xx.append(e['accel_x'][ids]); yy.append(target[ids]); groups.extend([e['group']]*len(ids))
        x = np.concatenate(xx); y = np.concatenate(yy)
        counts = Counter(groups); weights = np.array([1/counts[g] for g in groups]); weights /= weights.sum()
        mean = (x*weights[:, None]).sum(0)
        std = np.maximum(np.sqrt(((x-mean)**2*weights[:, None]).sum(0)), 1e-5)
        z = np.c_[(x-mean)/std, np.ones(len(x))]
        reg = ACC_ALPHA*np.eye(z.shape[1]); reg[-1, -1] = 0.
        coef = np.linalg.solve(z.T@(z*weights[:, None])+reg, z.T@(y*weights))
        cap = max(.1, float(np.quantile(np.abs(y), .995)))
        pred = np.clip(z@coef, -cap, cap)
        q = dict(mean=mean.tolist(), std=std.tolist(), coef=coef.tolist(), cap=cap,
                 samples=len(x), fitting_weighted_acceleration_rmse_mps2=float(np.sqrt(np.sum(weights*(pred-y)**2))))
        models[setup] = q
    return models


def predicted_acceleration(e, model):
    q = model[e['setup']]
    z = np.c_[(e['accel_x']-q['mean'])/q['std'], np.ones(len(e['accel_x']))]
    pred = np.clip(z@q['coef'], -q['cap'], q['cap'])
    return trailing(pred, e['data']['imu_valid'])


def thresholds(entries, acceleration):
    result = {}
    for setup in sorted(acceleration):
        decels = []; mismatches = []; asymmetries = []; residuals = []; speeds = []
        for e in entries:
            if e['setup'] != setup:
                continue
            ids = np.flatnonzero(e['label'])[::5]
            dv = e['wheel_dv'][ids]; acc = predicted_acceleration(e, acceleration)[ids]
            decels.extend((-dv[dv < -.05]).tolist())
            braking = dv < -.05
            positive = acc[braking]-dv[braking]
            mismatches.extend(positive[positive > 0].tolist())
            asymmetries.extend(e['wheel_asymmetry'][ids].tolist())
            residuals.extend(np.abs(e['data']['gt_v'][ids]-e['base_motion'][ids, 0]).tolist())
            speeds.extend(np.abs(e['data']['gt_v'][ids]).tolist())
        # Quantiles are fixed before scoring the held participants. Floors merely
        # suppress numerical near-zero events in empirically calibrated units.
        result[setup] = dict(deceleration=max(.10, float(np.quantile(decels, GATE_QUANTILES['deceleration']))),
            wheel_body_mismatch=max(.10, float(np.quantile(mismatches, GATE_QUANTILES['wheel_body_mismatch']))),
            wheel_asymmetry=max(.05, float(np.quantile(asymmetries, GATE_QUANTILES['wheel_asymmetry']))),
            correction_cap_mps=max(.10, float(np.quantile(residuals, .995))),
            speed_cap_mps=max(.20, float(np.quantile(speeds, .995))))
    return result


def bridge(e, acceleration_model, gate_model):
    d = e['data']; t = d['t']; valid = d['imu_valid']; m = e['base_motion']; n = len(t)
    acceleration = predicted_acceleration(e, acceleration_model); q = gate_model[e['setup']]
    concurrent = e['wheel_dv'] < -q['deceleration']
    asymmetric = (e['wheel_asymmetry'] > q['wheel_asymmetry']) & (np.min(e['individual_wheel_dv'], axis=1) < -q['deceleration'])
    decel = np.where(asymmetric, np.minimum(e['wheel_dv'], np.min(e['individual_wheel_dv'], axis=1)), e['wheel_dv'])
    disagreement = acceleration-decel > q['wheel_body_mismatch']
    gate = valid & (concurrent | asymmetric) & disagreement & (m[:, 0] > .05)
    correction = np.zeros(n); active = np.zeros(n, bool); events = []
    for start, stop in runs(valid):
        i = start
        while i < stop-3:
            if not gate[i:i+3].all():
                i += 1
                continue
            anchor = max(start, int(np.searchsorted(t, t[i]-ANCHOR_LOOKBACK_S)))
            anchor_speed = m[anchor, 0]
            if anchor_speed <= .10:
                i += 1
                continue
            speed = anchor_speed
            for j in range(anchor+1, i+1):
                speed += .5*(acceleration[j-1]+acceleration[j])*(t[j]-t[j-1])
            if speed <= m[i, 0]+.02:
                i += 1
                continue
            event_start = i; j = i
            while j < stop and t[j]-t[event_start] < MAX_BRIDGE_S:
                if j > event_start:
                    speed += .5*(acceleration[j-1]+acceleration[j])*(t[j]-t[j-1])
                speed = np.clip(speed, 0., min(q['speed_cap_mps'], 1.05*anchor_speed))
                elapsed = t[j]-t[event_start]
                # Smooth onset and release inside the strict one-second window.
                taper = min(1., elapsed/.05, max(0., (MAX_BRIDGE_S-elapsed)/.15))
                correction[j] = taper*np.clip(speed-m[j, 0], 0., q['correction_cap_mps'])
                active[j] = correction[j] > 0.
                if j > event_start+5 and speed <= m[j, 0]+.01:
                    break
                if j > event_start+5 and e['wheel_dv'][j] > q['deceleration']:
                    break
                j += 1
            if active[event_start:j+1].any():
                events.append(dict(start=event_start, end=min(j, stop-1), anchor=anchor,
                                   start_s=float(t[event_start]), end_s=float(t[min(j, stop-1)]),
                                   asymmetric=bool(asymmetric[event_start]), concurrent=bool(concurrent[event_start])))
            # At least0.25s cooldown prevents one-second bridges chaining forever.
            i = max(j+1, int(np.searchsorted(t, t[event_start]+MAX_BRIDGE_S+.25)))
    stats = dict(id=e['row']['id'], participant=e['row']['participant'], condition=e['row']['condition'],
        eligible_gate_frames=int(gate.sum()), concurrent_gate_frames=int((gate & concurrent).sum()),
        asymmetric_gate_frames=int((gate & asymmetric).sum()), events=len(events), active_frames=int(active.sum()),
        bridge_added_distance_m=float(np.trapezoid(correction, t)), maximum_bridge_correction_mps=float(correction.max()))
    return correction, acceleration, active, events, stats


def evaluate(entries, acceleration, gate, cfg, cache=None):
    records = {blend: [] for blend in BLENDS}; local = []; diagnostics = []
    for e in entries:
        extra, apred, active, events, stats = bridge(e, acceleration, gate); diagnostics.append(stats)
        d = e['data']; arrays = dict(time_s=d['t'], reference_xy_m=d['gt_xy'], reference_heading_rad=d['gt_heading'],
            reference_valid=d['gt_valid'], imu_valid=d['imu_valid'], bridge_speed_correction_mps=extra,
            bridge_active=active, predicted_center_acceleration_mps2=apred, wheel_midpoint_speed_mps=e['wheel_midpoint'], wheel_acceleration_mps2=e['wheel_dv'])
        reference_heading = None
        for blend in BLENDS:
            m = e['base_motion'].copy(); m[:, 0] += blend*extra
            xy, heading = integrate(d, m)
            if reference_heading is None:
                reference_heading = heading
            elif not np.array_equal(reference_heading, heading):
                raise RuntimeError('Bridge altered heading')
            record = dict(id=e['row']['id'], participant=e['row']['participant'], condition=e['row']['condition'], **metrics(d, xy, heading, cfg))
            records[blend].append(record)
            prefix = 'bridge_'+str(blend).replace('.', 'p')
            arrays[prefix+'_xy_m'] = xy; arrays[prefix+'_heading_rad'] = heading; arrays[prefix+'_motion'] = m
            for number, event in enumerate(events):
                a, b = event['start'], event['end']
                # Event support is exact observed endpoints; no filling or choosing
                # endpoints according to trajectory fit.
                supported = bool(d['gt_valid'][a] and d['gt_valid'][b] and b > a)
                value = float(np.linalg.norm((xy[b]-xy[a])-(d['gt_xy'][b]-d['gt_xy'][a]))) if supported else None
                local.append(dict(id=e['row']['id'], participant=e['row']['participant'], condition=e['row']['condition'], blend=blend,
                                  event=number, start_s=event['start_s'], end_s=event['end_s'], observed_endpoints_supported=supported,
                                  interval_displacement_error_m=value, asymmetric=event['asymmetric'], concurrent=event['concurrent']))
        if cache is not None:
            np.savez_compressed(cache/(e['row']['id']+'.npz'), **arrays)
    return records, local, diagnostics


def acceleration_diagnostics(entries, model):
    rows = []
    for e in entries:
        target = observed_acceleration(e); pred = predicted_acceleration(e, model); mask = np.isfinite(target)
        rows.append(dict(id=e['row']['id'], participant=e['row']['participant'], condition=e['row']['condition'],
                         samples=int(mask.sum()), acceleration_rmse_mps2=float(np.sqrt(np.mean((pred[mask]-target[mask])**2))) if mask.any() else None))
    return rows


def main():
    torch.set_num_threads(4); started = time.perf_counter()
    if OUT.exists():
        raise RuntimeError('Preserve prior bridge run')
    OUT.mkdir(); (OUT/'trajectories').mkdir()
    save_json(OUT/'protocol.json', dict(blends=BLENDS, bridge_duration_cap_s=MAX_BRIDGE_S, anchor_lookback_s=ANCHOR_LOOKBACK_S,
        correction='Positive forward-speed bridge only; original yaw and lateral untouched', features='Center startup-gravity-aligned acceleration3 + gyro3 + norms + gyro squared; zero temporal context',
        acceleration_supervision='Derivative of original observed TRAIN forward velocity only,trim50ms edges',
        acceleration_ridge_alpha=ACC_ALPHA, gate_quantiles=GATE_QUANTILES, gate='Concurrent wheel deceleration or asymmetric implied midpoint speed disagreement; center acceleration inconsistent with wheel deceleration; forward pre-brake speed present',
        inferential_limit='Empirically calibrated wheel/body inconsistency is not uniquely identifiable tire slip',
        selection='Minimum equal-participant observed trajectory RMSE in No3/8/15/20 training fold under<=5% worst-participant regression versus blend0',
        fold=sorted(FOLD), v21_correction_refitted_within_fold=True,
        caveat='Inherited neural predictor and calibration remain fixed and previously saw held training participants; conditional experiment, not full nested validation.',
        test_accessed=False, validation_used_for_selection=False))
    source = ROOT/'outputs_observed_reference_v7'; cfg = json.loads((source/'run.json').read_text())['settings']
    cal = json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    train = load_train(ROOT/'outputs_motion_endpoint_v16')
    fitting = [e for e in train if e['row']['participant'] not in FOLD]
    inner = [e for e in train if e['row']['participant'] in FOLD]
    base = refit_base(fitting); fitting_prepared = prepare(fitting, base, cal); inner_prepared = prepare(inner, base, cal)
    acceleration = fit_acceleration(fitting_prepared); gate = thresholds(fitting_prepared, acceleration)
    save_json(OUT/'inner_model.json', dict(base=base, acceleration=acceleration, gate=gate, fitting_ids=[e['row']['id'] for e in fitting]))
    records, local, diagnostics = evaluate(inner_prepared, acceleration, gate, cfg)
    write_csv(OUT/'inner_event_displacement.csv', local); write_csv(OUT/'inner_detection.csv', diagnostics)
    write_csv(OUT/'inner_acceleration_diagnostics.csv', acceleration_diagnostics(inner_prepared, acceleration))
    (_, people, _)=summarize(records[0.]); basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people}
    candidates=[]; innertrials=[]; innerpeople=[]
    for blend in BLENDS:
        summary, people, _ = summarize(records[blend])
        supported=[q['interval_displacement_error_m'] for q in local if q['blend']==blend and q['observed_endpoints_supported']]
        result=dict(blend=blend,score=summary['equal_participant_mean_position_rmse_m'],
            worst_person_ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in people),
            supported_braking_intervals=len(supported),braking_interval_displacement_rmse_m=float(np.sqrt(np.mean(np.square(supported)))) if supported else None)
        candidates.append(result);innertrials.extend(dict(blend=blend,**r) for r in records[blend]);innerpeople.extend(dict(blend=blend,**r) for r in people)
        print('Training-fold bridge',result,flush=True)
    selected=min((c for c in candidates if c['worst_person_ratio']<=1.05),key=lambda q:q['score'])
    save_json(OUT/'selection.json',dict(selected=selected,candidates=candidates,selected_before_validation=True))
    write_csv(OUT/'inner_trials.csv',innertrials);write_csv(OUT/'inner_participants.csv',innerpeople)
    del fitting,inner,fitting_prepared,inner_prepared,records
    base=refit_base(train);prepared=prepare(train,base,cal);acceleration=fit_acceleration(prepared);gate=thresholds(prepared,acceleration)
    original=json.loads((ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text())
    delta=max(float(np.max(np.abs(np.array(base['fits'][k]['weights'])-original['fits'][k]['weights']))) for k in base['fits'])
    if delta>1e-6:raise RuntimeError('Refitted v21 control coefficients differ')
    save_json(OUT/'model.json',dict(base=base,acceleration=acceleration,gate=gate,selected=selected,training_ids=[e['row']['id'] for e in train],control_coefficient_difference=delta))
    write_csv(OUT/'training_acceleration_diagnostics.csv',acceleration_diagnostics(prepared,acceleration))
    trainpeople={e['row']['participant'] for e in train};del train,prepared
    manifest=json.loads((source/'artifact_manifest.json').read_text());ridge=load_observed_ridge()
    states={q['id']:q for q in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
    validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        if row['participant'] in trainpeople:raise RuntimeError('Participant leakage')
        motion=ridge(sensor(d));x=feature_matrix(sensor(d),motion,cal[row['setup']],states[row['id']],'gravity_rotation')
        label=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])
        validation.append(dict(row=row,data=d,motion=motion,linear=x,nonlinear=nonlinear_features(x),setup=row['setup'],label=label))
    prepared=prepare(validation,base,cal);records,local,diagnostics=evaluate(prepared,acceleration,gate,cfg,OUT/'trajectories')
    write_csv(OUT/'validation_detection.csv',diagnostics);write_csv(OUT/'validation_event_displacement.csv',local)
    write_csv(OUT/'validation_acceleration_diagnostics.csv',acceleration_diagnostics(prepared,acceleration))
    summaries={}
    for blend,rows in records.items():
        key='bridge_'+str(blend).replace('.','p');summaries[key],people,maneuvers=summarize(rows)
        for suffix,values in [('trials',rows),('participants',people),('maneuvers',maneuvers)]:write_csv(OUT/(key+'_'+suffix+'.csv'),values)
    expected=json.loads((ROOT/'outputs_trajectory_best_v21/summary.json').read_text())['models']['Nonlinear interval correction v21']['equal_participant_mean_position_rmse_m']
    if abs(summaries['bridge_0p0']['equal_participant_mean_position_rmse_m']-expected)>1e-8:raise RuntimeError('Bridge0 control score differs')
    result=dict(summary=summaries,selected=selected,training_trials=473,validation_trials=71,
        validation_detected_events=sum(q['events'] for q in diagnostics),validation_active_bridge_frames=sum(q['active_frames'] for q in diagnostics),
        test_accessed=False,validation_used_for_selection=False,calibration_refitted=False,inherited_base_refitted=False,v21_correction_refitted_within_fold=True,
        control_coefficient_difference=delta,runtime_seconds=time.perf_counter()-started,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',ROOT/'outputs_nonlinear_endpoint_v21/model.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json']})
    save_json(OUT/'run.json',result)
    lines=['# Braking center-acceleration bridge v34','','A training-fitted center-IMU acceleration model advances pre-brake forward speed for at most1second when empirical wheel/body braking disagreement is present. Blend candidates0/.25/.5; positive bounded forward correction only. Yaw/lateral unchanged. This is distinct from v28 additive motion regression.','',f'Training-fold selection: {selected}','','| Blend | Validation RMSE(mm) |','|---|---:|']
    lines += [f'| {blend} | {summaries["bridge_"+str(blend).replace(".","p")]["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for blend in BLENDS]
    lines += ['',f'Detected validation events: {result["validation_detected_events"]}; active100Hz bridge frames: {result["validation_active_bridge_frames"]}. Original observed masks unchanged; originalv21 refit/control reproduced. All473 training cases used. Test untouched. Empirical disagreement can also arise from scaling/timing/tilt; no uniquely identified slip claim. Conditional inherited-base/calibration limitation remains.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}))
    print(json.dumps(result,indent=2),flush=True)


def finish_from_saved_predictions():
    """Finish summary after diagnostics repair without refitting or retuning."""
    started=time.perf_counter()
    if (OUT/'run.json').exists():raise RuntimeError('Already complete')
    model=json.loads((OUT/'model.json').read_text());selected=model['selected']
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text());records={blend:[] for blend in BLENDS};accdiag=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        with np.load(OUT/'trajectories'/(row['id']+'.npz'),allow_pickle=False) as z:
            if not np.array_equal(z['reference_valid'],d['gt_valid']):raise RuntimeError('Saved prediction reference mask differs')
            for blend in BLENDS:
                prefix='bridge_'+str(blend).replace('.','p')
                records[blend].append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,z[prefix+'_xy_m'],z[prefix+'_heading_rad'],cfg)))
            label=d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])
            target=observed_acceleration(dict(data=d,label=label));mask=np.isfinite(target);pred=z['predicted_center_acceleration_mps2']
            accdiag.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],samples=int(mask.sum()),
                acceleration_rmse_mps2=float(np.sqrt(np.mean((pred[mask]-target[mask])**2))) if mask.any() else None))
    write_csv(OUT/'validation_acceleration_diagnostics.csv',accdiag)
    summaries={}
    for blend,rows in records.items():
        key='bridge_'+str(blend).replace('.','p');summaries[key],people,maneuvers=summarize(rows)
        for suffix,values in [('trials',rows),('participants',people),('maneuvers',maneuvers)]:write_csv(OUT/(key+'_'+suffix+'.csv'),values)
    expected=json.loads((ROOT/'outputs_trajectory_best_v21/summary.json').read_text())['models']['Nonlinear interval correction v21']['equal_participant_mean_position_rmse_m']
    if abs(summaries['bridge_0p0']['equal_participant_mean_position_rmse_m']-expected)>1e-8:raise RuntimeError('Bridge0 control score differs')
    with (OUT/'validation_detection.csv').open(newline='',encoding='utf-8') as f:diagnostics=list(csv.DictReader(f))
    result=dict(summary=summaries,selected=selected,training_trials=473,validation_trials=71,
        validation_detected_events=sum(int(q['events']) for q in diagnostics),validation_active_bridge_frames=sum(int(q['active_frames']) for q in diagnostics),
        test_accessed=False,validation_used_for_selection=False,calibration_refitted=False,inherited_base_refitted=False,v21_correction_refitted_within_fold=True,
        control_coefficient_difference=model['control_coefficient_difference'],summary_continuation_seconds=time.perf_counter()-started,
        diagnostic_repair='Validation acceleration diagnostic label construction fixed; frozen saved predictions reused, no refitting/reselection.',
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',ROOT/'outputs_nonlinear_endpoint_v21/model.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json']})
    save_json(OUT/'run.json',result)
    lines=['# Braking center-acceleration bridge v34','','Training-fitted center acceleration advances pre-brake forward speed for at most1second during empirical wheel/body braking disagreement. Positive bounded forward correction only; yaw/lateral untouched. Original observed derivatives only. V21 residual correction is refitted excluding the held training participants; inherited neural/calibration conditional limitation remains.','',f'Training-fold selection: {selected}','','| Blend | Validation RMSE(mm) |','|---|---:|']
    lines += [f'| {blend} | {summaries["bridge_"+str(blend).replace(".","p")]["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for blend in BLENDS]
    lines += ['',f'Detected validation events: {result["validation_detected_events"]}; active100Hz bridge frames: {result["validation_active_bridge_frames"]}. Original masks andv21 control reproduced. All473 training cases used; test untouched. Physical slip is not uniquely identified by empirical disagreement. Nonzero bridges fail the training-fold guard and are rejected.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    if '--finish-from-saved-predictions' in sys.argv:finish_from_saved_predictions()
    else:main()
