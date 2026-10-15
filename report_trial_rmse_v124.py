"""Report sealed v124 TRAIN results; no fitting or recording evaluation."""
import csv
import json
import numpy as np
import pipeline as p
from combined_physics_folds_v58 import verified_json
from report_frozen_validation_v123 import group_metrics
from reservoir_stability_v122 import summarize as stability

SOURCE = p.ROOT/'outputs_trial_rmse_v124'
OUT = p.ROOT/'outputs_trial_rmse_v124_report'


def main():
    OUT.mkdir(exist_ok=False)
    run = verified_json(SOURCE, 'run.json')
    manifest = json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    assert p.digest(SOURCE/'trials.csv') == manifest['trials.csv']
    with (SOURCE/'trials.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    selected = run['selected']
    name = selected['candidate']
    groups = []
    for model in sorted({r['candidate'] for r in rows}):
        rr = [{k: v for k, v in r.items() if k not in ('candidate', 'fold')}
              for r in rows if r['candidate'] == model]
        assert len(rr) == len({r['id'] for r in rr}) == 207
        groups.extend(group_metrics(rr, model))
    p.write_csv(OUT/'grouped_metrics.csv', groups)
    def value(model, metric, dimension='overall', group='all'):
        return next(r['equal_person_mean'] for r in groups if r['model'] == model
                    and r['metric'] == metric and r['group_type'] == dimension and r['group'] == group)
    people = sorted({r['participant'] for r in rows})
    benefit = np.array([1000*(value('v121', 'position_rmse_m', 'participant', person)-
                             value(name, 'position_rmse_m', 'participant', person)) for person in people])
    stats = dict(stability(benefit), participant_benefits_mm=dict(zip(people, benefit.tolist())),
                 participants_improved=int((benefit > 0).sum()), conditional_post_selection_train_only=True)
    p.save_json(OUT/'stability.json', stats)
    baseline = 1000*value('v121', 'position_rmse_m')
    candidate = 1000*value(name, 'position_rmse_m')
    lines = ['# v124: trial-RMSE readout results', '',
             f'Matched TRAIN XY ATE: v121 **{baseline:.9f} mm** -> selected **{candidate:.9f} mm**',
             f'({100*(baseline-candidate)/baseline:.6f}% lower). Selected `{name}`. All207 recordings,',
             '12 participants and all15 No20 retained on the same original clocks/crops/support.', '',
             '| Readout | ATE mm | Heading RMSE degrees | Eligible |',
             '| --- | ---: | ---: | --- |']
    for c in run['candidates']:
        lines.append(f"| {c['candidate']} | {1000*c['equal_participant_mean_position_rmse_m']:.6f} | {c['equal_participant_mean_heading_rmse_deg']:.6f} | {c['eligible']} |")
    lines += ['', '## How the model was obtained', '',
              'Reviewed v121 code and previous rejected models. Kept the fixed16-state temporal',
              'reservoir, TRAIN-fold normalization, .05m/s/.02rad/s correction caps and frozen',
              'v34 motion. Reproduced all207 v34 and v121 motions, trajectories, support and',
              'primary metrics before any candidate fit. Changed the training objective from',
              'mean squared path error to smoothed mean trial XY RMSE plus heading RMSE,',
              'with a quadratic prior at the frozen v121 weights. Three predeclared prior',
              'penalties .1/1/10; twelve GN/IRLS steps and fitting-only line search. Each',
              'held participant stays outside its fit, normalization and prior fitting.',
              'Every original participant/maneuver/tail/endpoint/heading guard must pass',
              'against both v121 and v34. No clock, mask or gate changes.', '',
              '## Selected result on identical support', '',
              '| Maneuver | v34 mm | v121 mm | Selected mm |',
              '| --- | ---: | ---: | ---: |']
    for condition in sorted({r['condition'] for r in rows}):
        vv = [1000*value(model, 'position_rmse_m', 'condition', condition) for model in ('v34', 'v121', name)]
        lines.append(f'| {condition} | {vv[0]:.6f} | {vv[1]:.6f} | {vv[2]:.6f} |')
    lines += ['', '| Participant | v121 mm | Selected mm | Benefit mm |',
              '| --- | ---: | ---: | ---: |']
    for person, gain in zip(people, benefit):
        b = 1000*value('v121', 'position_rmse_m', 'participant', person)
        c = 1000*value(name, 'position_rmse_m', 'participant', person)
        lines.append(f'| {person} | {b:.6f} | {c:.6f} | {gain:+.6f} |')
    lines += ['', 'All candidate guard ratios are preserved in `outputs_trial_rmse_v124/run.json`.',
              'All historical and v74 supplementary metrics are in the sealed trial table;',
              '`outputs_trial_rmse_v124_report/grouped_metrics.csv` includes equal-participant',
              'overall/participant/maneuver means and explicit availability denominators.', '',
              '## Uncertainty and evidence limits', '',
              f"{stats['participants_improved']}/12 participants improve. Leave-one-person-out mean benefit range",
              f"{min(stats['leave_one_person_out_benefits_mm']):.6f} to {max(stats['leave_one_person_out_benefits_mm']):.6f}mm.",
              f"Descriptive bootstrap95 interval {stats['bootstrap_percentile95_mm']}; exact paired sign-flip fraction {stats['two_sided_sign_flip_fraction']:.9f}.",
              'These are conditional post-selection TRAIN summaries, without an independent',
              'significance/generalization claim. Historical parent calibration and266 other',
              'training-record dependence persist. Offline future context, optical-dependent',
              'crops and unresolved independent clocks/firmware/acquisition provenance remain.',
              'No v124 validation/test scoring, deployment, commit or push. The completed v121',
              'exposed validation score99.303735166mm stays a separate result.', '',
              'Independent review status: `research_state/v124_independent_review.json`.',
              'Synthetic checks cover all34 objective derivatives including saturation,',
              'monotone/deterministic fitting, exact-prior and original integration Jacobian.', '']
    bundle = p.ROOT/'models/trial_rmse_v124'
    if (bundle/'verification.json').exists():
        verification = verified_json(bundle, 'verification.json')
        lines += ['## Frozen callable bundle', '',
                  '`models/trial_rmse_v124`: selected penalty fitted once on all207 TRAIN',
                  'using frozen full-TRAIN v121 prior/normalization and v34 parent.',
                  f"All{verification['recordings']} sensor-only inference reproductions pass; maximum motion difference {verification['maximum_motion_difference']:.3g}.",
                  'Every optical/identity poisoning check passes. These are package reproduction',
                  'checks, not held-out scores.', '', '```python',
                  'from reservoir_inference_v121 import load_reservoir_model',
                  "predict = load_reservoir_model('models/trial_rmse_v124')", 'motion = predict(sensor)',
                  '```', '', f"Model JSON SHA256: `{p.digest(bundle/'model.json')}`.", '']
    report = p.ROOT/'research_docs/trial_rmse_results_v124.md'
    report.write_text('\n'.join(lines), encoding='utf-8')
    dependencies = [SOURCE/'artifact_manifest.json', SOURCE/'trials.csv', SOURCE/'run.json',
                    p.ROOT/'report_trial_rmse_v124.py', p.ROOT/'report_frozen_validation_v123.py',
                    p.ROOT/'reservoir_stability_v122.py', report]
    p.save_json(OUT/'run.json', dict(inputs={str(f.relative_to(p.ROOT)): p.digest(f) for f in dependencies},
                grouped_rows=len(groups), prediction_evaluations=0))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={f.name: p.digest(f) for f in OUT.iterdir() if f.is_file()}))
    print(json.dumps(dict(selected=name, TRAIN_ATE_mm=candidate, benefit_mm=baseline-candidate,
                          participants_improved=stats['participants_improved'])), flush=True)


if __name__ == '__main__':
    main()
