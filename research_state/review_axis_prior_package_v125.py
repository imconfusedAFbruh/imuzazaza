"""Independent saved v125 package/report checks; no fit or prediction reruns."""
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'models/axis_prior_v125'
REPORT = ROOT / 'outputs_axis_prior_v125_report'
SCREEN = ROOT / 'outputs_axis_prior_v125'
PRIOR = ROOT / 'models/reservoir_path_v121_completed'
SELECTED = 'speed1_yaw10'
NAMES = {'v34', 'v121', 'v124', 'speed1_yaw10', 'speed10_yaw1', 'speed3_yaw3'}
PRIOR_MODEL_SHA256 = '6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b'
REVIEWED_SOURCES = {
    'package_axis_prior_v125.py': 'a9b14712220970d687b9574e848b3e4ff5a3e2bc6c026e756b1696c39211815f',
    'report_axis_prior_v125.py': 'dfaa327fe978433305333c1d97d895c420c4948a53e256487bdc4c728a7b42a1',
    'report_frozen_validation_v123.py': '168d70a4fdbaee48499896c7c14d1a7a0f98139177c0eea6d5fe4b7ab4d68dba',
    'reservoir_stability_v122.py': 'b31d4cbad1b5beca83db04b962c851a29d16b2aab5ebc4158f198f8ce45da282',
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


def hashes(base, mapping):
    for name, expected in mapping.items():
        path = (base / name.replace('\\', '/')).resolve()
        assert path.is_relative_to(ROOT), ('outside workspace', name)
        assert digest(path) == expected, ('hash mismatch', name)
    return len(mapping)


def seal(folder, expected_files=None):
    manifest = normalized(read(folder / 'artifact_manifest.json')['sha256'])
    actual = {path.relative_to(folder).as_posix() for path in folder.rglob('*')
              if path.is_file() and path.name != 'artifact_manifest.json'}
    assert actual == set(manifest), ('manifest coverage', folder, actual ^ set(manifest))
    if expected_files is not None:
        assert actual == expected_files, ('unexpected output', folder, actual ^ expected_files)
    return hashes(folder, manifest)


def close(actual, saved, label):
    assert math.isfinite(actual) and math.isfinite(float(saved)), (label, actual, saved)
    assert np.isclose(actual, float(saved), rtol=1e-10, atol=1e-10), (label, actual, saved)


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def equal_person(records, key):
    by_person = defaultdict(list)
    for row in records:
        value = number(row[key])
        if value is not None:
            by_person[row['participant']].append(value)
    return statistics.mean(statistics.mean(values) for values in by_person.values()) if by_person else None


def paired_statistics(benefits):
    benefits = np.asarray(benefits, dtype=float)
    n = len(benefits)
    omitted = np.array([np.delete(benefits, i).mean() for i in range(n)])
    draws = np.random.default_rng(122).integers(0, n, size=(4096, n))
    interval = np.quantile(np.mean(benefits[draws], axis=1), [.025, .975])
    signs = np.where((np.arange(2**n)[:, None] >> np.arange(n)) & 1, 1., -1.)
    means = np.mean(signs * benefits[None, :], axis=1)
    count = int(np.count_nonzero(np.abs(means) >= abs(float(benefits.mean())) - 1e-12))
    return omitted, interval, count


def self_check():
    assert number('') is None and number('True') is None and number('nan') is None
    assert number('2.5') == 2.5
    assert equal_person([{'participant': 'A', 'x': 1.}] * 3 + [{'participant': 'B', 'x': 9.}], 'x') == 5.
    assert equal_person([{'participant': 'A', 'x': ''}], 'x') is None
    omitted, interval, count = paired_statistics([2., 2., 2.])
    assert np.array_equal(omitted, [2., 2., 2.]) and np.array_equal(interval, [2., 2.]) and count == 2


def main():
    self_check()
    screen_review = read(ROOT / 'research_state/v125_independent_review.json')
    assert screen_review['status'] == 'PASS' and screen_review['selected']['candidate'] == SELECTED
    assert digest(SCREEN / 'artifact_manifest.json') == screen_review['output_manifest_sha256']
    assert digest(ROOT / 'research_state/review_axis_prior_v125.py') == screen_review['review_script_sha256']
    screen, protocol = read(SCREEN/'run.json'), read(SCREEN/'protocol.json')
    model, prior = read(BUNDLE/'model.json'), read(PRIOR/'model.json')
    assert digest(PRIOR/'model.json') == PRIOR_MODEL_SHA256
    assert digest(PRIOR/'model.json') == read(PRIOR/'artifact_manifest.json')['sha256']['model.json']
    assert screen['selected']['candidate'] == SELECTED and screen['selected']['eligible'] is True
    assert model['penalties'] == protocol['configs'][SELECTED] == [1., 10.]
    assert model['selected_fold_result'] == screen['selected']
    ids = model['training_ids']
    assert ids == protocol['training_ids'] == prior['training_ids']
    assert len(ids) == len(set(ids)) == 207
    assert model['normalization'] == prior['normalization']
    assert set(model['fits']) == set(prior['fits']) == set(model['normalization'])
    assert model['validation_evaluated'] is False and model['test_evaluated'] is False
    assert 'v121 selected weights are fitting prior' in model['baseline']
    inputs, dependencies = normalized(read(BUNDLE/'inputs.json')), normalized(model['dependencies'])
    expected_sources = {**protocol['sources'], 'package_axis_prior_v125.py': REVIEWED_SOURCES['package_axis_prior_v125.py']}
    expected_inputs = {'models/reservoir_path_v121_completed/model.json',
                       'models/reservoir_path_v121_completed/artifact_manifest.json',
                       'outputs_axis_prior_v125/run.json', 'outputs_axis_prior_v125/protocol.json',
                       'outputs_axis_prior_v125/artifact_manifest.json',
                       'outputs_reservoir_path_v121/protocol.json', 'outputs_reservoir_path_v121/artifact_manifest.json',
                       'outputs_motion_endpoint_v16/run.json', 'outputs_motion_endpoint_v16/artifact_manifest.json',
                       'outputs_observed_reference_v7/run.json', 'outputs_observed_reference_v7/artifact_manifest.json',
                       'outputs_amended_v2/calibration.json',
                       'outputs_nonlinear_endpoint_v21/model.json', 'outputs_nonlinear_endpoint_v21/artifact_manifest.json',
                       'outputs_dynamic_tilt_v33/tilt_0.3_model.json', 'outputs_dynamic_tilt_v33/artifact_manifest.json'}
    expected_inputs |= {f'outputs_motion_endpoint_v16/prepared_training/{ident}.{suffix}'
                        for ident in ids for suffix in ('npz', 'json')}
    expected_inputs |= set(expected_sources)
    assert set(inputs) == expected_inputs, ('bundle input coverage', set(inputs) ^ expected_inputs)
    added_dependencies = {'axis_prior_v125.py', 'package_axis_prior_v125.py', 'test_axis_prior_v125.py',
                          'trial_rmse_v124.py', 'research_docs/axis_prior_v125.md',
                          'models/reservoir_path_v121_completed/model.json',
                          'models/reservoir_path_v121_completed/artifact_manifest.json',
                          'outputs_axis_prior_v125/artifact_manifest.json'}
    assert set(dependencies) == set(normalized(prior['dependencies'])) | added_dependencies | set(expected_sources)
    for name, sha in {**normalized(prior['dependencies']), **expected_sources}.items():
        assert dependencies[name] == sha, ('changed inherited or screened dependency', name)
    assert all(inputs[name] == sha for name, sha in expected_sources.items())
    bundle_files = {'model.json', 'inputs.json', 'fit_checkpoint.json', 'trial_verification.json', 'verification.json', 'README.md'}
    report_files = {'grouped_metrics.csv', 'stability.json', 'run.json'}
    report_run = read(REPORT/'run.json')
    report_inputs = normalized(report_run['inputs'])
    expected_report_inputs = {'outputs_axis_prior_v125/artifact_manifest.json', 'outputs_axis_prior_v125/trials.csv',
                              'outputs_axis_prior_v125/run.json', 'report_axis_prior_v125.py',
                              'report_frozen_validation_v123.py', 'reservoir_stability_v122.py',
                              'pipeline.py', 'combined_physics_folds_v58.py',
                              'models/axis_prior_v125/artifact_manifest.json', 'models/axis_prior_v125/model.json',
                              'models/axis_prior_v125/verification.json', 'research_docs/axis_prior_results_v125.md'}
    assert set(report_inputs) == expected_report_inputs, ('report input coverage', set(report_inputs) ^ expected_report_inputs)
    counts = dict(screen_outputs=seal(SCREEN), bundle_outputs=seal(BUNDLE, bundle_files),
                  bundle_inputs=hashes(ROOT, inputs), bundle_dependencies=hashes(ROOT, dependencies),
                  report_outputs=seal(REPORT, report_files), report_inputs=hashes(ROOT, report_inputs),
                  reviewed_sources=hashes(ROOT, REVIEWED_SOURCES))
    for name, sha in expected_sources.items():
        assert dependencies[name] == inputs[name] == sha
    fit_details = {}
    for setup, fit in model['fits'].items():
        weights, center = np.asarray(fit['weights']), np.asarray(prior['fits'][setup]['weights'])
        assert weights.shape == center.shape == (17, 2)
        assert np.isfinite(weights).all() and np.isfinite(center).all()
        history = fit['history']
        assert 1 <= len(history) <= 12 and (len(history) == 12 or history[-1]['step'] == 0.)
        assert [r['iteration'] for r in history] == list(range(len(history)))
        assert all(r['step'] in (1., .5, .25, .125, 0.) for r in history)
        assert all(r['step'] != 0. for r in history[:-1])
        assert np.isfinite([r['objective'] for r in history]).all()
        for previous, current in zip(history, history[1:]):
            assert (current['objective'] < previous['objective']) if current['step'] else (current['objective'] == previous['objective'])
        fit_details[setup] = dict(iterations=len(history), prior_L2_change=float(np.linalg.norm(weights-center)))
    assert read(BUNDLE/'fit_checkpoint.json') == dict(completed_setups=sorted(model['fits']), status='complete')
    verification, checks = read(BUNDLE/'verification.json'), read(BUNDLE/'trial_verification.json')
    assert len(checks) == len({r['id'] for r in checks}) == 207
    assert {r['id'] for r in checks} == set(ids)
    assert all(r['optical_identity_poisoning_invariant'] is True for r in checks)
    assert all(math.isfinite(r['maximum_motion_difference']) and 0 <= r['maximum_motion_difference'] < 1e-7 for r in checks)
    maximum = max(r['maximum_motion_difference'] for r in checks)
    assert maximum == verification['maximum_motion_difference']
    assert verification['recordings'] == 207 and verification['full_train_fit'] is True
    assert verification['all_optical_identity_poisoning_checks_passed'] is True
    assert verification['validation_accessed'] is False and verification['test_accessed'] is False
    assert verification['note'] == 'Full TRAIN inference reproduction; not held-out accuracy'
    raw = defaultdict(list)
    for row in table(SCREEN/'trials.csv'):
        raw[row['candidate']].append(row)
    assert set(raw) == NAMES
    assert all(len(rr) == len({r['id'] for r in rr}) == 207 for rr in raw.values())
    assert all({r['id'] for r in rr} == set(ids) for rr in raw.values())
    assert all(sum(r['participant'] == 'No.20' for r in rr) == 15 for rr in raw.values())
    assert all(sum(int(r['scored_frames']) for r in rr) == 314498 for rr in raw.values())
    people = sorted({r['participant'] for r in raw[SELECTED]})
    assert len(people) == 12 and len({r['condition'] for r in raw[SELECTED]}) == 7
    grouped = table(REPORT/'grouped_metrics.csv')
    grouped_map = {(r['model'], r['group_type'], r['group'], r['metric']): r for r in grouped}
    assert len(grouped_map) == len(grouped) == report_run['grouped_rows'] == 8520
    expected_keys, unavailable, partial = set(), 0, 0
    for name, rr in raw.items():
        metrics = [key for key in rr[0] if key not in ('id', 'participant', 'condition', 'fold', 'candidate')
                   and any(number(r[key]) is not None for r in rr)]
        groups = [('overall', 'all', rr)]
        for dimension in ('participant', 'condition'):
            for label in sorted({r[dimension] for r in rr}):
                groups.append((dimension, label, [r for r in rr if r[dimension] == label]))
        for dimension, label, subset in groups:
            for metric in metrics:
                key = (name, dimension, label, metric)
                expected_keys.add(key)
                saved = grouped_map[key]
                by_person = defaultdict(list)
                for row in subset:
                    value = number(row[metric])
                    if value is not None:
                        by_person[row['participant']].append(value)
                available_count = sum(len(values) for values in by_person.values())
                expected = dict(available_trials=available_count, total_trials=len(subset),
                                available_participants=len(by_person), total_participants=len({r['participant'] for r in subset}),
                                missing_trials=len(subset)-available_count)
                assert all(int(saved[field]) == value for field, value in expected.items()), (key, expected, saved)
                if by_person:
                    close(statistics.mean(statistics.mean(values) for values in by_person.values()), saved['equal_person_mean'], key)
                else:
                    assert saved['equal_person_mean'] == '', key
                    unavailable += 1
                partial += int(0 < available_count < len(subset))
    assert expected_keys == set(grouped_map)
    assert report_run['prediction_evaluations'] == 0
    benefits = np.array([1000*(equal_person([r for r in raw['v124'] if r['participant'] == person], 'position_rmse_m')
                                -equal_person([r for r in raw[SELECTED] if r['participant'] == person], 'position_rmse_m'))
                         for person in people])
    stats = read(REPORT/'stability.json')
    assert list(stats['participant_benefits_mm']) == people
    for person, value in zip(people, benefits):
        close(value, stats['participant_benefits_mm'][person], ('participant benefit', person))
    omitted, interval, sign_count = paired_statistics(benefits)
    mean_benefit = float(benefits.mean())
    close(mean_benefit, stats['mean_benefit_mm'], 'mean benefit')
    np.testing.assert_allclose(omitted, stats['leave_one_person_out_benefits_mm'], rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(interval, stats['bootstrap_percentile95_mm'], rtol=1e-10, atol=1e-10)
    assert stats['participants_improved'] == int((benefits > 0).sum())
    assert stats['sign_flips'] == 4096 and stats['two_sided_sign_flip_fraction'] == sign_count/4096
    assert stats['conditional_post_selection_train_only'] is True
    baseline, selected = 1000*equal_person(raw['v124'], 'position_rmse_m'), 1000*equal_person(raw[SELECTED], 'position_rmse_m')
    close(baseline, screen_review['baseline_v124_ATE_mm'], 'baseline cross-review')
    close(selected, screen_review['selected']['ATE_mm'], 'selected cross-review')
    close(baseline-selected, mean_benefit, 'paired mean identity')
    document = (ROOT/'research_docs/axis_prior_results_v125.md').read_text(encoding='utf-8')
    assert f'**{baseline:.9f} mm** -> selected **{selected:.9f} mm**' in document
    assert f'Selected `{SELECTED}`' in document and digest(BUNDLE/'model.json') in document
    assert f'{int((benefits > 0).sum())}/12 participants improve against v124.' in document
    assert f"{stats['two_sided_sign_flip_fraction']:.9f}" in document
    for person, benefit in zip(people, benefits):
        base = 1000*equal_person([r for r in raw['v124'] if r['participant'] == person], 'position_rmse_m')
        current = 1000*equal_person([r for r in raw[SELECTED] if r['participant'] == person], 'position_rmse_m')
        assert f'| {person} | {base:.6f} | {current:.6f} | {benefit:+.6f} |' in document
    for condition in sorted({r['condition'] for r in raw[SELECTED]}):
        values = [1000*equal_person([r for r in raw[name] if r['condition'] == condition], 'position_rmse_m')
                  for name in ('v34', 'v121', 'v124', SELECTED)]
        assert '| '+condition+' | '+' | '.join(f'{value:.6f}' for value in values)+' |' in document
    for choice in screen['candidates']:
        for control, guard in choice['guards'].items():
            for category, values in guard.items():
                for label, value in values.items():
                    if value > 1.05:
                        assert f'{control}/{category}/{label}={value:.9f}' in document
    result = dict(status='PASS', reviewed_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Sealed package metadata/report arithmetic; no fit/inference/validation/test rerun',
                  hash_counts=counts, model_sha256=digest(BUNDLE/'model.json'), selected=SELECTED, penalties=[1., 10.],
                  full_train_ids=207, participants=12, no20_recordings=15, scored_frames_per_screen_candidate=314498,
                  frozen_prior_normalization_preserved=True, fits=fit_details,
                  inference_verification_records=207, recorded_maximum_motion_difference=maximum,
                  recorded_optical_identity_poisoning_checks_all_passed=True,
                  grouped_rows_verified=8520, groups_without_available_values=unavailable,
                  groups_with_partial_availability=partial, report_input_coverage_complete=True,
                  bundle_claim_input_hashes={name: report_inputs['models/axis_prior_v125/'+name]
                                           for name in ('model.json', 'artifact_manifest.json', 'verification.json')},
                  participant_benefits_mm=dict(zip(people, benefits.tolist())),
                  participants_improved=int((benefits > 0).sum()), mean_benefit_mm=mean_benefit,
                  leave_one_person_out_benefit_range_mm=[float(omitted.min()), float(omitted.max())],
                  bootstrap_seed=122, bootstrap_draws=4096, bootstrap_percentile95_mm=interval.tolist(),
                  exact_sign_flip_count=sign_count, exact_sign_flip_total=4096,
                  two_sided_sign_flip_fraction=sign_count/4096,
                  screen_review_sha256=digest(ROOT/'research_state/v125_independent_review.json'),
                  review_script_sha256=digest(Path(__file__)),
                  source_review=dict(frozen_training_prior='PASS', package_pre_fit_source_pins='PASS',
                                     actual_public_loader_and_poisoning_runner='PASS', report_grouping_and_statistics='PASS', blockers=[]),
                  declined_checks=['Saved inference/poisoning records checked without rerunning predictions',
                                   'Training objective values not recomputed; frozen source/prior and finite monotone histories checked',
                                   'Grouped diagnostic values reconstructed from sealed CSV, not independently recomputed from raw inputs',
                                   'No raw acquisition, validation/test accuracy, timing/runtime geometry or deployment evaluation'],
                  limitations=['Conditional post-selection TRAIN improvement; no independent significance claim',
                               'Saved public-loader equivalence is full-TRAIN reproduction, distinct from participant-fold accuracy'])
    target = ROOT/'research_state/v125_package_report_review.json'
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
