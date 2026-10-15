"""Report sealed v125 TRAIN outputs without fitting or evaluating recordings."""
import csv
import json
import numpy as np
import pipeline as p
from combined_physics_folds_v58 import verified_json
from report_frozen_validation_v123 import group_metrics
from reservoir_stability_v122 import summarize as stability

SOURCE = p.ROOT/'outputs_axis_prior_v125'
OUT = p.ROOT/'outputs_axis_prior_v125_report'


def main():
    OUT.mkdir(exist_ok=False)
    run = verified_json(SOURCE, 'run.json')
    manifest = json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    assert p.digest(SOURCE/'trials.csv') == manifest['trials.csv']
    with (SOURCE/'trials.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    selected = run['selected']['candidate']
    groups = []
    for model in sorted({r['candidate'] for r in rows}):
        rr = [{k: v for k, v in r.items() if k not in ('candidate', 'fold')}
              for r in rows if r['candidate'] == model]
        assert len(rr) == len({r['id'] for r in rr}) == 207
        groups.extend(group_metrics(rr, model))
    p.write_csv(OUT/'grouped_metrics.csv', groups)
    def value(model, metric='position_rmse_m', dimension='overall', group='all'):
        return next(r['equal_person_mean'] for r in groups if r['model'] == model
                    and r['metric'] == metric and r['group_type'] == dimension and r['group'] == group)
    people = sorted({r['participant'] for r in rows})
    benefit = np.array([1000*(value('v124', dimension='participant', group=person)-
                             value(selected, dimension='participant', group=person)) for person in people])
    stats = dict(stability(benefit), participant_benefits_mm=dict(zip(people, benefit.tolist())),
                 participants_improved=int((benefit > 0).sum()), conditional_post_selection_train_only=True)
    p.save_json(OUT/'stability.json', stats)
    base, current = 1000*value('v124'), 1000*value(selected)
    lines = ['# v125: separate speed/yaw prior results', '',
             f'Matched TRAIN XY ATE: v124 **{base:.9f} mm** -> selected **{current:.9f} mm**.',
             f'Selected `{selected}`; {100*(base-current)/base:.6f}% lower.',
             'All207 recordings/12 people/15 No20/314498 scored frames retained.', '',
             '| Readout | ATE mm | Heading degrees | Eligible |',
             '| --- | ---: | ---: | --- |']
    for c in run['candidates']:
        lines.append(f"| {c['candidate']} | {1000*c['equal_participant_mean_position_rmse_m']:.6f} | {c['equal_participant_mean_heading_rmse_deg']:.6f} | {c['eligible']} |")
    lines += ['', '## Method', '',
              'Kept v124 trial-RMSE/heading loss, v121 prior/normalization, fixed16-state',
              'reservoir, frozen v34 motion, caps, original folds/clocks/crops/support.',
              'Changed only the speed/yaw prior strengths: exactly (1,10), (10,1),',
              '(3,3), specified before fitting. Reproduced all207 trajectories for',
              'v34/v121/v124 first. Fit only on the other participants with twelve',
              'GN/IRLS iterations and fitting-only line search. Selection requires',
              'lower equal-person ATE than v124 and every original5% guard against',
              'ALL THREE controls. No participant/maneuver identity enters inference.',
              'Synthetic checks verify all34 gradients including saturation, exact',
              'scalar equivalence, deterministic monotone fits and exact prior.', '',
              '## Guard failures', '']
    for c in run['candidates']:
        failures = [(control, kind, group, ratio) for control, guard in c['guards'].items()
                    for kind, ratios in guard.items() for group, ratio in ratios.items() if ratio > 1.05]
        lines.append(f"- `{c['candidate']}`: "+('; '.join(
            f'{control}/{kind}/{group}={ratio:.9f}' for control, kind, group, ratio in failures)
            if failures else 'none; all regression guards pass.'))
    lines += ['', '## Matched maneuver results', '',
              '| Maneuver | v34 mm | v121 mm | v124 mm | Selected mm |',
              '| --- | ---: | ---: | ---: | ---: |']
    for condition in sorted({r['condition'] for r in rows}):
        values = [1000*value(model, dimension='condition', group=condition)
                  for model in ('v34', 'v121', 'v124', selected)]
        lines.append('| '+condition+' | '+' | '.join(f'{x:.6f}' for x in values)+' |')
    lines += ['', '| Participant | v124 mm | Selected mm | Benefit mm |',
              '| --- | ---: | ---: | ---: |']
    for person, gain in zip(people, benefit):
        b = 1000*value('v124', dimension='participant', group=person)
        c = 1000*value(selected, dimension='participant', group=person)
        lines.append(f'| {person} | {b:.6f} | {c:.6f} | {gain:+.6f} |')
    lines += ['', '## Evidence limits', '',
              f"{stats['participants_improved']}/12 participants improve against v124.",
              f"Descriptive bootstrap95 benefit interval: {stats['bootstrap_percentile95_mm']}mm.",
              f"Exact sign-flip fraction: {stats['two_sided_sign_flip_fraction']:.9f}.",
              'These are conditional post-selection TRAIN summaries. Repeated development',
              'exposure,266 inherited parent training records, offline future context,',
              'optical crops and unresolved clocks/acquisition/runtime identity remain.',
              'v12199.303735166mm remains the best completed exposed validation result.',
              'No new validation/test scoring, deployment, commit or push.',
              'All supplementary metrics/availability denominators are retained in',
              '`outputs_axis_prior_v125_report/grouped_metrics.csv`.',
              'Independent screen review: `research_state/v125_independent_review.json`.', '']
    dependencies = [SOURCE/'artifact_manifest.json', SOURCE/'trials.csv', SOURCE/'run.json',
                    p.ROOT/'report_axis_prior_v125.py', p.ROOT/'report_frozen_validation_v123.py',
                    p.ROOT/'reservoir_stability_v122.py', p.ROOT/'pipeline.py',
                    p.ROOT/'combined_physics_folds_v58.py']
    bundle = p.ROOT/'models/axis_prior_v125'
    if selected != 'v124':
        verification = verified_json(bundle, 'verification.json')
        dependencies += [bundle/'artifact_manifest.json', bundle/'model.json', bundle/'verification.json']
        lines += ['## Frozen callable bundle', '', '`models/axis_prior_v125`.',
                  f"All{verification['recordings']} public inference reproductions and optical/identity poisoning checks pass; maximum motion difference {verification['maximum_motion_difference']:.3g}.",
                  'These full-TRAIN package checks are distinct from participant-fold scores.',
                  f"Model JSON SHA256: `{p.digest(bundle/'model.json')}`.", '']
    report = p.ROOT/'research_docs/axis_prior_results_v125.md'
    assert not report.exists()
    report.write_text('\n'.join(lines), encoding='utf-8')
    dependencies.append(report)
    p.save_json(OUT/'run.json', dict(inputs={str(f.relative_to(p.ROOT)): p.digest(f) for f in dependencies},
                grouped_rows=len(groups), prediction_evaluations=0))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={f.name: p.digest(f) for f in OUT.iterdir() if f.is_file()}))
    print(json.dumps(dict(selected=selected, TRAIN_ATE_mm=current, benefit_mm=base-current,
                         participants_improved=stats['participants_improved'])), flush=True)


if __name__ == '__main__':
    main()
