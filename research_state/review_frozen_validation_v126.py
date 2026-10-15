"""Independent sealed v126 arithmetic; never opens raw or validation caches."""
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs_frozen_validation_v126'
REPORT = ROOT/'outputs_frozen_validation_v126_report'
GOLD = ROOT/'outputs_frozen_validation_v123_exact'
NAMES = ('v34', 'v121', 'v125')
GUARDS = ('Position_P95_mm', 'Last_Supported_Endpoint_Error_mm', 'heading_rmse_deg')
TOL = dict(xy_m=1e-8, aggregate_m=1e-9, motion=1e-7, startup=1e-10,
           heading_rad=1e-8, trial_atol=1e-9, trial_rtol=1e-10)
GOLD_MANIFEST_SHA256 = '13c5a1f9b0e33c9c01cb01e4918d45b34580b4efa9c113896a6c9479081b164f'
MODELS = {
    'models/reservoir_path_v121_completed': '6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b',
    'models/axis_prior_v125': '7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2',
}
SOURCES = {
    'frozen_validation_v126.py': '55bd72732342db3ebfd4bb496363207d4ca7eafe359224a94852aff2148e8d53',
    'test_frozen_validation_v126.py': '7c8a53742848040c7123b59765bbc230fb4ab96ab319ace210a631c26d1698ee',
    'report_frozen_validation_v126.py': 'd2ba88b5f2dc41a21cf01780c722cc294211c66fabf41b1ca3717a3425827100',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def table(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalized(mapping):
    result = {name.replace('\\', '/'): value for name, value in mapping.items()}
    assert len(result) == len(mapping), 'duplicate normalized provenance path'
    return result


def protected(name):
    return name.startswith(('imu3/', 'c3d/', 'outputs_observed_reference_v7/cache/',
                            'outputs_dynamic_blend_v34/trajectories/'))


def hashes(base, mapping):
    for name, expected in normalized(mapping).items():
        relative = (base/name).relative_to(ROOT).as_posix()
        assert not protected(relative), ('raw/cache access forbidden', relative)
        path = (base/name).resolve()
        assert path.is_relative_to(ROOT), name
        assert digest(path) == expected, ('hash mismatch', name)
    return len(mapping)


def seal(folder, expected=None):
    manifest = normalized(read(folder/'artifact_manifest.json')['sha256'])
    actual = {f.relative_to(folder).as_posix() for f in folder.rglob('*')
              if f.is_file() and f.name != 'artifact_manifest.json'}
    assert actual == set(manifest), ('output coverage', folder, actual ^ set(manifest))
    if expected is not None:
        assert actual == expected, ('unexpected output', folder, actual ^ expected)
    return hashes(folder, manifest)


def close(actual, saved, label, atol=1e-10):
    assert math.isfinite(actual) and math.isfinite(float(saved)), (label, actual, saved)
    assert np.isclose(actual, float(saved), rtol=1e-10, atol=atol), (label, actual, saved)


def number(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) else None


def average(records, key, group=None):
    if group:
        return {label: average([r for r in records if r[group] == label], key)
                for label in sorted({r[group] for r in records})}
    by_person = defaultdict(list)
    for row in records:
        value = number(row[key])
        if value is not None:
            by_person[row['participant']].append(value)
    return statistics.mean(statistics.mean(values) for values in by_person.values()) if by_person else None


def ratio(value, baseline):
    assert math.isfinite(value) and math.isfinite(baseline) and min(value, baseline) >= 0.
    return value/baseline if baseline else (1. if value == 0. else None)


def delta(actual, expected, tolerance, label):
    assert actual.shape == expected.shape and actual.dtype == expected.dtype, label
    assert np.array_equal(np.isnan(actual), np.isnan(expected)), (label, 'NaN mask')
    assert np.array_equal(np.isfinite(actual), np.isfinite(expected)), (label, 'finite mask')
    valid = np.isfinite(expected)
    maximum = float(np.max(np.abs(actual[valid]-expected[valid]))) if valid.any() else 0.
    assert maximum <= tolerance, (label, maximum, tolerance)
    return maximum


def integrate(z, motion):
    velocity = (motion[1:]+motion[:-1])/2
    dt = np.diff(z['t'])
    heading = np.r_[0., np.cumsum(dt*velocity[:, 2])]+z['gt_heading'][0]
    angle = (heading[1:]+heading[:-1])/2
    steps = dt[:, None]*np.c_[velocity[:, 0]*np.cos(angle)-velocity[:, 1]*np.sin(angle),
                              velocity[:, 0]*np.sin(angle)+velocity[:, 1]*np.cos(angle)]
    xy = np.vstack((np.zeros(2), np.cumsum(steps, axis=0)))+z['gt_xy'][0]
    bad = np.flatnonzero(~z['imu_valid'])
    if len(bad):
        xy[bad[0]:], heading[bad[0]:] = np.nan, np.nan
    return xy, heading


def metrics(z, xy, heading):
    valid = z['gt_valid'] & np.isfinite(xy).all(1)
    assert valid.any() and np.isfinite(z['gt_xy'][valid]).all()
    assert np.isfinite(heading[valid]).all() and np.isfinite(z['gt_heading'][valid]).all()
    errors = np.linalg.norm(xy[valid]-z['gt_xy'][valid], axis=1)
    difference = heading[valid]-z['gt_heading'][valid]
    wrapped = np.arctan2(np.sin(difference), np.cos(difference))
    return dict(position_rmse_m=float(np.sqrt(np.mean(errors**2))),
                Position_P95_mm=float(np.percentile(errors, 95)*1000),
                Last_Supported_Endpoint_Error_mm=float(errors[-1]*1000),
                heading_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(wrapped**2)))),
                scored_frames=int(valid.sum()), Valid_Frame_Count=int(valid.sum()),
                reference_coverage=float(z['gt_valid'].mean()),
                reconstruction_coverage=float(np.isfinite(xy).all(1).mean()),
                ATE_RMSE_m=float(np.sqrt(np.mean(errors**2))),
                ATE_RMSE_mm=float(np.sqrt(np.mean(errors**2))*1000)), valid


