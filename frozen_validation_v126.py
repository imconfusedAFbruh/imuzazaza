"""One frozen v125 comparison against reproduced v121/v34; no fitting."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OPENBLAS_NUM_THREADS'] = '4'
import csv
import datetime
import json
from pathlib import Path
import sys
import time
import numpy as np
import pipeline as p
import frozen_validation_v123 as old

OUT = p.ROOT/'outputs_frozen_validation_v126'
GOLD = p.ROOT/'outputs_frozen_validation_v123_exact'
BUNDLES = {'v121': 'models/reservoir_path_v121_completed', 'v125': 'models/axis_prior_v125'}
FROZEN = {'v121': '6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b',
          'v125': '7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2'}


def dual_decision(controls, candidate):
    if set(controls) != {'v34', 'v121'}:
        raise ValueError('Both frozen controls are required')
    decisions = {name: old.decision(rows, candidate) for name, rows in controls.items()}
    return dict(eligible=all(d['eligible'] for d in decisions.values()), controls=decisions)


def metric_match(actual, saved):
    for key, value in actual.items():
        target = saved[key]
        if value is None:
            if target not in ('', None):
                raise ValueError('Historical missing metric changed: '+key)
        elif isinstance(value, bool):
            if str(value) != target:
                raise ValueError('Historical boolean changed: '+key)
        elif isinstance(value, (float, int)):
            if not np.isclose(value, float(target), rtol=old.TOL['trial_rtol'], atol=old.TOL['trial_atol']):
                raise ValueError('Historical metric changed: '+key)
        elif str(value) != target:
            raise ValueError('Historical identity changed: '+key)


def main():
    started = time.perf_counter()
    old.stop_check()
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromNames(['test_frozen_validation_v123', 'test_frozen_validation_v126'])
    if not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful():
        raise RuntimeError('Synthetic validation contracts failed')
    import torch
    from observed_training_experiment import observed_rows
    from dynamic_blend_inference_v34 import load_dynamic_blend, integrate_motion
    from reservoir_inference_v121 import load_reservoir_model
    from stationary_gravity_inference_v14 import initialize_startup
    from metric_contract_v74 import metrics
    torch.set_num_threads(4)
    if torch.cuda.is_available():
        raise RuntimeError('Original CPU calculation required')
    for name, folder in BUNDLES.items():
        if p.digest(p.ROOT/folder/'model.json') != FROZEN[name]:
            raise ValueError('Frozen model changed: '+name)
    OUT.mkdir(exist_ok=False)
    (OUT/'controls').mkdir()
    (OUT/'predictions').mkdir()
    inputs = {}
    def pin(path):
        path = Path(path)
        name, sha = str(path.relative_to(p.ROOT)), p.digest(path)
        if name in inputs and inputs[name] != sha:
            raise ValueError('Input changed during evaluation: '+name)
        inputs[name] = sha
        return sha
    def seal(folder, name):
        pin(folder/'artifact_manifest.json')
        manifest = json.loads((folder/'artifact_manifest.json').read_text())['sha256']
        path = folder/name
        if pin(path) != manifest[name]:
            raise ValueError('Changed sealed input: '+str(path))
        return path
    # Reuse the prior comparison's complete dependency/raw-identity record.
    gold_inputs = json.loads(seal(GOLD, 'input_hashes.json').read_text())
    for name, sha in gold_inputs.items():
        if pin(p.ROOT/name) != sha:
            raise ValueError('Changed v123 input: '+name)
    expected = {}
    for name, filename in (('v34', 'baseline_trials.csv'), ('v121', 'candidate_trials.csv')):
        with seal(GOLD, filename).open(newline='') as stream:
            table = list(csv.DictReader(stream))
        expected[name] = {r['id']: r for r in table}
        if len(table) != len(expected[name]) or len(table) != 71:
            raise ValueError('Expected exactly71 distinct control records')
    if expected['v34'].keys() != expected['v121'].keys():
        raise ValueError('Controls use different records')
    source = p.ROOT/'outputs_observed_reference_v7'
    cfg = json.loads(seal(source, 'run.json').read_text())['settings']
    seal(source, 'qc.csv')
    manifest = json.loads((source/'artifact_manifest.json').read_text())
    cal_path = p.ROOT/'outputs_amended_v2/calibration.json'
    pin(cal_path)
    calibration = json.loads(cal_path.read_text())
    states = json.loads(seal(p.ROOT/'outputs_stationary_gravity_v14', 'initialization.json').read_text())
    previous_states = {r['id']: r for r in states['records']}
    controls_predict = {'v34': load_dynamic_blend(), 'v121': load_reservoir_model()}
    candidate_predict = load_reservoir_model(BUNDLES['v125'])
    for folder in BUNDLES.values():
        model = json.loads((p.ROOT/folder/'model.json').read_text())
        for name in model['dependencies']:
            pin(p.ROOT/name)
        for path in (p.ROOT/folder).iterdir():
            if path.is_file():
                pin(path)
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(p.ROOT) and path.is_file() and path.suffix == '.py':
                pin(path)
    for name in ('frozen_validation_v126.py', 'test_frozen_validation_v126.py',
                 'research_docs/frozen_validation_v126.md', 'research_docs/frozen_validation_decision_v125.md'):
        pin(p.ROOT/name)
    p.save_json(OUT/'protocol.json', dict(candidate='v125', candidate_sha256=FROZEN['v125'],
                control_sha256=FROZEN['v121'], controls=['v34', 'v121'], tolerances=old.TOL,
                validation_ids=sorted(expected['v34']),
                authorization='Renewed user reply: Make the best model ever!!!!!, following the concrete frozen-validation proposal; interpreted as direction to proceed',
                source_and_initial_input_hashes=inputs.copy(), test_accessed=False, refitting=False,
                retuning=False, started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    entries, checks, seen = [], [], set()
    rows = {'v34': [], 'v121': []}
    for row, d, _ in observed_rows(source, cfg, 'validation', manifest):
        old.stop_check()
        ident = row['id']
        if ident not in expected['v34'] or ident in seen:
            raise ValueError('Unexpected or duplicate validation ID')
        seen.add(ident)
        for suffix in ('.npz', '.json'):
            pin(source/'cache'/(ident+suffix))
        for kind in ('imu', 'c3d'):
            pin(p.ROOT/row[kind])
        tt, raw, valid = p.sample_streams(p.imu_streams(p.ROOT/row['imu']), cfg)
        state = initialize_startup(dict(t=tt, raw=raw, imu_valid=valid), calibration[row['setup']])
        state_checks = {key: old.delta(np.asarray(state[key]), np.asarray(previous_states[ident][key]),
                        old.TOL['startup'], key) for key in ('gravity', 'gyro_bias')}
        if state['eligible'] != previous_states[ident]['eligible']:
            raise ValueError('Startup eligibility changed')
        sensor = {k: d[k] for k in ('setup', 't', 'raw', 'imu_valid')}
        sensor['initialization'] = state
        control_arrays = {}
        with np.load(seal(GOLD, str(Path('predictions')/(ident+'.npz')))) as saved:
            for key in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid'):
                if not np.array_equal(d[key], saved[key], equal_nan=True):
                    raise ValueError('Historical reference changed: '+key)
            for name, predictor in controls_predict.items():
                prefix = 'baseline' if name == 'v34' else 'candidate'
                motion = predictor(sensor)
                xy, heading = integrate_motion(d['t'], motion, d['gt_xy'][0], d['gt_heading'][0], d['imu_valid'])
                differences = {key: old.delta(value, saved[prefix+'_'+key], tolerance, name+' '+key)
                    for key, value, tolerance in (('motion', motion, old.TOL['motion']),
                         ('xy', xy, old.TOL['xy_m']), ('heading', heading, old.TOL['heading_rad']))}
                support = old.check_support(d['gt_valid'], saved[prefix+'_xy'], saved[prefix+'_heading'], xy, heading, motion)
                if not np.array_equal(support, saved['scored_support']):
                    raise ValueError('Historical scored support changed')
                record = dict(id=ident, participant=row['participant'], condition=row['condition'],
                              **p.metrics(d, xy, heading, cfg), **metrics(d, xy, heading, motion))
                metric_match(record, expected[name][ident])
                rows[name].append(record)
                checks.append(dict(id=ident, control=name, **state_checks, **differences))
                control_arrays.update({name+'_motion': motion, name+'_xy': xy, name+'_heading': heading})
        np.savez_compressed(OUT/'controls'/(ident+'.npz'), **control_arrays, scored_support=support)
        entries.append((row, d, sensor, control_arrays))
        p.save_json(OUT/'checkpoint.json', dict(stage='control_reproduction', recordings=len(entries), candidate_count=0))
        if len(entries) % 10 == 0:
            print('Both controls reproduced', len(entries), '/71', flush=True)
    if seen != set(expected['v34']) or len(checks) != 142:
        raise ValueError('Incomplete controls')
    summaries = {name: p.summarize(rr)[0] for name, rr in rows.items()}
    for name, score in (('v34', .1007021193993738), ('v121', .09930373516586414)):
        summary = summaries[name]
        if summary['trials'] != 71 or summary['participants'] != 4 or abs(summary['equal_participant_mean_position_rmse_m']-score) > old.TOL['aggregate_m']:
            raise ValueError('Control aggregate changed: '+name)
        if sum(r['scored_frames'] for r in rows[name]) != 105821:
            raise ValueError('Changed control frames')
    p.save_json(OUT/'control_reproduction.json', dict(summaries=summaries, checks=checks, exact_reference_and_support=True))
    p.save_json(OUT/'input_hashes.json', inputs)
    print('All142 control reconstructions pass; starting one frozen v125 candidate', flush=True)
    candidate = []
    for row, d, sensor, controls in entries:
        old.stop_check()
        ident = row['id']
        motion = candidate_predict(sensor)
        xy, heading = integrate_motion(d['t'], motion, d['gt_xy'][0], d['gt_heading'][0], d['imu_valid'])
        for name in ('v34', 'v121'):
            support = old.check_support(d['gt_valid'], controls[name+'_xy'], controls[name+'_heading'], xy, heading, motion)
        candidate.append(dict(id=ident, participant=row['participant'], condition=row['condition'],
                             **p.metrics(d, xy, heading, cfg), **metrics(d, xy, heading, motion)))
        arrays = {k: d[k] for k in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid')}
        np.savez_compressed(OUT/'predictions'/(ident+'.npz'), **arrays, **controls,
                           v125_motion=motion, v125_xy=xy, v125_heading=heading, scored_support=support)
        p.write_csv(OUT/'v125_trials.csv', candidate)
        p.save_json(OUT/'checkpoint.json', dict(stage='candidate_evaluation', recordings=71, candidate_count=len(candidate)))
        if len(candidate) % 10 == 0:
            print('Frozen candidate evaluated', len(candidate), '/71', flush=True)
    if len(candidate) != 71 or sum(r['scored_frames'] for r in candidate) != 105821:
        raise ValueError('Candidate recording/frame support changed')
    result = dual_decision(rows, candidate)
    for name, rr in {**rows, 'v125': candidate}.items():
        p.write_csv(OUT/(name+'_trials.csv'), rr)
        _, people, maneuvers = p.summarize(rr)
        p.write_csv(OUT/(name+'_participants.csv'), people)
        p.write_csv(OUT/(name+'_maneuvers.csv'), maneuvers)
    for name, sha in inputs.items():
        if p.digest(p.ROOT/name) != sha:
            raise ValueError('Input changed during evaluation: '+name)
    p.save_json(OUT/'input_hashes.json', inputs)
    p.save_json(OUT/'run.json', dict(decision=result, validation_trials=71, validation_accessed=True,
                test_accessed=False, refitting=False, retuning=False, promotion=False, complete_support=True,
                runtime_seconds=time.perf_counter()-started, review_status='pending',
                interpretation='Previously exposed development validation; not a blind final test'))
    p.save_json(OUT/'checkpoint.json', dict(stage='complete', recordings=71, candidate_count=71))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={str(f.relative_to(OUT)): p.digest(f)
                for f in OUT.rglob('*') if f.is_file() and f.name != 'artifact_manifest.json'}))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    existed_before = OUT.exists()
    try:
        main()
    except BaseException as exc:
        if not existed_before and OUT.exists() and not (OUT/'run.json').exists():
            p.save_json(OUT/'failure.json', dict(error=repr(exc), candidate_not_accepted=True,
                instruction='Preserve attempt and diagnose; no retuning or tolerance relaxation'))
        raise
