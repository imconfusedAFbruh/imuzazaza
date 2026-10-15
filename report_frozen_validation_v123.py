"""Reporting only from sealed v123 trial tables; no model or data evaluation."""
import csv
import json
import math
import statistics
from pathlib import Path
import pipeline as p

SOURCE=p.ROOT/'outputs_frozen_validation_v123_exact'
OUT=p.ROOT/'outputs_frozen_validation_v123_report'


def number(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None


def group_metrics(rows,model):
    keys=[k for k in rows[0] if k not in ('id','participant','condition')
          and any(number(r[k]) is not None for r in rows)]
    groups=[('overall','all',rows)]
    for dimension in ('participant','condition'):
        for value in sorted({r[dimension] for r in rows}):
            groups.append((dimension,value,[r for r in rows if r[dimension]==value]))
    result=[]
    for dimension,value,group in groups:
        people=sorted({r['participant'] for r in group})
        for key in keys:
            available=[r for r in group if number(r[key]) is not None]
            means=[statistics.mean(number(r[key]) for r in available if r['participant']==person)
                   for person in people if any(r['participant']==person for r in available)]
            result.append(dict(model=model,group_type=dimension,group=value,metric=key,
                equal_person_mean=statistics.mean(means) if means else '',
                available_trials=len(available),total_trials=len(group),
                available_participants=len(means),total_participants=len(people),
                missing_trials=len(group)-len(available)))
    return result


def main():
    OUT.mkdir(exist_ok=False)
    manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256'];inputs={}
    def read(name):
        path=SOURCE/name;sha=p.digest(path)
        if sha!=manifest[name]:raise ValueError('Changed sealed table: '+name)
        inputs[name]=sha
        return path
    run=json.loads(read('run.json').read_text());decision=run['decision']
    rows={model:list(csv.DictReader(read(model+'_trials.csv').open(newline='')))
          for model in ('baseline','candidate')}
    table=[]
    for model,rr in rows.items():table.extend(group_metrics(rr,model))
    p.write_csv(OUT/'grouped_metrics.csv',table)
    def mean(model,key,group_type='overall',group='all'):
        return next(r['equal_person_mean'] for r in table if r['model']==model and r['metric']==key
                    and r['group_type']==group_type and r['group']==group)
    b=1000*decision['baseline']['equal_participant_mean_position_rmse_m']
    c=1000*decision['candidate']['equal_participant_mean_position_rmse_m']
    report=[
        '# v123: frozen v121 passes the matched validation comparison', '',
        f'14 October 2026. Equal-person XY ATE improves **{b:.9f} -> {c:.9f} mm**',
        f'({b-c:.6f} mm / {100*(b-c)/b:.3f}% lower), on all71 identical exposed validation',
        'recordings/four participants. Every predeclared guard passes. This is conditional',
        'development validation, not a new blind test or proof of published-method superiority.',
        'No deployment promotion, refit, retuning, alternative candidate, reserved-test',
        'evaluation, commit or push. Independent review status is recorded separately in',
        '`research_state/v123_independent_review.json`; the sealed run retains its at-execution status.', '',
        '## How this result was obtained', '',
        'The earlier v121 TRAIN search reproduced frozen v34, added a fixed 16-state',
        'temporal reservoir over gravity-rotation IMU features, and optimized bounded',
        'forward/yaw residuals through exact integrated trajectory loss. Three fixed',
        'penalties were screened in participant folds; penalty10 passed every guard.',
        'Penalty1 had lower TRAIN error but failed participant guards. The selected',
        'readout was fitted on all207 identified TRAIN records and frozen before this',
        'comparison. v122 stability analysis was descriptive, not another selection step.', '',
        'After explicit user authorization, the evaluation-only v123 runner reconstructed',
        'native IMU startup initialization and reproduced every saved v34 motion, trajectory,',
        'heading, identity, metric and reference/support array before any v121 prediction.',
        'It then evaluated the frozen v121 package once with the same time grid, clock maps,',
        'crop, reference masks and one original optical initial pose. Prediction inputs',
        'contained only sensor/setup/IMU initialization. No optical feedback or alignment.', '',
        'Two implementation failures were preserved: virtual PyTorch `_ops.py` has no',
        'source file; then a baseline-only check exposed the historical two-thread floating',
        'point residual. Restoring the original v33 producer four-thread configuration',
        'gave exact reproduction without changing any tolerance. Both failed attempts',
        'evaluated zero candidate recordings. The final guarded run completed exit0.', '',
        '## Matched participant results', '',
        '| Participant | v34 ATE mm | v121 ATE mm | Change |',
        '| --- | ---: | ---: | ---: |']
    for person,ratio in decision['participant_ratios'].items():
        report.append(f"| {person} | {1000*mean('baseline','position_rmse_m','participant',person):.6f} | {1000*mean('candidate','position_rmse_m','participant',person):.6f} | {100*(ratio-1):+.3f}% |")
    report.extend(['','## Matched maneuver results','','| Maneuver | v34 ATE mm | v121 ATE mm | Change |','| --- | ---: | ---: | ---: |'])
    for cond,ratio in decision['maneuver_ratios'].items():
        report.append(f"| {cond} | {1000*mean('baseline','position_rmse_m','condition',cond):.6f} | {1000*mean('candidate','position_rmse_m','condition',cond):.6f} | {100*(ratio-1):+.3f}% |")
    report.extend(['','## Additional outcomes','','| Metric (equal-person mean) | v34 | v121 |','| --- | ---: | ---: |'])
    for key in ('Position_P95_mm','Last_Supported_Endpoint_Error_mm','heading_rmse_deg',
                'Route_RMSE_mm','Route_P95_mm','RTE_1s_mm','RTE_5s_mm','RTE_10s_mm',
                'Scored_Coverage_pct','C3D_Coverage_pct'):
        report.append(f"| {key} | {mean('baseline',key):.6f} | {mean('candidate',key):.6f} |")
    report.extend(['', 'P95 position, last-supported endpoint and heading guard ratios are respectively',
        ', '.join(f"{decision['guard_ratios'][key]:.9f}" for key in ('Position_P95_mm','Last_Supported_Endpoint_Error_mm','heading_rmse_deg'))+'.',
        'All are below1.05; every participant and maneuver ATE ratio is also below1.05.',
        'No.5, PS and SL worsen slightly; the favorable mean is not uniform improvement.', '',
        '`outputs_frozen_validation_v123_report/grouped_metrics.csv` contains all numeric',
        'legacy/v74 metrics at overall, participant and maneuver level. Means exclude',
        'missing values, and every row reports available/total trial and participant',
        'counts. Maneuvers average participant means, not pooled trials. Frame/window',
        'count fields are explicitly mean counts in this table; per-record counts remain',
        'in the sealed trial tables. Unsupported genuine endpoint metrics remain missing.',
        'RTE at different durations can have different eligible records; use denominators.', '',
        '## Artifacts and limitations', '',
        '- `outputs_frozen_validation_v123_exact`: all71 paired predictions, baseline audit,',
        '  full per-record metrics, participant/maneuver tables, input/source/output hashes.',
        '- `models/reservoir_path_v121_completed/model.json`: unchanged frozen candidate;',
        '  SHA256 `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`.',
        '- `research_docs/frozen_validation_v123.md`: authorization, fixed tolerances,',
        '  support/guard contract and preserved implementation-failure history.', '',
        'The full pipeline still inherits calibration and266 parent training records,',
        'offline future context, optical-dependent crop and unresolved independent-clock',
        'and firmware provenance assumptions. These71 validation records have prior',
        'development exposure. Historical test is not blind. Independent final data and',
        'a faithful external comparator remain needed; no further candidate tuning is',
        'authorized by this comparison. The next authorized work is independent review',
        'and evidence consolidation; numerical evaluation is complete.', ''])
    path=p.ROOT/'research_docs/frozen_validation_results_v123.md'
    if path.exists():raise RuntimeError('Preserve existing report')
    path.write_text('\n'.join(report),encoding='utf-8')
    p.save_json(OUT/'run.json',dict(input_hashes=inputs,source_sha256=p.digest(Path(__file__)),
        report_sha256=p.digest(path),grouped_rows=len(table),prediction_evaluations=0,
        aggregation='equal participant mean among available records, explicit denominators'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={f.name:p.digest(f) for f in OUT.iterdir() if f.is_file()}))
    print(json.dumps(dict(ATE_baseline_mm=b,ATE_candidate_mm=c,benefit_mm=b-c,grouped_metric_rows=len(table)),indent=2))


if __name__=='__main__':main()
