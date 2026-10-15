"""Independently verify sealed v124 bundle/report metadata and report arithmetic."""
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
BUNDLE = ROOT / 'models/trial_rmse_v124'
REPORT = ROOT / 'outputs_trial_rmse_v124_report'
SCREEN = ROOT / 'outputs_trial_rmse_v124'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def hashes(base, mapping):
    for name, sha in mapping.items():
        path = base / name
        assert path.is_relative_to(ROOT)
        assert digest(path) == sha, ('hash mismatch', name)
    return len(mapping)


def table(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def close(actual, expected, label):
    assert np.isclose(actual, float(expected), rtol=1e-10, atol=1e-10), (
        label, actual, expected)


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def sealed_counts(folder):
    manifest = read(folder / 'artifact_manifest.json')['sha256']
    count = hashes(folder, manifest)
    assert {str(f.relative_to(folder)) for f in folder.rglob('*')
            if f.is_file() and f.name != 'artifact_manifest.json'} == set(manifest)
    return count


def main():
    screen = read(SCREEN / 'run.json')
    protocol = read(SCREEN / 'protocol.json')
    model = read(BUNDLE / 'model.json')
    prior = read(ROOT / 'models/reservoir_path_v121_completed/model.json')
    verification = read(BUNDLE / 'verification.json')
    trial_checks = read(BUNDLE / 'trial_verification.json')
    report_run = read(REPORT / 'run.json')
    counts = dict(bundle_outputs=sealed_counts(BUNDLE),
                  bundle_inputs=hashes(ROOT, read(BUNDLE / 'inputs.json')),
                  bundle_dependencies=hashes(ROOT, model['dependencies']),
                  report_outputs=sealed_counts(REPORT),
                  report_inputs=hashes(ROOT, report_run['inputs']))
    assert model['penalty'] == 10. == float(screen['selected']['candidate'].split('_')[1])
    assert model['selected_fold_result'] == screen['selected']
    ids = model['training_ids']
    assert ids == protocol['training_ids'] == prior['training_ids']
    assert len(ids) == len(set(ids)) == 207
    assert model['normalization'] == prior['normalization']
    assert set(model['fits']) == set(prior['fits']) == set(model['normalization'])
    assert not model['validation_evaluated'] and not model['test_evaluated']
    for name, sha in prior['dependencies'].items():
        assert model['dependencies'][name] == sha
    fit_details = {}
    for setup, fit in model['fits'].items():
        weights = np.asarray(fit['weights'])
        original = np.asarray(prior['fits'][setup]['weights'])
        assert weights.shape == original.shape == (17, 2)
        assert np.isfinite(weights).all()
        history = fit['history']
        assert 1 <= len(history) <= 12
        assert [r['iteration'] for r in history] == list(range(len(history)))
        assert all(r['step'] in (1., .5, .25, .125, 0.) for r in history)
        assert all(r['step'] != 0. for r in history[:-1])
        assert np.isfinite([r['objective'] for r in history]).all()
        assert np.all(np.diff([r['objective'] for r in history]) <= 0)
        fit_details[setup] = dict(iterations=len(history),
                                 prior_weight_L2_change=float(np.linalg.norm(weights - original)))
    assert read(BUNDLE / 'fit_checkpoint.json') == dict(
        completed_setups=sorted(model['fits']), status='complete')
    assert len(trial_checks) == len({r['id'] for r in trial_checks}) == 207
    assert {r['id'] for r in trial_checks} == set(ids)
    assert all(r['optical_identity_poisoning_invariant'] is True for r in trial_checks)
    maximum = max(r['maximum_motion_difference'] for r in trial_checks)
    assert all(math.isfinite(r['maximum_motion_difference']) and
               0 <= r['maximum_motion_difference'] < 1e-7 for r in trial_checks)
    assert maximum == verification['maximum_motion_difference'] == 0.
    assert verification['recordings'] == 207 and verification['full_train_fit'] is True
    assert verification['all_optical_identity_poisoning_checks_passed'] is True
    assert not verification['validation_accessed'] and not verification['test_accessed']

    rows = table(SCREEN / 'trials.csv')
    raw = defaultdict(list)
    for row in rows:
        raw[row['candidate']].append(row)
    assert set(raw) == {'v34', 'v121', 'lambda_0.1', 'lambda_1', 'lambda_10'}
    assert all(len(rr) == len({r['id'] for r in rr}) == 207 for rr in raw.values())
    assert all({r['id'] for r in rr} == set(ids) for rr in raw.values())
    grouped = table(REPORT / 'grouped_metrics.csv')
    grouped_map = {(r['model'], r['group_type'], r['group'], r['metric']): r for r in grouped}
    assert len(grouped_map) == len(grouped) == report_run['grouped_rows'] == 7100
    expected_keys = set()
    unavailable_groups = 0
    partial_groups = 0
    for name, rr in raw.items():
        metrics = [key for key in rr[0]
                   if key not in ('candidate', 'fold', 'id', 'participant', 'condition')
                   and any(number(r[key]) is not None for r in rr)]
        groups = [('overall', 'all', rr)]
        for dimension in ('participant', 'condition'):
            for group in sorted({r[dimension] for r in rr}):
                groups.append((dimension, group, [r for r in rr if r[dimension] == group]))
        for dimension, group, sub in groups:
            people = {r['participant'] for r in sub}
            for metric in metrics:
                key = (name, dimension, group, metric)
                expected_keys.add(key)
                saved = grouped_map[key]
                available = [(r['participant'], number(r[metric])) for r in sub
                             if number(r[metric]) is not None]
                by_person = defaultdict(list)
                for person, value in available:
                    by_person[person].append(value)
                expected = dict(available_trials=len(available), total_trials=len(sub),
                                available_participants=len(by_person), total_participants=len(people),
                                missing_trials=len(sub) - len(available))
                assert all(int(saved[k]) == value for k, value in expected.items()), (key, expected, saved)
                if by_person:
                    mean = statistics.mean(statistics.mean(v) for v in by_person.values())
                    close(mean, saved['equal_person_mean'], key)
                else:
                    assert saved['equal_person_mean'] == ''
                    unavailable_groups += 1
                partial_groups += int(0 < len(available) < len(sub))
    assert expected_keys == set(grouped_map)
    assert report_run['prediction_evaluations'] == 0

    people = sorted({r['participant'] for r in rows})
    assert len(people) == 12
    benefits = np.array([
        1000 * (statistics.mean(float(r['position_rmse_m']) for r in raw['v121'] if r['participant'] == person)
                - statistics.mean(float(r['position_rmse_m']) for r in raw['lambda_10'] if r['participant'] == person))
        for person in people])
    stats = read(REPORT / 'stability.json')
    assert list(stats['participant_benefits_mm']) == people
    for person, benefit in zip(people, benefits):
        close(benefit, stats['participant_benefits_mm'][person], ('benefit', person))
    mean_benefit = float(benefits.mean())
    omitted = np.array([np.delete(benefits, i).mean() for i in range(len(people))])
    draws = np.random.default_rng(122).integers(0, 12, size=(4096, 12))
    bootstrap = np.quantile(np.mean(benefits[draws], axis=1), [.025, .975])
    signs = np.where((np.arange(4096)[:, None] >> np.arange(12)) & 1, 1., -1.)
    sign_means = np.mean(signs * benefits[None, :], axis=1)
    sign_count = int(np.count_nonzero(np.abs(sign_means) >= abs(mean_benefit) - 1e-12))
    close(mean_benefit, stats['mean_benefit_mm'], 'mean benefit')
    np.testing.assert_allclose(omitted, stats['leave_one_person_out_benefits_mm'], rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(bootstrap, stats['bootstrap_percentile95_mm'], rtol=1e-10, atol=1e-10)
    assert stats['participants_improved'] == int((benefits > 0).sum()) == 8
    assert stats['sign_flips'] == 4096
    assert stats['two_sided_sign_flip_fraction'] == sign_count / 4096 == .1533203125
    assert stats['conditional_post_selection_train_only'] is True

    supplemental_paths = [BUNDLE / name for name in ('artifact_manifest.json', 'model.json', 'verification.json')]
    supplemental = {str(path.relative_to(ROOT)): digest(path) for path in supplemental_paths}
    recorded_inputs = {name.replace(chr(92), '/') for name in report_run['inputs']}
    omitted_inputs = [name for name in supplemental if name.replace(chr(92), '/') not in recorded_inputs]
    assert len(omitted_inputs) == 3
    result = dict(status='PASS', reviewed_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Sealed package metadata and report arithmetic; no fit/inference/validation/test rerun',
                  hash_counts=counts, model_sha256=digest(BUNDLE / 'model.json'),
                  full_train_ids=207, frozen_prior_normalization_preserved=True,
                  fits=fit_details, inference_verification_records=207,
                  recorded_maximum_motion_difference=maximum,
                  recorded_optical_identity_poisoning_checks_all_passed=True,
                  grouped_rows_verified=7100, groups_without_available_values=unavailable_groups,
                  groups_with_partial_availability=partial_groups,
                  participant_benefits_mm=dict(zip(people, benefits.tolist())),
                  participants_improved=8, mean_benefit_mm=mean_benefit,
                  leave_one_person_out_benefit_range_mm=[float(omitted.min()), float(omitted.max())],
                  bootstrap_seed=122, bootstrap_draws=4096,
                  bootstrap_percentile95_mm=bootstrap.tolist(), exact_sign_flip_count=sign_count,
                  exact_sign_flip_total=4096, two_sided_sign_flip_fraction=sign_count / 4096,
                  supplemental_report_input_hashes=supplemental,
                  original_report_provenance_note='Original sealed report run.json omitted these three bundle inputs; this independent review supplies their hashes without changing the sealed report.',
                  review_script_sha256=digest(Path(__file__)),
                  source_review=dict(objective_and_gradient='pass', held_exclusions='pass',
                                     package_uses_existing_sensor_only_loader='pass',
                                     statistics_selection_independent='pass', blockers=[]),
                  declined_checks=['New fitting or inference repetition: outside independent output review',
                                   'Validation/test accuracy: outside v124 protocol',
                                   'Acquisition/timing identity: no new linked evidence in this protocol'],
                  limitations=['Inference equivalence/poisoning checks verified from sealed207-record artifacts and reviewed runner; not rerun by reviewer',
                               'Conditional post-selection TRAIN improvement; bootstrap interval includes zero',
                               'No generalization, independent timing or deployment approval established'])
    target = ROOT / 'research_state/v124_package_report_review.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