def summary(records):
    return dict(trials=len(records), participants=len({r['participant'] for r in records}),
                equal_participant_mean_position_rmse_m=average(records, 'position_rmse_m'),
                equal_participant_mean_heading_rmse_deg=average(records, 'heading_rmse_deg'))


def decision(base, candidate):
    actual = dict(participant_ratios={}, maneuver_ratios={}, guard_ratios={})
    for category, group in (('participant_ratios', 'participant'), ('maneuver_ratios', 'condition')):
        values, references = average(candidate, 'position_rmse_m', group), average(base, 'position_rmse_m', group)
        assert set(values) == set(references)
        actual[category] = {label: ratio(value, references[label]) for label, value in values.items()}
    actual['guard_ratios'] = {key: ratio(average(candidate, key), average(base, key)) for key in GUARDS}
    failures = [label for category in actual.values() for label, value in category.items() if value is None or value > 1.05]
    if average(candidate, 'position_rmse_m') >= average(base, 'position_rmse_m'):
        failures.append('mean_ATE_not_lower')
    return dict(eligible=not failures, failed_guards=failures, baseline=summary(base), candidate=summary(candidate), **actual)


def sensitivity(benefits):
    values = np.asarray(benefits, dtype=float)
    omitted = np.array([np.delete(values, i).mean() for i in range(4)])
    draws = np.random.default_rng(122).integers(0, 4, size=(4096, 4))
    interval = np.quantile(values[draws].mean(axis=1), [.025, .975])
    signs = np.where((np.arange(16)[:, None] >> np.arange(4)) & 1, 1., -1.)
    means = np.mean(signs*values, axis=1)
    count = int(np.count_nonzero(np.abs(means) >= abs(float(values.mean()))-1e-12))
    return omitted, interval, count


