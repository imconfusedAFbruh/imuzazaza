"""Independent sealed TRAIN-screen review; no fitting, inference or raw access."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs_axis_prior_v125'
PARENT = ROOT / 'outputs_trial_rmse_v124'
PRIOR = ROOT / 'outputs_reservoir_path_v121'
FOLDS = [
    {'No.3', 'No.8', 'No.15', 'No.20'},
    {'No.1', 'No.4', 'No.13', 'No.16'},
    {'No.6', 'No.7', 'No.17', 'No.19'},
]
CONFIGS = {'speed1_yaw10': [1., 10.], 'speed10_yaw1': [10., 1.],
           'speed3_yaw3': [3., 3.]}
CONTROLS = ('v34', 'v121', 'v124')
NAMES = (*CONTROLS, *CONFIGS)
GUARD_METRICS = ('Position_P95_mm', 'Last_Supported_Endpoint_Error_mm',
                 'heading_rmse_deg')
PREVIOUS_MANIFEST_SHA256 = 'e00ab4b33d90b0af6daaef8d63b41fdeb1c7c3317c9cf47ba03b5f7b3fcbe3b3'
REVIEWED_SOURCES = {
    'axis_prior_v125.py': '906e6501dcb2a5d04d987d4cee20be97ebc4c866e3737a4582c3211ecad7a6d5',
    'test_axis_prior_v125.py': '59b4f384ccb665b14ecd2595e3a93712328006ae4911954c45dea8c78b55791d',
    'research_docs/axis_prior_v125.md': '2a63f6ab81ed52647bdc0d933cb34a6f01bff6ec14e257315b031f4093f506b9',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalized(mapping):
    result = {name.replace('\\', '/'): value for name, value in mapping.items()}
    assert len(result) == len(mapping), 'duplicate normalized provenance path'
    return result


def hashes(base, mapping):
    for name, expected in mapping.items():
        path = (base / name.replace('\\', '/')).resolve()
        assert path.is_relative_to(ROOT), ('outside workspace', name)
        assert digest(path) == expected, ('hash mismatch', name)
    return len(mapping)


def close(actual, saved, label):
    assert np.isfinite(actual) and np.isfinite(float(saved)), (label, actual, saved)
    assert np.isclose(actual, float(saved), rtol=1e-10, atol=1e-10), (label, actual, saved)


def equal(actual, expected, label):
    assert actual.shape == expected.shape and actual.dtype == expected.dtype, label
    assert np.array_equal(actual, expected, equal_nan=True), label


def aggregate(records, key, group=None):
    if group:
        return {value: aggregate([r for r in records if r[group] == value], key)
                for value in sorted({r[group] for r in records})}
    return float(np.mean([np.mean([r[key] for r in records if r['participant'] == person])
                          for person in sorted({r['participant'] for r in records})]))


def ratio(value, baseline):
    return value / baseline if baseline else (1. if value == 0 else float('inf'))


def runs(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def direct_metrics(z, xy, heading):
    valid = z['gt_valid'] & np.isfinite(xy).all(1)
    error = xy[valid] - z['gt_xy'][valid]
    distance = np.linalg.norm(error, axis=1)
    angle = heading[valid] - z['gt_heading'][valid]
    wrapped = np.arctan2(np.sin(angle), np.cos(angle))
    count = int(valid.sum())
    measured = dict(position_rmse_m=float(np.sqrt(np.mean(distance ** 2))),
                    heading_rmse_deg=float(np.degrees(np.sqrt(np.mean(wrapped ** 2)))),
                    Position_P95_mm=float(np.percentile(distance, 95) * 1000),
                    Last_Supported_Endpoint_Error_mm=float(distance[-1] * 1000),
                    scored_frames=count, Valid_Frame_Count=count,
                    reference_coverage=float(z['gt_valid'].mean()),
                    reconstruction_coverage=float(np.isfinite(xy).all(1).mean()),
                    ATE_RMSE_m=float(np.sqrt(np.mean(distance ** 2))),
                    ATE_RMSE_mm=float(np.sqrt(np.mean(distance ** 2)) * 1000),
                    Position_MAE_mm=float(distance.mean() * 1000),
                    RMSE_X_mm=float(np.sqrt(np.mean(error[:, 0] ** 2)) * 1000),
                    RMSE_Y_mm=float(np.sqrt(np.mean(error[:, 1] ** 2)) * 1000),
                    C3D_Coverage_pct=float(z['gt_valid'].mean() * 100),
                    Scored_Coverage_pct=float(valid.mean() * 100),
                    Valid_Supported_Run_Count=len(runs(valid)),
                    Yaw_RMSE_deg=float(np.degrees(np.sqrt(np.mean(wrapped ** 2)))),
                    Yaw_Frame_Count=count,
                    Last_Supported_Time_s=float(z['t'][np.flatnonzero(valid)[-1]]))
    adjacent = z['gt_valid'][1:] & z['gt_valid'][:-1]
    reference_path = float(np.linalg.norm(np.diff(z['gt_xy'], axis=0), axis=1)[adjacent].sum())
    supported_path = sum(float(np.linalg.norm(np.diff(z['gt_xy'][a:b], axis=0), axis=1).sum())
                         for a, b in runs(valid))
    predicted_path = sum(float(np.linalg.norm(np.diff(xy[a:b], axis=0), axis=1).sum())
                         for a, b in runs(valid))
    measured.update(reference_path_valid_m=reference_path,
                    Reference_Supported_Path_m=supported_path,
                    Path_Length_Error_mm=1000 * abs(predicted_path - supported_path))
    if supported_path >= 1.:
        measured['Last_Supported_Normalized_Endpoint_pct'] = 100 * distance[-1] / supported_path
    else:
        measured['Last_Supported_Normalized_Endpoint_pct'] = None
    theta = z['gt_heading'][valid]
    for prefix, component in (
            ('Longitudinal_Position_mm', error[:, 0] * np.cos(theta) + error[:, 1] * np.sin(theta)),
            ('Lateral_Position_mm', -error[:, 0] * np.sin(theta) + error[:, 1] * np.cos(theta))):
        component = component * 1000
        bias, sd = float(component.mean()), float(component.std(ddof=1))
        measured.update({prefix + '_samples': count, prefix + '_RMSE': float(np.sqrt(np.mean(component ** 2))),
                         prefix + '_Bias': bias, prefix + '_LoA_low': bias - 1.96 * sd,
                         prefix + '_LoA_high': bias + 1.96 * sd,
                         prefix + '_R2': None, prefix + '_Pearson': None})
    stride = max(1, round(1 / np.median(np.diff(z['t']))))
    for duration in (1, 5, 10):
        errors, possible = [], 0
        for i in range(0, len(valid), stride):
            j = int(np.searchsorted(z['t'], z['t'][i] + duration - 1e-9))
            if j >= len(valid):
                continue
            possible += 1
            if valid[i:j+1].all():
                delta = (xy[j] - xy[i]) - (z['gt_xy'][j] - z['gt_xy'][i])
                errors.append(float(np.linalg.norm(delta)))
        measured.update({f'RTE_{duration}s_mm': float(1000 * np.sqrt(np.mean(np.square(errors)))) if errors else None,
                         f'RTE_{duration}s_Windows': len(errors),
                         f'RTE_{duration}s_Coverage_pct': 100 * len(errors) / possible if possible else None})
    for distance_m in (1, 5, 10):
        errors = []
        for a, b in runs(valid):
            travelled = np.r_[0., np.cumsum(np.linalg.norm(np.diff(z['gt_xy'][a:b], axis=0), axis=1))]
            start = 0
            while start < len(travelled):
                end = int(np.searchsorted(travelled, travelled[start] + distance_m))
                if end >= len(travelled):
                    break
                turn = z['gt_heading'][a+start] - heading[a+start]
                rotation = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
                delta = rotation @ (xy[a+end] - xy[a+start]) - (z['gt_xy'][a+end] - z['gt_xy'][a+start])
                errors.append(float(np.linalg.norm(delta)))
                start = end
        measured[f'relative_{distance_m}m_rmse_m'] = float(np.sqrt(np.mean(np.square(errors)))) if errors else None
        measured[f'relative_{distance_m}m_segments'] = len(errors)
    return measured, valid


def compare_metrics(measured, saved, label):
    for key, value in measured.items():
        if value is None:
            assert saved[key] in ('', None), (label, key, saved[key])
        else:
            close(value, saved[key], (label, key))


def integration_check(z, motion, xy, heading, label):
    velocity = (motion[1:] + motion[:-1]) / 2
    dt = np.diff(z['t'])
    reconstructed_heading = np.r_[0., np.cumsum(dt * velocity[:, 2])] + z['gt_heading'][0]
    mid = (reconstructed_heading[:-1] + reconstructed_heading[1:]) / 2
    displacement = dt[:, None] * np.c_[velocity[:, 0] * np.cos(mid) - velocity[:, 1] * np.sin(mid),
                                       velocity[:, 0] * np.sin(mid) + velocity[:, 1] * np.cos(mid)]
    reconstructed_xy = np.vstack((np.zeros(2), np.cumsum(displacement, axis=0))) + z['gt_xy'][0]
    bad = np.flatnonzero(~z['imu_valid'])
    if len(bad):
        reconstructed_heading[bad[0]:] = np.nan
        reconstructed_xy[bad[0]:] = np.nan
    np.testing.assert_allclose(xy, reconstructed_xy, rtol=1e-12, atol=1e-12, err_msg=str(label))
    np.testing.assert_allclose(heading, reconstructed_heading, rtol=1e-12, atol=1e-12, err_msg=str(label))


def self_check():
    assert ratio(0., 0.) == 1. and ratio(1., 0.) == float('inf')
    assert aggregate([{'participant': 'A', 'x': 1.}] * 3 + [{'participant': 'B', 'x': 9.}], 'x') == 5.
    assert runs(np.array([False, True, True, False, True])) == [(1, 3), (4, 5)]
    t = np.arange(0., 2.01, .01)
    truth = np.c_[t, np.zeros(len(t))]
    z = dict(t=t, gt_xy=truth, gt_heading=np.zeros(len(t)),
             gt_valid=np.ones(len(t), bool), imu_valid=np.ones(len(t), bool))
    measured, valid = direct_metrics(z, truth + [.003, .004], np.full(len(t), 2 * np.pi))
    assert valid.all() and abs(measured['ATE_RMSE_mm'] - 5.) < 1e-10
    assert abs(measured['Position_P95_mm'] - 5.) < 1e-10
    assert measured['heading_rmse_deg'] < 1e-10 and measured['RTE_1s_mm'] < 1e-10
    motion = np.c_[np.ones(len(t)), np.zeros((len(t), 2))]
    integration_check(z, motion, truth, np.zeros(len(t)), 'synthetic integration')


def main():
    self_check()
    assert read(OUT / 'checkpoint.json') == dict(completed_folds=3, rows=1242, status='complete')
    assert digest(PARENT / 'artifact_manifest.json') == PREVIOUS_MANIFEST_SHA256
    protocol, run = read(OUT / 'protocol.json'), read(OUT / 'run.json')
    old_protocol, old_run = read(PARENT / 'protocol.json'), read(PARENT / 'run.json')
    prior_protocol = read(PRIOR / 'protocol.json')
    ids = protocol['training_ids']
    assert ids == old_protocol['training_ids'] == prior_protocol['training_ids']
    assert len(ids) == len(set(ids)) == 207
    assert protocol['configs'] == CONFIGS and protocol['controls'] == list(CONTROLS)
    assert all(not value[key] for value in (protocol, run) for key in ('validation_accessed', 'test_accessed'))
    assert old_run['selected']['candidate'] == 'lambda_10'
    close(old_run['selected']['equal_participant_mean_position_rmse_m'], .12887285434811182, 'v124 frozen score')
    assert protocol['sources'] == {**old_protocol['sources'], **REVIEWED_SOURCES}
    assert all(old_protocol['sources'][name] == sha for name, sha in prior_protocol['source_hashes'].items())
    manifest, old_manifest = read(OUT / 'artifact_manifest.json')['sha256'], read(PARENT / 'artifact_manifest.json')['sha256']
    expected_files = {'protocol.json', 'run.json', 'inputs.json', 'trials.csv', 'baseline_reproduction.json', 'checkpoint.json'}
    expected_files |= {f'fold_{fold}_models.json' for fold in range(3)}
    expected_files |= {f'predictions/{ident}.npz' for ident in ids}
    expected_files |= {f'{name}_{group}.csv' for name in ('v124', *CONFIGS) for group in ('participants', 'maneuvers')}
    actual_files = {f.relative_to(OUT).as_posix() for f in OUT.rglob('*')
                    if f.is_file() and f.name != 'artifact_manifest.json'}
    assert actual_files == set(normalized(manifest)) == expected_files
    inputs = normalized(read(OUT / 'inputs.json'))
    expected_inputs = {'outputs_amended_v2/calibration.json'}
    for folder, names in (
            ('outputs_motion_endpoint_v16', ('run.json', 'artifact_manifest.json')),
            ('outputs_observed_reference_v7', ('run.json', 'artifact_manifest.json')),
            ('outputs_reservoir_path_v121', ('protocol.json', 'artifact_manifest.json')),
            ('outputs_dynamic_blend_v34', ('artifact_manifest.json',)),
            ('outputs_trial_rmse_v124', ('protocol.json', 'run.json', 'trials.csv', 'artifact_manifest.json'))):
        expected_inputs |= {folder + '/' + name for name in names}
    for folder in ('outputs_reservoir_path_v121', 'outputs_dynamic_blend_v34', 'outputs_trial_rmse_v124'):
        expected_inputs |= {f'{folder}/fold_{fold}_models.json' for fold in range(3)}
    expected_inputs |= {f'outputs_motion_endpoint_v16/prepared_training/{ident}.{suffix}'
                        for ident in ids for suffix in ('npz', 'json')}
    expected_inputs |= {f'outputs_trial_rmse_v124/predictions/{ident}.npz' for ident in ids}
    assert set(inputs) == expected_inputs, ('unexpected or missing input', set(inputs) ^ expected_inputs)
    counts = dict(output=hashes(OUT, manifest), input=hashes(ROOT, inputs),
                  source=hashes(ROOT, protocol['sources']), frozen_v124_output=hashes(PARENT, old_manifest))
    for name, sha in inputs.items():
        if name.startswith('outputs_trial_rmse_v124/') and not name.endswith('/artifact_manifest.json'):
            assert sha == normalized(old_manifest)[name.split('/', 1)[1]]
    saved_rows = rows(OUT / 'trials.csv')
    saved = {(r['id'], r['candidate']): r for r in saved_rows}
    assert len(saved) == len(saved_rows) == 1242
    assert set(saved) == {(ident, name) for ident in ids for name in NAMES}
    old_saved = {(r['id'], r['candidate']): r for r in rows(PARENT / 'trials.csv')}
    metadata = {ident: old_saved[(ident, 'v34')] for ident in ids}
    assert {r['participant'] for r in metadata.values()} == set.union(*FOLDS)
    assert sum(r['participant'] == 'No.20' for r in metadata.values()) == 15
    fold_checks = []
    for fold, held in enumerate(FOLDS):
        model = read(OUT / f'fold_{fold}_models.json')
        prior = read(PRIOR / f'fold_{fold}_models.json')
        previous = read(PARENT / f'fold_{fold}_models.json')
        base = read(ROOT / f'outputs_dynamic_blend_v34/fold_{fold}_models.json')
        expected = {ident for ident in ids if metadata[ident]['participant'] not in held}
        assert len(model['fitting_ids']) == len(set(model['fitting_ids']))
        assert set(model['fitting_ids']) == set(prior['fitting_ids']) == set(previous['fitting_ids']) == expected
        assert model['held_people'] == prior['held_people'] == previous['held_people'] == base['held_people'] == sorted(held)
        assert model['normalization'] == prior['normalization'] == previous['normalization']
        assert set(base['fit_ids']) & set(ids) == expected
        assert all(ident.rsplit('_', 1)[-1] not in held for ident in base['fit_ids'])
        assert set(model['models']) == set(CONFIGS)
        fitting_histories = []
        for name, setups in model['models'].items():
            assert set(setups) == set(prior['models']['10.0']) == set(prior['normalization'])
            for setup, fit in setups.items():
                weights, center = np.asarray(fit['weights']), np.asarray(prior['models']['10.0'][setup]['weights'])
                assert weights.shape == center.shape == (17, 2)
                assert np.isfinite(weights).all() and np.isfinite(center).all()
                history = fit['history']
                assert 1 <= len(history) <= 12
                assert len(history) == 12 or history[-1]['step'] == 0.
                assert [r['iteration'] for r in history] == list(range(len(history)))
                assert all(r['step'] in (1., .5, .25, .125, 0.) for r in history)
                assert all(r['step'] != 0. for r in history[:-1])
                values = np.asarray([r['objective'] for r in history])
                assert np.isfinite(values).all() and np.all(np.diff(values) <= 0.)
                for earlier, later in zip(history, history[1:]):
                    assert (later['objective'] < earlier['objective']) if later['step'] else (later['objective'] == earlier['objective'])
                fitting_histories.append(dict(candidate=name, setup=setup, iterations=len(history),
                                              prior_L2_change=float(np.linalg.norm(weights-center))))
        fold_checks.append(dict(fold=fold, fitting=len(expected), held=len(ids)-len(expected), fits=fitting_histories))
    reproduction = read(OUT / 'baseline_reproduction.json')
    reproduced = {(r['id'], r['control']): r for r in reproduction}
    assert len(reproduced) == len(reproduction) == 621
    assert set(reproduced) == {(ident, name) for ident in ids for name in CONTROLS}
    records, frames, array_comparisons, metric_comparisons = [], Counter(), 0, 0
    for number, ident in enumerate(ids, 1):
        with np.load(OUT / 'predictions' / (ident + '.npz'), allow_pickle=False) as z, \
                np.load(PARENT / 'predictions' / (ident + '.npz'), allow_pickle=False) as parent:
            assert set(z.files) == {'t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid'} | {
                name + '_' + key for name in NAMES for key in ('motion', 'xy', 'heading')}
            for key in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid'):
                equal(z[key], parent[key], (ident, key))
            assert np.isfinite(z['t']).all() and np.all(np.diff(z['t']) > 0.)
            assert z['gt_valid'].dtype == z['imu_valid'].dtype == np.dtype(bool)
            support = parent['gt_valid'] & np.isfinite(parent['v34_xy']).all(1)
            for name, old_name in (('v34', 'v34'), ('v121', 'v121'), ('v124', 'lambda_10')):
                for key in ('motion', 'xy', 'heading'):
                    equal(z[name + '_' + key], parent[old_name + '_' + key], (ident, name, key))
                    array_comparisons += 1
                previous_row = old_saved[(ident, old_name)]
                current_row = saved[(ident, name)]
                assert set(previous_row) == set(current_row)
                for key in previous_row.keys() - {'candidate'}:
                    assert previous_row[key] == current_row[key], (ident, name, 'control CSV', key)
            for name in NAMES:
                xy, heading, motion = z[name+'_xy'], z[name+'_heading'], z[name+'_motion']
                assert xy.shape == z['gt_xy'].shape and heading.shape == z['gt_heading'].shape
                assert motion.shape == (len(z['t']), 3)
                assert np.isfinite(heading[support]).all() and np.isfinite(motion[z['imu_valid']]).all()
                assert np.isfinite(z['gt_xy'][support]).all() and np.isfinite(z['gt_heading'][support]).all()
                assert np.all(np.abs(motion[:, 0]-z['v34_motion'][:, 0]) <= .05+1e-12)
                assert np.all(np.abs(motion[:, 2]-z['v34_motion'][:, 2]) <= .02+1e-12)
                equal(motion[:, 1], z['v34_motion'][:, 1], (ident, name, 'lateral'))
                integration_check(z, motion, xy, heading, (ident, name))
                measured, valid = direct_metrics(z, xy, heading)
                assert np.array_equal(valid, support), (ident, name, 'support')
                row = saved[(ident, name)]
                assert row['participant'] == metadata[ident]['participant'] and row['condition'] == metadata[ident]['condition']
                assert int(row['fold']) == next(i for i, held in enumerate(FOLDS) if row['participant'] in held)
                compare_metrics(measured, row, (ident, name))
                metric_comparisons += len(measured)
                if name in CONTROLS:
                    primary = {k: measured[k] for k in ('position_rmse_m', 'heading_rmse_deg', 'reference_coverage',
                               'reconstruction_coverage', 'scored_frames', 'reference_path_valid_m')}
                    compare_metrics(primary, reproduced[(ident, name)], (ident, name, 'pre-fit reproduction'))
                records.append(dict(id=ident, participant=row['participant'], condition=row['condition'], candidate=name,
                                    **{key: measured[key] for key in ('position_rmse_m', *GUARD_METRICS)}))
                frames[name] += int(valid.sum())
        if number % 50 == 0:
            print('Independently checked saved predictions', number, '/207', flush=True)
    assert dict(frames) == {name: 314498 for name in NAMES}
    assert array_comparisons == 1863
    grouped = {name: [r for r in records if r['candidate'] == name] for name in NAMES}
    choices = {choice['candidate']: choice for choice in run['candidates']}
    assert len(choices) == len(run['candidates']) == 4 and set(choices) == {'v124', *CONFIGS}
    baseline = aggregate(grouped['v124'], 'position_rmse_m')
    close(baseline, .12887285434811182, 'reconstructed frozen v124 score')
    derived = []
    for name in ('v124', *CONFIGS):
        values, choice, passed, worst = grouped[name], choices[name], True, {}
        score = aggregate(values, 'position_rmse_m')
        close(score, choice['equal_participant_mean_position_rmse_m'], (name, 'summary ATE'))
        close(aggregate(values, 'heading_rmse_deg'), choice['equal_participant_mean_heading_rmse_deg'], (name, 'summary heading'))
        assert choice['trials'] == 207 and choice['participants'] == 12
        assert set(choice['guards']) == set(CONTROLS)
        for control in CONTROLS:
            guard = {}
            for category, group in (('participant_ratios', 'participant'), ('maneuver_ratios', 'condition')):
                actual, reference = aggregate(values, 'position_rmse_m', group), aggregate(grouped[control], 'position_rmse_m', group)
                assert set(actual) == set(reference)
                guard[category] = {key: ratio(value, reference[key]) for key, value in actual.items()}
            guard['metric_ratios'] = {key: ratio(aggregate(values, key), aggregate(grouped[control], key)) for key in GUARD_METRICS}
            assert set(choice['guards'][control]) == set(guard)
            for category, ratios in guard.items():
                assert set(ratios) == set(choice['guards'][control][category])
                for key, value in ratios.items():
                    close(value, choice['guards'][control][category][key], (name, control, category, key))
                    passed = passed and value <= 1.05
                worst[control+'_'+category] = max(ratios.values())
        eligible = name == 'v124' or (passed and score < baseline)
        assert choice['eligible'] == eligible
        derived.append(dict(candidate=name, eligible=eligible, ATE_mm=score*1000, max_guard_ratios=worst))
        for group, filename, score_key in (('participant', 'participants', 'mean_trial_position_rmse_m'),
                                           ('condition', 'maneuvers', 'equal_participant_mean_position_rmse_m')):
            table = rows(OUT / f'{name}_{filename}.csv')
            indexed = {r[group]: r for r in table}
            expected_groups = aggregate(values, 'position_rmse_m', group)
            assert len(indexed) == len(table) and set(indexed) == set(expected_groups)
            for label, group_score in expected_groups.items():
                close(group_score, indexed[label][score_key], (name, group, label, 'table'))
                subset = [r for r in values if r[group] == label]
                assert int(indexed[label]['trials']) == len(subset)
                if group == 'participant':
                    close(aggregate(subset, 'heading_rmse_deg'), indexed[label]['mean_trial_heading_rmse_deg'], (name, label, 'table heading'))
                else:
                    assert int(indexed[label]['participants']) == len({r['participant'] for r in subset})
    selected = min((choice for choice in derived if choice['eligible']), key=lambda choice: choice['ATE_mm'])
    assert selected['candidate'] == run['selected']['candidate']
    assert run['selected'] == choices[selected['candidate']]
    result = dict(status='PASS', reviewed_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Independent sealed TRAIN screen arithmetic; no fit or inference rerun', hash_counts=counts,
                  source_review=dict(axis_loss_gradient_GN_IRLS='PASS', frozen_prior_use='PASS by reviewed source and sealed fold metadata',
                                     package_pre_fit_source_pin_fix='PASS', blockers=[]),
                  recordings=207, participants=12, no20_recordings=15, candidates=6, paired_prediction_sets=1242,
                  scored_frames=dict(frames), exact_control_array_comparisons=array_comparisons,
                  directly_reconstructed_metric_values=metric_comparisons, folds=fold_checks,
                  selected=selected, candidates_reviewed=derived, baseline_v124_ATE_mm=baseline*1000,
                  benefit_vs_v124_mm=baseline*1000-selected['ATE_mm'],
                  frozen_v124_manifest_sha256=PREVIOUS_MANIFEST_SHA256,
                  output_manifest_sha256=digest(OUT/'artifact_manifest.json'), review_script_sha256=digest(Path(__file__)),
                  checks=['all output/input/source hashes and exact output/input path coverage',
                          'frozen v124 output seal and all inherited v121/v124 source hashes unchanged',
                          '207 IDs/12 people/15 No20 and original fold exclusions/normalizations',
                          'fixed three configs and finite weights/permitted monotone fit histories',
                          '621 pre-fit reproduction records; 1863 exact triple-control array comparisons',
                          '1242 paired supports, finite supported predictions and independent saved-motion integration',
                          'speed/yaw caps and exactly unchanged lateral motion',
                          'direct primary/guard metrics and position/coverage/path/RTE/distance-relative diagnostics',
                          'all control CSV metric fields exactly equal sealed v124',
                          'all participant/maneuver tables and every guard versus all three controls',
                          'strict v124 improvement/eligibility/winner reconstructed'],
                  declined_checks=['Fitting loss values/initial priors not recomputed from training features; source and sealed prior metadata reviewed',
                                   'Route/Frechet and filtered derivative diagnostic values for new candidates not independently recomputed; no selection uses them',
                                   'Full-TRAIN package/report output review is a separate follow-up',
                                   'No raw acquisition, validation/test, runtime geometry or independent generalization evaluation'],
                  limitations=['Conditional post-selection TRAIN screen only',
                               'Synthetic loss tests passed in coordinator execution; reviewer inspected them without rerunning'])
    target = ROOT / 'research_state/v125_independent_review.json'
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
