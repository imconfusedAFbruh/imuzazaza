"""Check previously reported minima against sealed trial summaries only."""
import csv
import json
from pathlib import Path
from matched_maneuver_audit_v115 import balanced, digest, ROOT

OUT = ROOT / 'outputs_maneuver_minima_provenance_v116'
CASES = [
    ('10x5', 'outputs_clock_arbitrated_v42', 'common_native', 'new_clock_refit_blend'),
    ('AR', 'outputs_long_horizon_v9', '', 'endpoint_44'),
    ('CR', 'outputs_nonlinear_endpoint_tuning_v22', '', 'selected'),
    ('OS', 'outputs_observed_sync_v9', '', 'physics_bootstrap_alignment'),
    ('PS', 'outputs_clock_refit_v38', 'common_native', 'new_clock_refit_blend'),
    ('SL', 'outputs_clock_refit_v38', 'own_clock_full', 'new_clock_refit_blend'),
    ('ST', 'outputs_clock_arbitrated_v42', 'own_clock_full', 'new_clock_refit_blend'),
]


def main():
    inputs = {}

    def read(folder, name):
        path = ROOT / folder / name
        manifest = json.loads((ROOT / folder / 'artifact_manifest.json').read_text())['sha256']
        assert digest(path) == manifest[name], path
        inputs[str(path.relative_to(ROOT))] = digest(path)
        with path.open(newline='') as f:
            return list(csv.DictReader(f))

    baseline = read('outputs_dynamic_blend_v34', 'selected_blend_trials.csv')
    control = {r['id']: r for r in baseline}
    assert len(baseline) == len(control) == 71
    table = []
    for maneuver, folder, evaluation, method in CASES:
        trial_file = (evaluation if evaluation else method) + '_trials.csv'
        summary_file = (evaluation + '_' if evaluation else '') + method + '_maneuvers.csv'
        trials = read(folder, trial_file)
        if evaluation:
            trials = [r for r in trials if r['method'] == method]
        assert len(trials) == 71 and len({r['id'] for r in trials}) == 71
        assert {r['id'] for r in trials} == set(control)
        for r in trials:
            assert all(r[k] == control[r['id']][k] for k in ('participant', 'condition'))
        rows = [dict(r, participant_id=r['participant'], score=1000 * float(r['position_rmse_m']))
                for r in trials]
        group = [r for r in rows if r['condition'] == maneuver]
        summary = [r for r in read(folder, summary_file) if r['condition'] == maneuver]
        assert len(summary) == 1
        value = balanced(group)
        assert abs(value - 1000 * float(summary[0]['equal_participant_mean_position_rmse_m'])) < 1e-9
        assert len(group) == int(summary[0]['trials'])
        table.append(dict(maneuver=maneuver, source=folder, method=method,
                          evaluation=evaluation or 'historical original evaluation',
                          maneuver_ATE_mm=value, whole_model_ATE_mm=balanced(rows),
                          trials=len(group), people=len({r['participant'] for r in group}),
                          maneuver_frame_count_differences=sum(r['scored_frames'] != control[r['id']]['scored_frames'] for r in group),
                          all71_frame_count_differences=sum(r['scored_frames'] != control[r['id']]['scored_frames'] for r in rows)))
    OUT.mkdir(exist_ok=False)
    with (OUT / 'provenance.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    result = dict(experiment='v116', input_hashes=inputs,
                  protocol_sha256=digest(ROOT / 'research_docs/maneuver_minima_provenance_v116.md'),
                  helper_sha256=digest(ROOT / 'matched_maneuver_audit_v115.py'),
                  raw_or_prediction_reads=0, test_accessed=False, promotion=False,
                  qualification='equal frame counts do not establish identical support, clocks or initial pose')
    (OUT / 'run.json').write_text(json.dumps(result, indent=2))
    (OUT / 'artifact_manifest.json').write_text(json.dumps(dict(
        sha256={p.name: digest(p) for p in OUT.iterdir() if p.is_file()},
        source_sha256=digest(Path(__file__))), indent=2))
    print(json.dumps(table, indent=2))


if __name__ == '__main__':
    main()
