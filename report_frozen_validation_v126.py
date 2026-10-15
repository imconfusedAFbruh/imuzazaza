"""Summarize one sealed frozen comparison; no recording or model evaluation."""
import csv
import json
import numpy as np
import pipeline as p
from report_frozen_validation_v123 import group_metrics
from reservoir_stability_v122 import summarize as stability

SOURCE = p.ROOT/'outputs_frozen_validation_v126'
OUT = p.ROOT/'outputs_frozen_validation_v126_report'


def main():
    inputs = {}
    def pin(path):
        name, sha = str(path.relative_to(p.ROOT)), p.digest(path)
        if name in inputs and inputs[name] != sha:
            raise ValueError('Report input changed: '+name)
        inputs[name] = sha
        return path
    manifest = json.loads(pin(SOURCE/'artifact_manifest.json').read_text())['sha256']
    def sealed(name):
        path = pin(SOURCE/name)
        if inputs[str(path.relative_to(p.ROOT))] != manifest[name]:
            raise ValueError('Changed sealed comparison input: '+name)
        return path
    run = json.loads(sealed('run.json').read_text())
    protocol = json.loads(sealed('protocol.json').read_text())
    for name in ('report_frozen_validation_v126.py', 'report_frozen_validation_v123.py',
                 'reservoir_stability_v122.py', 'pipeline.py'):
        pin(p.ROOT/name)
    for folder, sha in (('models/axis_prior_v125', protocol['candidate_sha256']),
                        ('models/reservoir_path_v121_completed', protocol['control_sha256'])):
        pin(p.ROOT/folder/'artifact_manifest.json')
        if p.digest(pin(p.ROOT/folder/'model.json')) != sha:
            raise ValueError('Frozen model changed')
    rows, groups = {}, []
    for name in ('v34', 'v121', 'v125'):
        with sealed(name+'_trials.csv').open(newline='') as stream:
            rows[name] = list(csv.DictReader(stream))
        assert len(rows[name]) == len({r['id'] for r in rows[name]}) == 71
        assert sum(int(r['scored_frames']) for r in rows[name]) == 105821
        groups.extend(group_metrics(rows[name], name))
    OUT.mkdir(exist_ok=False)
    p.write_csv(OUT/'grouped_metrics.csv', groups)
    def value(name, key='position_rmse_m', dimension='overall', group='all'):
        return next(r['equal_person_mean'] for r in groups if r['model'] == name and
                    r['metric'] == key and r['group_type'] == dimension and r['group'] == group)
    people = sorted({r['participant'] for r in rows['v125']})
    assert len(people) == 4
    benefit = np.array([1000*(value('v121', dimension='participant', group=person)-
                             value('v125', dimension='participant', group=person)) for person in people])
    stats = dict(stability(benefit), participant_benefits_mm=dict(zip(people, benefit.tolist())),
                 participants_improved=int((benefit > 0).sum()), previously_exposed_validation_only=True)
    p.save_json(OUT/'stability.json', stats)
    decision = run['decision']
    passed = decision['eligible']
    baseline, candidate = 1000*value('v121'), 1000*value('v125')
    best = 'v125' if passed else 'v121'
    lines = ['# v126: frozen v125 validation results', '',
             f"V125 {'passes' if passed else 'fails'} the predeclared dual-control comparison.",
             f'Matched equal-person XY ATE: v121 **{baseline:.9f} mm** -> v125 **{candidate:.9f} mm**',
             f'({baseline-candidate:+.9f}mm benefit, {100*(baseline-candidate)/baseline:+.6f}%).',
             f'Best completed guard-passing validation model: **{best}**.',
             'All71 previously exposed validation records/four people/105821 scored frames',
             'retained. No refit, alternative candidate, tuning, test use or deployment.', '',
             '## Method and frozen identity', '',
             'The TRAIN-only v125 study fixed speed/yaw prior strengths(1,10), retaining',
             'the v124 trial-RMSE loss, v121 prior/normalization and fixed16-state reservoir.',
             'All207 public inference/poisoning checks and independent TRAIN reviews passed',
             'before this comparison. The model was frozen before validation access.',
             f"Candidate model SHA256: `{protocol['candidate_sha256']}`.",
             'User renewed the model request after the concrete frozen-comparison proposal;',
             'that contextual direction was recorded before execution in frozen_validation_v126.md.',
             'Original IMU startup and both public controls were reconstructed for all71',
             'before any v125 prediction. Frozen v123 tolerances and four-thread CPU were',
             'retained. Identical clocks/crops/reference/support and original single initial',
             'pose were used. Motion prediction received only sensor/setup/IMU initialization.',
             'V125 was then evaluated once, with exact finite support against both controls.', '',
             '## Equal-person metrics', '', '| Metric | v34 | v121 | v125 |',
             '| --- | ---: | ---: | ---: |']
    for key in ('ATE_RMSE_mm', 'Position_P95_mm', 'Last_Supported_Endpoint_Error_mm',
                'heading_rmse_deg', 'Route_RMSE_mm', 'Route_P95_mm', 'RTE_1s_mm', 'RTE_5s_mm', 'RTE_10s_mm'):
        vv = [value(name, key) for name in ('v34', 'v121', 'v125')]
        lines.append('| '+key+' | '+' | '.join(f'{x:.6f}' if x != '' else 'unavailable' for x in vv)+' |')
    for dimension, title in (('participant', 'Participant'), ('condition', 'Maneuver')):
        lines += ['', '## '+title+' results', '', f'| {title} | v34 mm | v121 mm | v125 mm |',
                  '| --- | ---: | ---: | ---: |']
        for label in sorted({r[dimension] for r in rows['v125']}):
            vv = [1000*value(name, dimension=dimension, group=label) for name in ('v34', 'v121', 'v125')]
            lines.append('| '+label+' | '+' | '.join(f'{x:.6f}' for x in vv)+' |')
    lines += ['', '## Original guard decisions', '']
    for control, outcome in decision['controls'].items():
        lines += [f"### Against {control}: {'PASS' if outcome['eligible'] else 'FAIL'}", '',
                  'Failed guards: '+(', '.join(outcome['failed_guards']) or 'none')+'.', '',
                  '| Guard class | Group | Ratio |', '| --- | --- | ---: |']
        for kind in ('participant_ratios', 'maneuver_ratios', 'guard_ratios'):
            for label, ratio in outcome[kind].items():
                lines.append(f"| {kind} | {label} | {ratio:.9f} |" if ratio is not None else f'| {kind} | {label} | failed positive-over-zero |')
    lines += ['', '## Availability and uncertainty', '',
              '| Model/metric | Available records | Available people |', '| --- | ---: | ---: |']
    for row in groups:
        if row['group_type'] == 'overall' and row['metric'] in ('RTE_1s_mm', 'RTE_5s_mm', 'RTE_10s_mm'):
            lines.append(f"| {row['model']}/{row['metric']} | {row['available_trials']}/{row['total_trials']} | {row['available_participants']}/{row['total_participants']} |")
    lines += ['', f"{stats['participants_improved']}/4 participants improve against v121.",
              f"Descriptive bootstrap95 benefit interval: {stats['bootstrap_percentile95_mm']}mm.",
              f"Exact sign-flip fraction: {stats['two_sided_sign_flip_fraction']:.9f} over {stats['sign_flips']} signs.",
              'These small-cohort, previously exposed development-validation summaries',
              'do not establish independent significance or blind final generalization.',
              'The TRAIN127.531627048mm result describes a different cohort and is not',
              'directly compared to these validation scores. All diagnostic metrics and',
              'availability denominators are preserved in the grouped CSV. Genuine',
              'acquisition endpoints are unavailable; last-supported endpoint is distinct.',
              'Inherited266 parent training records, offline context/optical crops, and',
              'unresolved independent clocks/firmware/runtime/geometry/final data persist.',
              'No model or prior artifact was changed by this evaluation. The bundle',
              'validation_evaluated=false field records its earlier freeze-time status;',
              'this separate sealed comparison records subsequent evaluation.', '',
              'Independent review completion is recorded separately in',
              '`research_state/v126_independent_review.json`; sealed run status is historical.', '']
    report = p.ROOT/'research_docs/frozen_validation_results_v126.md'
    assert not report.exists()
    report.write_text('\n'.join(lines), encoding='utf-8')
    pin(report)
    for name, sha in inputs.items():
        if p.digest(p.ROOT/name) != sha:
            raise ValueError('Report input changed: '+name)
    p.save_json(OUT/'run.json', dict(inputs=inputs, grouped_rows=len(groups), prediction_evaluations=0))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={f.name: p.digest(f) for f in OUT.iterdir() if f.is_file()}))
    print(json.dumps(dict(eligible=passed, best_completed_validation=best,
                         v121_ATE_mm=baseline, v125_ATE_mm=candidate, benefit_mm=baseline-candidate)), flush=True)


if __name__ == '__main__':
    main()