def self_check():
    assert ratio(0., 0.) == 1. and ratio(1., 0.) is None
    assert average([{'participant': 'A', 'x': 1.}]*3+[{'participant': 'B', 'x': 9.}], 'x') == 5.
    omitted, interval, count = sensitivity([2., 2., 2., 2.])
    assert np.array_equal(omitted, np.full(4, 2.)) and np.array_equal(interval, [2., 2.]) and count == 2
    t = np.arange(0., 1.01, .01)
    z = dict(t=t, gt_xy=np.c_[t, np.zeros(len(t))], gt_heading=np.zeros(len(t)),
             gt_valid=np.ones(len(t), bool), imu_valid=np.ones(len(t), bool))
    motion = np.c_[np.ones(len(t)), np.zeros((len(t), 2))]
    xy, heading = integrate(z, motion)
    measured, valid = metrics(z, xy+[.003, .004], heading+2*np.pi)
    assert valid.all() and abs(measured['ATE_RMSE_mm']-5.) < 1e-10 and measured['heading_rmse_deg'] < 1e-10


def main():
    self_check()
    assert read(OUT/'checkpoint.json') == dict(stage='complete', recordings=71, candidate_count=71)
    assert digest(GOLD/'artifact_manifest.json') == GOLD_MANIFEST_SHA256
    gold_manifest = normalized(read(GOLD/'artifact_manifest.json')['sha256'])
    gold_inputs = normalized(read(GOLD/'input_hashes.json'))
    assert digest(GOLD/'input_hashes.json') == gold_manifest['input_hashes.json']
    protocol, run = read(OUT/'protocol.json'), read(OUT/'run.json')
    inputs = normalized(read(OUT/'input_hashes.json'))
    initial = normalized(protocol['source_and_initial_input_hashes'])
    assert len(inputs) == 524 and len(initial) == 453 and len(gold_inputs) == 429
    assert protocol['tolerances'] == TOL and protocol['controls'] == ['v34', 'v121']
    assert protocol['candidate'] == 'v125' and protocol['candidate_sha256'] == MODELS['models/axis_prior_v125']
    assert protocol['control_sha256'] == MODELS['models/reservoir_path_v121_completed']
    assert 'interpreted as direction to proceed' in protocol['authorization']
    assert all(protocol[key] is False for key in ('test_accessed', 'refitting', 'retuning'))
    assert all(run[key] is False for key in ('test_accessed', 'refitting', 'retuning', 'promotion'))
    assert run['validation_accessed'] is True and run['complete_support'] is True and run['validation_trials'] == 71
    ids = protocol['validation_ids']
    assert len(ids) == len(set(ids)) == 71
    expected_initial = set(gold_inputs) | {f'outputs_frozen_validation_v123_exact/{name}'
        for name in ('artifact_manifest.json', 'input_hashes.json', 'baseline_trials.csv', 'candidate_trials.csv')}
    expected_initial |= {'frozen_validation_v126.py', 'test_frozen_validation_v126.py',
                         'research_docs/frozen_validation_v126.md', 'research_docs/frozen_validation_decision_v125.md'}
    model_outputs = {}
    for folder, sha in MODELS.items():
        path = ROOT/folder
        assert digest(path/'model.json') == sha
        model = read(path/'model.json')
        model_outputs[folder] = seal(path)
        expected_initial |= {folder+'/'+f.name for f in path.iterdir() if f.is_file()}
        expected_initial |= set(normalized(model['dependencies']))
        assert all(initial[name] == expected for name, expected in normalized(model['dependencies']).items())
    assert set(initial) == expected_initial, ('initial pin coverage', set(initial) ^ expected_initial)
    predictions = {f'outputs_frozen_validation_v123_exact/predictions/{ident}.npz': gold_manifest[f'predictions/{ident}.npz'] for ident in ids}
    assert inputs == {**initial, **predictions}, 'final pin coverage differs from initial pins plus71 saved controls'
    assert all(inputs[name] == sha for name, sha in gold_inputs.items()), 'changed prior input identity pin'
    deferred = {name: sha for name, sha in inputs.items() if protected(name)}
    assert all(name in gold_inputs and sha == gold_inputs[name] for name, sha in deferred.items())
    expected_outputs = {'protocol.json', 'run.json', 'input_hashes.json', 'checkpoint.json', 'control_reproduction.json'}
    expected_outputs |= {f'{name}_{kind}.csv' for name in NAMES for kind in ('trials', 'participants', 'maneuvers')}
    expected_outputs |= {f'{kind}/{ident}.npz' for kind in ('controls', 'predictions') for ident in ids}
    counts = dict(output=seal(OUT, expected_outputs), input_pins=len(inputs), inherited_pins=len(gold_inputs),
                  input_content_rehashed=hashes(ROOT, {name: sha for name, sha in inputs.items() if not protected(name)}),
                  input_prior_pin_equality_without_content_access=len(deferred), source=hashes(ROOT, SOURCES), model_outputs=model_outputs)
    for name in ('frozen_validation_v126.py', 'test_frozen_validation_v126.py'):
        assert initial[name] == SOURCES[name]
    plan_sha = initial['research_docs/frozen_validation_v126.md']
    assert digest(ROOT/'research_docs/frozen_validation_v126.md') == plan_sha
    rows = {name: table(OUT/(name+'_trials.csv')) for name in NAMES}
    indexed = {name: {r['id']: r for r in rr} for name, rr in rows.items()}
    assert all(len(rr) == len(indexed[name]) == 71 and set(indexed[name]) == set(ids) for name, rr in rows.items())
    assert {r['participant'] for r in rows['v34']} == {'No.5', 'No.10', 'No.14', 'No.18'}
    assert len({r['condition'] for r in rows['v34']}) == 7
    old_rows = {'v34': table(GOLD/'baseline_trials.csv'), 'v121': table(GOLD/'candidate_trials.csv')}
    for name, filename in (('v34', 'baseline_trials.csv'), ('v121', 'candidate_trials.csv')):
        assert digest(GOLD/filename) == gold_manifest[filename]
        previous = {r['id']: r for r in old_rows[name]}
        assert len(previous) == len(old_rows[name]) == 71 and set(previous) == set(ids)
        for ident in ids:
            saved, actual = previous[ident], indexed[name][ident]
            assert set(saved) == set(actual)
            for key, value in saved.items():
                numeric = number(value)
                if numeric is None:
                    assert actual[key] == value, (name, ident, key)
                else:
                    close(float(actual[key]), numeric, (name, ident, key), TOL['trial_atol'])
    reproduction = read(OUT/'control_reproduction.json')
    reproduction_index = {(r['id'], r['control']): r for r in reproduction['checks']}
    assert len(reproduction_index) == len(reproduction['checks']) == 142
    assert set(reproduction_index) == {(ident, name) for ident in ids for name in ('v34', 'v121')}
    assert reproduction['exact_reference_and_support'] is True
    records = {name: [] for name in NAMES}
    frames, maxima = Counter(), defaultdict(float)
    paired, reference_arrays, control_arrays = 0, 0, 0
    for ident in ids:
        with np.load(OUT/'predictions'/(ident+'.npz'), allow_pickle=False) as z, \
             np.load(GOLD/'predictions'/(ident+'.npz'), allow_pickle=False) as gold, \
             np.load(OUT/'controls'/(ident+'.npz'), allow_pickle=False) as control:
            assert set(z.files) == {'t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid', 'scored_support'} | {
                name+'_'+key for name in NAMES for key in ('motion', 'xy', 'heading')}
            for key in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid'):
                assert np.array_equal(z[key], gold[key], equal_nan=True), (ident, key)
                reference_arrays += 1
            assert np.isfinite(z['t']).all() and np.all(np.diff(z['t']) > 0.)
            assert z['gt_valid'].dtype == z['imu_valid'].dtype == np.dtype(bool)
            for name, prefix in (('v34', 'baseline'), ('v121', 'candidate')):
                check = reproduction_index[(ident, name)]
                assert all(0 <= check[key] <= TOL['startup'] for key in ('gravity', 'gyro_bias'))
                for key, tolerance in (('motion', TOL['motion']), ('xy', TOL['xy_m']), ('heading', TOL['heading_rad'])):
                    maximum = delta(z[name+'_'+key], gold[prefix+'_'+key], tolerance, (ident, name, key))
                    close(maximum, check[key], (ident, name, 'recorded delta', key), 1e-15)
                    maxima[name+'_'+key] = max(maxima[name+'_'+key], maximum)
                    assert np.array_equal(z[name+'_'+key], control[name+'_'+key], equal_nan=True)
                    control_arrays += 1
            support = gold['scored_support']
            assert np.array_equal(z['scored_support'], support) and np.array_equal(control['scored_support'], support)
            for name in NAMES:
                xy, heading, motion = z[name+'_xy'], z[name+'_heading'], z[name+'_motion']
                assert xy.shape == (len(z['t']), 2) and heading.shape == (len(z['t']),) and motion.shape == (len(z['t']), 3)
                assert np.array_equal(np.isfinite(xy), np.isfinite(gold['baseline_xy']))
                assert np.array_equal(np.isfinite(heading), np.isfinite(gold['baseline_heading']))
                assert np.isfinite(motion).all()
                expected_xy, expected_heading = integrate(z, motion)
                np.testing.assert_allclose(xy, expected_xy, rtol=1e-12, atol=1e-12)
                np.testing.assert_allclose(heading, expected_heading, rtol=1e-12, atol=1e-12)
                measured, actual_support = metrics(z, xy, heading)
                assert np.array_equal(actual_support, support)
                saved = indexed[name][ident]
                assert saved['participant'] == indexed['v34'][ident]['participant']
                assert saved['condition'] == indexed['v34'][ident]['condition']
                for key, value in measured.items():
                    close(value, saved[key], (ident, name, key))
                frames[name] += int(actual_support.sum())
                records[name].append(dict(id=ident, participant=saved['participant'], condition=saved['condition'], **measured))
                paired += 1
    assert paired == 213 and reference_arrays == 355 and control_arrays == 426
    assert dict(frames) == {name: 105821 for name in NAMES}
    derived = {name: decision(records[name], records['v125']) for name in ('v34', 'v121')}
    assert set(run['decision']['controls']) == set(derived)
    for control, actual in derived.items():
        saved = run['decision']['controls'][control]
        assert actual['eligible'] == saved['eligible'] and actual['failed_guards'] == saved['failed_guards']
        for category in ('participant_ratios', 'maneuver_ratios', 'guard_ratios', 'baseline', 'candidate'):
            assert set(actual[category]) == set(saved[category])
            for key, value in actual[category].items():
                if value is None:
                    assert saved[category][key] is None
                else:
                    close(value, saved[category][key], (control, category, key))
        for key, value in summary(records[control]).items():
            close(value, reproduction['summaries'][control][key], (control, 'reproduction summary', key))
    eligible = all(value['eligible'] for value in derived.values())
    assert run['decision']['eligible'] == eligible is False
    assert derived['v34']['eligible'] is True
    assert derived['v121']['failed_guards'] == ['OS', 'mean_ATE_not_lower']
    assert derived['v121']['maneuver_ratios']['OS'] > 1.05
    assert all(value > 1. for value in derived['v121']['participant_ratios'].values())
    for name in NAMES:
        close(average(records[name], 'position_rmse_m'), average(rows[name], 'position_rmse_m'), (name, 'CSV ATE'))
        for dimension, filename in (('participant', 'participants'), ('condition', 'maneuvers')):
            saved = table(OUT/f'{name}_{filename}.csv')
            lookup = {r[dimension]: r for r in saved}
            expected = average(records[name], 'position_rmse_m', dimension)
            assert len(lookup) == len(saved) and set(lookup) == set(expected)
            for label, value in expected.items():
                subset = [r for r in records[name] if r[dimension] == label]
                row = lookup[label]
                key = 'mean_trial_position_rmse_m' if dimension == 'participant' else 'equal_participant_mean_position_rmse_m'
                close(value, row[key], (name, dimension, label))
                assert int(row['trials']) == len(subset)
                if dimension == 'participant':
                    close(average(subset, 'heading_rmse_deg'), row['mean_trial_heading_rmse_deg'], (name, label, 'heading'))
                else:
                    assert int(row['participants']) == len({r['participant'] for r in subset})
    report_run = read(REPORT/'run.json')
    report_inputs = normalized(report_run['inputs'])
    expected_report = {f'outputs_frozen_validation_v126/{name}' for name in ('artifact_manifest.json', 'run.json', 'protocol.json')}
    expected_report |= {f'outputs_frozen_validation_v126/{name}_trials.csv' for name in NAMES}
    expected_report |= {'report_frozen_validation_v126.py', 'report_frozen_validation_v123.py', 'reservoir_stability_v122.py', 'pipeline.py',
                        'research_docs/frozen_validation_results_v126.md'}
    expected_report |= {folder+'/'+name for folder in MODELS for name in ('artifact_manifest.json', 'model.json')}
    assert set(report_inputs) == expected_report
    counts.update(report_output=seal(REPORT, {'grouped_metrics.csv', 'run.json', 'stability.json'}), report_input=hashes(ROOT, report_inputs))
    grouped = table(REPORT/'grouped_metrics.csv')
    grouped_map = {(r['model'], r['group_type'], r['group'], r['metric']): r for r in grouped}
    assert len(grouped_map) == len(grouped) == report_run['grouped_rows'] == 2556
    keys, unavailable, partial = set(), 0, 0
    for name, rr in rows.items():
        columns = [key for key in rr[0] if key not in ('id', 'participant', 'condition') and any(number(r[key]) is not None for r in rr)]
        groups = [('overall', 'all', rr)]
        for dimension in ('participant', 'condition'):
            groups += [(dimension, label, [r for r in rr if r[dimension] == label]) for label in sorted({r[dimension] for r in rr})]
        for dimension, label, subset in groups:
            for column in columns:
                key = (name, dimension, label, column)
                keys.add(key)
                saved = grouped_map[key]
                available = [r for r in subset if number(r[column]) is not None]
                expected = dict(available_trials=len(available), total_trials=len(subset), missing_trials=len(subset)-len(available),
                                available_participants=len({r['participant'] for r in available}),
                                total_participants=len({r['participant'] for r in subset}))
                assert all(int(saved[field]) == value for field, value in expected.items()), (key, expected)
                mean = average(subset, column)
                if mean is None:
                    assert saved['equal_person_mean'] == ''
                    unavailable += 1
                else:
                    close(mean, saved['equal_person_mean'], key)
                partial += int(0 < len(available) < len(subset))
    assert keys == set(grouped_map) and report_run['prediction_evaluations'] == 0
    people = sorted({r['participant'] for r in records['v125']})
    benefits = np.array([1000*(average([r for r in rows['v121'] if r['participant'] == person], 'position_rmse_m')
                              -average([r for r in rows['v125'] if r['participant'] == person], 'position_rmse_m')) for person in people])
    stats = read(REPORT/'stability.json')
    assert list(stats['participant_benefits_mm']) == people and (benefits < 0).all()
    for person, value in zip(people, benefits):
        close(value, stats['participant_benefits_mm'][person], ('participant benefit', person))
    omitted, interval, count = sensitivity(benefits)
    close(float(benefits.mean()), stats['mean_benefit_mm'], 'mean benefit')
    np.testing.assert_allclose(omitted, stats['leave_one_person_out_benefits_mm'], rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(interval, stats['bootstrap_percentile95_mm'], rtol=1e-10, atol=1e-10)
    assert stats['participants_improved'] == 0 and stats['sign_flips'] == 16
    assert stats['two_sided_sign_flip_fraction'] == count/16 == .125
    assert stats['previously_exposed_validation_only'] is True
    document = (ROOT/'research_docs/frozen_validation_results_v126.md').read_text(encoding='utf-8')
    baseline, candidate = 1000*average(records['v121'], 'position_rmse_m'), 1000*average(records['v125'], 'position_rmse_m')
    assert 'V125 fails the predeclared dual-control comparison.' in document
    assert 'V125 passes the predeclared dual-control comparison.' not in document
    assert 'Best completed guard-passing validation model: **v121**.' in document
    assert f'v121 **{baseline:.9f} mm** -> v125 **{candidate:.9f} mm**' in document
    assert 'Against v121: FAIL' in document and 'Failed guards: OS, mean_ATE_not_lower.' in document
    assert '0/4 participants improve against v121.' in document
    assert 'Exact sign-flip fraction: 0.125000000 over 16 signs.' in document
    for control, outcome in derived.items():
        for category in ('participant_ratios', 'maneuver_ratios', 'guard_ratios'):
            for label, value in outcome[category].items():
                assert f'| {category} | {label} | {value:.9f} |' in document
    for dimension in ('participant', 'condition'):
        for label in sorted({r[dimension] for r in rows['v125']}):
            values = [1000*average([r for r in rows[name] if r[dimension] == label], 'position_rmse_m') for name in NAMES]
            assert '| '+label+' | '+' | '.join(f'{value:.6f}' for value in values)+' |' in document
    for row in grouped:
        if row['group_type'] == 'overall' and row['metric'] in ('RTE_1s_mm', 'RTE_5s_mm', 'RTE_10s_mm'):
            assert f"| {row['model']}/{row['metric']} | {row['available_trials']}/{row['total_trials']} | {row['available_participants']}/{row['total_participants']} |" in document
    result = dict(status='PASS', reviewed_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Independent saved v126 predictions/core decisions and grouped-report arithmetic; no raw/cache or inference access',
                  hash_counts=counts, captured_preregistration_sha256=plan_sha,
                  recordings=71, participants=4, maneuvers=7, paired_predictions=paired, reference_array_comparisons=reference_arrays,
                  control_array_comparisons=control_arrays, scored_frames=dict(frames), historical_control_maximum_differences=dict(maxima),
                  all213_saved_motion_integrations_passed=True, all_exact_finite_and_scored_masks_passed=True,
                  model_sha256=MODELS, decisions=derived, candidate_eligible=False, best_completed_validation='v121',
                  v121_ATE_mm=baseline, v125_ATE_mm=candidate, benefit_vs_v121_mm=baseline-candidate,
                  grouped_rows_verified=2556, groups_without_values=unavailable, groups_partially_available=partial,
                  participant_benefits_mm=dict(zip(people, benefits.tolist())), participants_improved=0,
                  bootstrap_seed=122, bootstrap_draws=4096, bootstrap_percentile95_mm=interval.tolist(),
                  leave_one_person_out_benefits_mm=omitted.tolist(), exact_sign_flip_count=count, exact_sign_flip_total=16,
                  two_sided_sign_flip_fraction=count/16, report_rejection_and_denominators_verified=True,
                  input_hash_policy='All524 recorded pins verified; protected raw/cache/older trajectory entries compared to sealed v123 pins without opening those files; remaining inputs rehashed.',
                  output_manifest_sha256=digest(OUT/'artifact_manifest.json'), report_manifest_sha256=digest(REPORT/'artifact_manifest.json'),
                  review_script_sha256=digest(Path(__file__)),
                  source_review=dict(one_frozen_candidate='PASS', no_fit_or_retuning='PASS', controls_before_candidate='PASS',
                                     original_tolerances_and_four_CPU_threads='PASS', sensor_only_prediction='PASS', report_input_coverage='PASS', blockers=[]),
                  declined_checks=['Raw acquisitions, validation caches and older v34 trajectory contents not reopened; saved input pins checked against v123',
                                   'Startup gravity/bias recomputation and prediction inference not rerun; sealed142-control audit and reviewed source checked',
                                   'Secondary route/filter-derived values aggregated from sealed CSV, not recomputed from input signals',
                                   'No test, new fitting, alternative candidate, timing/runtime geometry or deployment evaluation'],
                  limitations=['Previously exposed development validation; no blind final generalization or independent significance claim',
                               'V125 is rejected against the primary v121 control despite passing historical v34 guards',
                               'V121 historical controls have floating-point differences up to2.22e-16 within unchanged v123 tolerances'])
    target = ROOT/'research_state/v126_independent_review.json'
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
