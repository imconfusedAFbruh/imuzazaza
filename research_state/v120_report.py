"""Save v120 model development results and handoff from sealed scores."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs_conservative_robust_v120'
run=json.loads((OUT/'run.json').read_text());selected=run['selected'];gain=selected['gain']
card=json.loads((ROOT/'models/conservative_robust_v120/model_card.json').read_text())
review=ROOT/'research_state/v120_review.json'
reviewed=review.exists() and json.loads(review.read_text())['status']=='passed'
lines=['# Conservative robust motion v120: accepted TRAIN development model','',
    'New user request on11October2026 authorized renewed model development afterv119.',
    'Selected fixed global gain0.075 of frozen delta3 robust corrections. No maneuver',
    'labels or optical values enter motion inference. This is a verified improving',
    'TRAIN development model in the frozen v52 family, not a demonstrated replacement',
    'for retained v34 on its separate validation evaluation.', '',
    '| Gain | Equal-person ATE mm | Heading RMSE deg | ST change | Eligible |',
    '| --- | ---: | ---: | ---: | --- |']
for c in run['candidates']:
    lines.append(f"| {c['gain']:g} | {1000*c['equal_participant_mean_position_rmse_m']:.6f} | {c['equal_participant_mean_heading_rmse_deg']:.6f} | {100*(c['maneuver_ratios']['ST']-1):+.3f}% | {c['eligible']} |")
lines+=['','## Selected model by maneuver','', '| Maneuver | Baseline ATE mm | v120 ATE mm | Change |','| --- | ---: | ---: | ---: |']
tables={g:{r['condition']:float(r['equal_participant_mean_position_rmse_m'])*1000 for r in csv.DictReader((OUT/f'gain_{g:g}_maneuvers.csv').open(newline=''))} for g in (0,gain)}
for name in sorted(tables[0]):
    a,b=tables[0][name],tables[gain][name];lines.append(f'| {name} | {a:.6f} | {b:.6f} | {100*(b/a-1):+.3f}% |')
lines+=['','## How the model was obtained','',
    '1. Freeze v52 participant-fold wheel-speed calibration and offline projected-yaw',
    '   baseline, original clocks, optical initialization and scoring support.',
    '2. v119 fits existing causal hysteresis features to forward/yaw residuals using',
    '   shared robust weights, ridge1, eight IRLS updates and TRAIN-only normalization.',
    '   Delta3 had the lowest overall TRAIN score, but gain0.25 failed the ST guard.',
    '3. v120 preregistered only gains0.05/0.075/0.10; retained coefficients/features',
    '   and caps0.1m/s/0.05rad/s. Gain0.075 is the lowest-ATE eligible candidate.',
    '   Gain0.10 fails ST; there is no maneuver-specific selector or retuning.',
    '4. All207 recordings/12people/all15No20 remain present with exact same masks.',
    '   Every person and maneuver stays within5%; overall P95position, last-supported',
    '   endpoint and heading also pass. This is descriptive TRAIN development evidence.',
    '5. Export models/conservative_robust_v120 with exact three research-fold replicas.',
    f"   Sensor-only inference reproduces all{card['verified_recordings']} held motions; maximum difference{card['max_motion_error']:.3g}.",
    '', 'Call conservative_robust_inference_v120.load_fold and predict_motion; bundle',
    'README/model_card document inputs and scope. It is not a full-data deployment',
    'refit, and selecting/averaging fold models for a new user has not been evaluated.',
    '', 'Independent review: '+('passed; see research_state/v120_review.json.' if reviewed else 'pending final audit.'),
    'No new validation/test scoring, deployment, commit or push. Retained historical',
    'v34 remains100.702119399mmATE/49.726226563mmroute on71 exposed validation trials.',
    'The all207 independent-clock gate remains unresolved; inherited calibration,',
    'crop and offline filter dependencies remain. No significance/superiority claim.',
    '', 'Next: further development is authorized by the latest user request; do not',
    'repeat completed v119/v120 grids. Preserve the selected model and exact guards.',
    'A validation comparison or full-data deployment milestone requires an explicit',
    'evaluation decision consistent with prior no-validation/no-promotion scope.']
report='\n'.join(lines)+'\n'
(ROOT/'research_docs/conservative_robust_results_v120.md').write_text(report,encoding='utf-8')
readme=ROOT/'README.md';previous=readme.read_text(encoding='utf-8').split('\n\n# Conservative robust motion v120:',1)[0]
readme.write_text(previous+'\n\n'+report,encoding='utf-8')
checkpoint='''# Current checkpoint — accepted TRAIN model v120

User renewed development authority afterv119: “create the new best model”.
v120 evaluated exactly gains.05/.075/.10 on frozen delta3 robust fits, no new fit.
Selected.075:147.746508->146.296429mm equal-person TRAIN ATE; six maneuvers improve,
ST+4.1275%, every person/maneuver/tail/heading/support guard passes. All207 retained.
Bundle models/conservative_robust_v120 with sensor-only inference reproduces all207
held motions within1e-12. Exact research-fold replicas, not a full-data refit.
Read research_docs/conservative_robust_results_v120.md for complete methodology.
No validation/test/promotion/commit/push. v34 historical validation best unchanged.
Further development authorized; do not repeat v119/v120 grids or fabricate a
comparison between TRAIN and v34 validation. No live job after bundle verification.
'''+('Independent final review passed.\n' if reviewed else 'Independent final review pending.\n')+'\n---\n'
for name in ('NEXT_SESSION','STATUS','TODO','BEST_RESULTS','EXPERIMENTS','FAILED_IDEAS'):
    path=ROOT/f'research_state/{name}.md';previous=path.read_text(encoding='utf-8')
    if previous.startswith('# Current checkpoint — accepted TRAIN model v120'):
        previous=previous.split('\n---\n',1)[1]
    path.write_text(checkpoint+previous,encoding='utf-8')
path=ROOT/'research_state/LAST_SCHEDULE_CHECK.json';state=json.loads(path.read_text())
state.update(action='v120 accepted TRAIN model packaged; review '+('passed' if reviewed else 'pending'),active_research_jobs=0,
    next_work='Preserve accepted v120; no repeated grids; further TRAIN development authorized; validation/deployment not inferred')
path.write_text(json.dumps(state,indent=2)+'\n')
