"""Document completed sealed TRAIN results without fitting or new predictions."""
import csv
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
out = ROOT/'outputs_joint_robust_motion_v119'
run = json.loads((out/'run.json').read_text())
lines = ['# Authorized TRAIN-only robust motion screen v119', '',
    'User authorized one additional family/max3 configurations. Guarded run completed',
    'all207 TRAIN recordings/12participants/all15 No20, three participant folds.',
    'All207 frozen v52 baseline scores/counts reproduced before candidate scoring.',
    'No new validation/test evaluation, promotion, commit or push.', '',
    '| Delta | Equal-person XY ATE (mm) | Heading RMSE (deg) | Worst person ratio | Worst maneuver ratio | Eligible |',
    '| --- | ---: | ---: | ---: | ---: | --- |']
for c in run['candidates']:
    lines.append(f"| {c['delta']:g} | {1000*c['equal_participant_mean_position_rmse_m']:.6f} | {c['equal_participant_mean_heading_rmse_deg']:.6f} | {max(c['participant_ratios'].values()):.6f} | {max(c['maneuver_ratios'].values()):.6f} | {c['eligible']} |")
lines += ['', f"TRAIN guard-selected delta: {run['selected']['delta']:g}. This is not promotion.", '',
    'Method: unchanged causal v56 hysteresis features; residual relative to frozen',
    'v52 speed/projected-yaw baseline; TRAIN-fitting group-balanced normalization;',
    'fixed centered target MAD scales, ridge1, eight shared two-component Huber IRLS',
    'updates, delta1.5/3/6 only; correction caps0.1m/s and0.05rad/s, fixed gain0.25.',
    'Held participants excluded from every residual fit and normalization. All four',
    'motions/positions/headings saved per recording for exact support review.', '',
    'Acceptance requires lower overall ATE and <=1.05 for every person/maneuver,',
    'overall trial P95position, last-supported endpoint and heading. All207 must',
    'remain represented. Missing support is never dropped or assigned a score.', '',
    '## Guard details', '']
for c in run['candidates'][1:]:
    lines += [f"Delta{c['delta']:g}: " + '; '.join(f'{k} ratio={v:.6f}' for k,v in c['guard_ratios'].items()),
              'Person/maneuver violations: ' + ', '.join(f'{k}={v:.6f}' for k,v in {**c['participant_ratios'],**c['maneuver_ratios']}.items() if v>1.05)]
lines += ['', '## Every maneuver on identical TRAIN support', '',
    '| Maneuver | Baseline (mm) | Delta1.5 (mm) | Delta3 (mm) | Delta6 (mm) |',
    '| --- | ---: | ---: | ---: | ---: |']
tables = {c['delta']:{r['condition']:float(r['equal_participant_mean_position_rmse_m'])*1000
    for r in csv.DictReader((out/f"delta_{c['delta']:g}_maneuvers.csv").open(newline=''))}
    for c in run['candidates']}
for maneuver in sorted(tables[0]):
    lines.append('| '+maneuver+' | '+' | '.join(f'{tables[d][maneuver]:.6f}' for d in (0,1.5,3,6))+' |')
lines += ['', 'Inherited optical crop/initial pose/clocks and offline projected gravity',
    'proxy remain; this does not resolve the strict all207 timing gate or demonstrate',
    'true attitude, genuine acquisition endpoints or deployment generalization.',
    'Retained historical v34 best remains100.702119399mmATE/49.726226563mmroute on',
    'its separate already-exposed validation evaluation. Do not compare that number',
    'directly with this207 TRAIN-fold mean or treat TRAIN selection as validation.', '',
    'Independent final review passed: all hashes,207 prediction files/828 unique rows,',
    'exact masks/primary guards and eligibility independently reproduced; see',
    'research_state/v119_review.json. Supplementary diagnostics were not all',
    'independently reconstructed. Numeric budget exhausted: no fourth config,',
    'new family, validation scoring or promotion authorized. Next numerical step',
    'requires separate user authorization; strict timing work requires new linked',
    'independent evidence. Completed unsuccessful timing searches should not repeat.']
(ROOT/'research_docs/joint_robust_motion_results_v119.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
checkpoint = '\n'.join(lines[:14]) + '\n\nSee research_docs/joint_robust_motion_results_v119.md.\nIndependent final review passed: all207x4 supports/guard metrics, fit exclusions,\nsource/output hashes and eligibility verified. All3 candidates rejected by ST guard.\nExtra numerical budget exhausted; no new family/configuration/validation/promotion\nauthorized. No live job. Earlier awaiting-approval/running checkpoints are historical.\n\n---\n'
for name in ('NEXT_SESSION','STATUS','TODO','BEST_RESULTS','EXPERIMENTS','FAILED_IDEAS'):
    path = ROOT/f'research_state/{name}.md'
    previous=path.read_text(encoding='utf-8')
    if previous.startswith('# Authorized TRAIN-only robust motion screen v119'):
        previous=previous.split('\n---\n',1)[1]
    path.write_text(checkpoint+previous,encoding='utf-8')
readme = ROOT/'README.md'
previous=readme.read_text(encoding='utf-8').split('\n\n# Authorized TRAIN-only robust motion screen v119',1)[0]
readme.write_text(previous+'\n\n'+ '\n'.join(lines)+'\n',encoding='utf-8')
schedule = ROOT/'research_state/LAST_SCHEDULE_CHECK.json'
state = json.loads(schedule.read_text()); state.update(action='v119 complete and independently reviewed; all3 candidates rejected by ST guard',active_research_jobs=0,next_work='Bounded numerical budget consumed; no new fit or validation without separate authorization or newly linked independent timing evidence')
schedule.write_text(json.dumps(state,indent=2)+'\n')
