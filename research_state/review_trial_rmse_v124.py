"""Independent TRAIN-output arithmetic review; no fitting or raw-data access."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs_trial_rmse_v124'
PARENT = ROOT / 'outputs_reservoir_path_v121'
FOLDS = [
    {'No.3', 'No.8', 'No.15', 'No.20'},
    {'No.1', 'No.4', 'No.13', 'No.16'},
    {'No.6', 'No.7', 'No.17', 'No.19'},
]
NAMES = ('v34', 'v121', 'lambda_0.1', 'lambda_1', 'lambda_10')
CORE = ('position_rmse_m', 'heading_rmse_deg', 'Position_P95_mm',
        'Last_Supported_Endpoint_Error_mm')


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_hashes(base, mapping):
    for name, sha in mapping.items():
        path = base / name
        assert path.is_relative_to(ROOT), name
        assert digest(path) == sha, ('hash mismatch', name)
    return len(mapping)


def close(actual, saved, label):
    assert np.isclose(actual, float(saved), rtol=1e-10, atol=1e-10), (
        label, actual, saved)


def aggregate(rows, key, group=None):
    if group is None:
        people = sorted({r['participant'] for r in rows})
        return float(np.mean([np.mean([r[key] for r in rows
                                      if r['participant'] == person])
                              for person in people]))
    return {value: aggregate([r for r in rows if r[group] == value], key)
            for value in sorted({r[group] for r in rows})}


def ratio(value, baseline):
    return value / baseline if baseline else (1. if value == 0 else float('inf'))


def main():
    import csv

    protocol = read(OUT / 'protocol.json')
    run = read(OUT / 'run.json')
    manifest = read(OUT / 'artifact_manifest.json')['sha256']
    inputs = read(OUT / 'inputs.json')
    old_protocol = read(PARENT / 'protocol.json')
    old_manifest = read(PARENT / 'artifact_manifest.json')['sha256']
    assert protocol['penalties'] == [.1, 1., 10.]
    assert not protocol['validation_accessed'] and not protocol['test_accessed']
    assert not run['validation_accessed'] and not run['test_accessed']
    counts = dict(output=verify_hashes(OUT, manifest),
                  input=verify_hashes(ROOT, inputs),
                  source=verify_hashes(ROOT, protocol['sources']))
    actual_files = {str(f.relative_to(OUT)) for f in OUT.rglob('*')
                    if f.is_file() and f.name != 'artifact_manifest.json'}
    assert actual_files == set(manifest)
    for name, sha in old_protocol['source_hashes'].items():
        assert protocol['sources'][name] == sha, ('changed v121 dependency', name)

    ids = protocol['training_ids']
    assert len(ids) == len(set(ids)) == 207
    assert set(ids) == set(old_protocol['training_ids'])
    with (OUT / 'trials.csv').open(newline='') as stream:
        saved_rows = list(csv.DictReader(stream))
    saved = {(r['id'], r['candidate']): r for r in saved_rows}
    assert len(saved) == len(saved_rows) == 1035
    assert set(saved) == {(ident, name) for ident in ids for name in NAMES}
    metadata = {ident: saved[(ident, 'v34')] for ident in ids}
    assert len({r['participant'] for r in metadata.values()}) == 12
    assert sum(r['participant'] == 'No.20' for r in metadata.values()) == 15
    old_trials_hash = digest(PARENT / 'trials.csv')
    assert old_trials_hash == old_manifest['trials.csv']
    with (PARENT / 'trials.csv').open(newline='') as stream:
        old_rows = {(r['id'], float(r['penalty'])): r
                    for r in csv.DictReader(stream)}

    fold_counts = []
    for fold, held in enumerate(FOLDS):
        model = read(OUT / f'fold_{fold}_models.json')
        prior = read(PARENT / f'fold_{fold}_models.json')
        v34_path = ROOT / 'outputs_dynamic_blend_v34'
        base = read(v34_path / f'fold_{fold}_models.json')
        expected = {i for i, r in metadata.items() if r['participant'] not in held}
        assert len(model['fitting_ids']) == len(set(model['fitting_ids']))
        assert set(model['fitting_ids']) == set(prior['fitting_ids']) == expected
        assert model['held_people'] == prior['held_people'] == base['held_people'] == sorted(held)
        assert model['normalization'] == prior['normalization']
        assert set(base['fit_ids']) & set(ids) == expected
        assert all(i.rsplit('_', 1)[-1] not in held for i in base['fit_ids'])
        assert set(model['models']) == {'0.1', '1.0', '10.0'}
        for penalty_models in model['models'].values():
            assert set(penalty_models) == set(prior['normalization'])
            for fit in penalty_models.values():
                weights = np.asarray(fit['weights'])
                assert weights.shape == (17, 2) and np.isfinite(weights).all()
                history = fit['history']
                assert 1 <= len(history) <= 12
                assert [r['iteration'] for r in history] == list(range(len(history)))
                assert all(r['step'] in (1., .5, .25, .125, 0.) for r in history)
                assert all(r['step'] != 0 for r in history[:-1])
                assert np.isfinite([r['objective'] for r in history]).all()
                assert np.all(np.diff([r['objective'] for r in history]) <= 0)
        fold_counts.append(dict(fold=fold, fitting=len(expected),
                                held=len(ids) - len(expected)))

    records = []
    frames = Counter()
    baseline_array_comparisons = 0
    for ident in ids:
        source = PARENT / 'predictions' / (ident + '.npz')
        assert digest(source) == old_manifest[str(source.relative_to(PARENT))]
        with np.load(OUT / 'predictions' / (ident + '.npz')) as z, np.load(source) as parent:
            for key in ('t', 'gt_xy', 'gt_heading', 'gt_valid', 'imu_valid'):
                assert np.array_equal(z[key], parent[key], equal_nan=True), (ident, key)
            expected_support = parent['gt_valid'] & np.isfinite(parent['lambda_0_xy']).all(1)
            for name, old_name in (('v34', 'lambda_0'), ('v121', 'lambda_10')):
                for key in ('motion', 'xy', 'heading'):
                    np.testing.assert_allclose(z[f'{name}_{key}'], parent[f'{old_name}_{key}'],
                                               rtol=1e-10, atol=1e-12)
                    baseline_array_comparisons += 1
            for name in NAMES:
                xy, heading = z[name + '_xy'], z[name + '_heading']
                motion = z[name + '_motion']
                support = z['gt_valid'] & np.isfinite(xy).all(1)
                assert np.array_equal(support, expected_support), (ident, name, 'support')
                assert np.isfinite(heading[support]).all()
                assert np.isfinite(z['gt_xy'][support]).all()
                assert np.isfinite(z['gt_heading'][support]).all()
                assert np.isfinite(motion[z['imu_valid']]).all()
                assert np.all(np.abs(motion[:, 0] - z['v34_motion'][:, 0]) <= .05 + 1e-12)
                assert np.all(np.abs(motion[:, 2] - z['v34_motion'][:, 2]) <= .02 + 1e-12)
                np.testing.assert_array_equal(motion[:, 1], z['v34_motion'][:, 1])
                errors = np.linalg.norm(xy[support] - z['gt_xy'][support], axis=1)
                dh = heading[support] - z['gt_heading'][support]
                angular = np.arctan2(np.sin(dh), np.cos(dh))
                measured = dict(position_rmse_m=float(np.sqrt(np.mean(errors ** 2))),
                                heading_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(angular ** 2)))),
                                Position_P95_mm=float(np.percentile(errors, 95) * 1000),
                                Last_Supported_Endpoint_Error_mm=float(errors[-1] * 1000))
                row = saved[(ident, name)]
                for key, value in measured.items():
                    close(value, row[key], (ident, name, key))
                assert int(row['scored_frames']) == int(row['Valid_Frame_Count']) == int(support.sum())
                close(measured['position_rmse_m'] * 1000, row['ATE_RMSE_mm'], (ident, name, 'ATE_RMSE_mm'))
                expected_fold = next(i for i, people in enumerate(FOLDS) if row['participant'] in people)
                assert int(row['fold']) == expected_fold
                assert row['participant'] == metadata[ident]['participant']
                assert row['condition'] == metadata[ident]['condition']
                if name in ('v34', 'v121'):
                    old = old_rows[(ident, 0. if name == 'v34' else 10.)]
                    for key in ('position_rmse_m', 'heading_rmse_deg'):
                        close(measured[key], old[key], (ident, name, 'old', key))
                    assert int(old['scored_frames']) == int(support.sum())
                records.append(dict(id=ident, participant=row['participant'],
                                    condition=row['condition'], candidate=name, **measured))
                frames[name] += int(support.sum())

    grouped = {name: [r for r in records if r['candidate'] == name] for name in NAMES}
    choices = {r['candidate']: r for r in run['candidates']}
    assert set(choices) == set(NAMES) - {'v34'}
    derived = []
    baseline = aggregate(grouped['v121'], 'position_rmse_m')
    for name in NAMES[1:]:
        rows = grouped[name]
        choice = choices[name]
        score = aggregate(rows, 'position_rmse_m')
        close(score, choice['equal_participant_mean_position_rmse_m'], (name, 'score'))
        close(aggregate(rows, 'heading_rmse_deg'), choice['equal_participant_mean_heading_rmse_deg'], (name, 'heading'))
        assert choice['trials'] == 207 and choice['participants'] == 12
        guard_pass = True
        worst = {}
        for control in ('v34', 'v121'):
            base_rows = grouped[control]
            actual_guards = {}
            for key, group in (('participant_ratios', 'participant'), ('maneuver_ratios', 'condition')):
                values = aggregate(rows, 'position_rmse_m', group)
                base_values = aggregate(base_rows, 'position_rmse_m', group)
                actual_guards[key] = {v: ratio(value, base_values[v]) for v, value in values.items()}
            actual_guards['metric_ratios'] = {
                k: ratio(aggregate(rows, k), aggregate(base_rows, k)) for k in CORE[1:]}
            for category, values in actual_guards.items():
                assert set(values) == set(choice['guards'][control][category])
                for key, value in values.items():
                    close(value, choice['guards'][control][category][key], (name, control, category, key))
                    guard_pass &= value <= 1.05
                worst[control + '_' + category] = max(values.values())
        eligible = name == 'v121' or (guard_pass and score < baseline)
        assert choice['eligible'] == eligible
        derived.append(dict(candidate=name, eligible=eligible, ATE_mm=score * 1000,
                            max_guard_ratios=worst))
    selected = min((r for r in derived if r['eligible']), key=lambda r: r['ATE_mm'])
    assert selected['candidate'] == run['selected']['candidate'] == 'lambda_10'
    assert run['selected'] == choices[selected['candidate']]
    checkpoint = read(OUT / 'checkpoint.json')
    assert checkpoint == dict(completed_folds=3, rows=1035, status='complete')
    result = dict(status='PASS', reviewed_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Independent sealed TRAIN screen output review; no fit or inference rerun',
                  hash_counts=counts, prior_dependency_source_differences=[],
                  recordings=207, participants=12, no20_recordings=15,
                  candidates=5, paired_prediction_sets=1035, scored_frames=dict(frames),
                  baseline_array_comparisons=baseline_array_comparisons, folds=fold_counts,
                  selected=selected, candidates_reviewed=derived,
                  baseline_v121_ATE_mm=baseline * 1000,
                  benefit_vs_v121_mm=baseline * 1000 - selected['ATE_mm'],
                  output_manifest_sha256=digest(OUT / 'artifact_manifest.json'),
                  review_script_sha256=digest(Path(__file__)),
                  checks=['all output/input/source hashes; exact file coverage',
                          'frozen v121 dependencies unchanged',
                          'exact207 IDs/all15 No20; all3 fitting exclusions',
                          'frozen normalization and permitted penalties/history',
                          'all207 controls vs sealed v121 motions/XY/headings and label arrays',
                          'all1035 exact paired supports and finite supported predictions',
                          'caps .05 m/s and .02 rad/s; unchanged lateral motion',
                          'direct trial XY RMSE/heading/P95/last-supported endpoint',
                          'direct equal-person summary and every guard vs both controls',
                          'candidate eligibility and selected winner reconstructed'],
                  limitations=['Conditional post-selection TRAIN result; no generalization claim',
                               'Package/report review deferred; no validation/test/raw acquisition access',
                               'Synthetic tests reported passing by coordinator; child execution blocked'])
    target = ROOT / 'research_state/v124_independent_review.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
