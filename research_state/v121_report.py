"""Report sealed strong-baseline challenger without new scoring."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'outputs_reservoir_path_v121'
run=json.loads((out/'run.json').read_text());selected=run['selected'];lam=selected['penalty']
bundle=ROOT/'models/reservoir_path_v121_completed'
verification=json.loads((bundle/'verification.json').read_text())
lines=['# v121: nonlinear temporal model beats the strongest retained TRAIN baseline','',
    'Frozen v34 matched TRAIN ATE132.240200mm ->129.739811mm (1.89% lower).',
    'All207 recordings/12people/all15No20 retained; every original guard passes.',
    'This is a measured improvement, not a claim of groundbreaking performance or',
    'universal superiority. No new validation/test evaluation has been performed.','',
    '| Penalty | Equal-person ATE mm | Heading RMSE deg | Worst person ratio | Eligible |',
    '| --- | ---: | ---: | ---: | --- |']
for c in run['candidates']:
    lines.append(f"| {c['penalty']:g} | {1000*c['equal_participant_mean_position_rmse_m']:.6f} | {c['equal_participant_mean_heading_rmse_deg']:.6f} | {max(c['participant_ratios'].values()):.6f} | {c['eligible']} |")
lines+=['','Penalty1 obtains127.490837mm but fails participant guards; it is rejected.',
    'Selected penalty10 worstperson+3.356%, worstmaneuver+0.264%; P95position',
    'ratio0.981494, last-supportedendpoint0.980206, heading0.981692.','',
    '| Maneuver | Matched v34 ATE mm | v121 ATE mm | Change |',
    '| --- | ---: | ---: | ---: |']
tables={v:{r['condition']:float(r['equal_participant_mean_position_rmse_m'])*1000 for r in csv.DictReader((out/f'lambda_{v:g}_maneuvers.csv').open(newline=''))} for v in (0,lam)}
for name in sorted(tables[0]):
    a,b=tables[0][name],tables[lam][name];lines.append(f'| {name} | {a:.6f} | {b:.6f} | {100*(b/a-1):+.3f}% |')
lines+=['','## Method and route to this result','',
    'v119/v120 improved a weaker physics baseline. The new comparison directly',
    'reproduces the retained v34 weight0.75 model, all207 exact historical scores',
    'and support counts before scoring candidates. Frozen parent models preserve',
    'their inherited266 additional training-record dependence; new residual fitting',
    'uses only identified TRAIN people, excluding each held participant fold.',
    '', 'A fixed16-state leaky tanh recurrent reservoir encodes central gravity-rotation',
    'IMU features, with fit-only normalization and seeded fixed recurrent weights.',
    'A joint forward/yaw readout is optimized against exact accumulated XY/heading',
    'trajectory error. Eight analytic GaussNewton steps with fitting-only line search',
    'replace short-interval/derivative-only objectives. Caps.05m/s and.02rad/s,',
    'three preregistered ridge penalties.1/1/10; no maneuver labels or identity at',
    'inference. Optical labels are used only for fitting and evaluation.',
    '', 'Independent reviewer checked all34 Jacobian columns (maxerror9.04e-10),',
    'all207x4 trajectory support/core metrics, fitting exclusions and hashes. All',
    'candidate predictions and perperson/maneuver results are preserved. See',
    'research_state/v121_review.json and v121_preparation_notes.md for audit and',
    'the two preserved pre-fit path/manifest lookup failures.',
    '', '## Actual model artifact','',
    'models/reservoir_path_v121_completed contains the full-TRAIN readout fit at selected',
    'penalty10 on all207 identified records, with the frozen full v34 parent.',
    'Use reservoir_inference_v121.load_reservoir_model()(sensor). Startup IMU',
    'initialization is supplied or computed from original startup history; an',
    'optical initial pose is supplied separately only for integration.',
    f"Full TRAIN inference reproduction: {verification['recordings']} recordings; maximum motion difference{verification['maximum_motion_difference']:.3g}.",
    'Optical/identity-field poisoning leaves inference unchanged. These package',
    'reproduction checks are not held-out accuracy measurements.',
    '', '## Package completion and provenance repair','',
    'The first package attempt saved the full-TRAIN coefficients, then stopped at',
    'a strict legacy pipeline hash check. Only sensor metadata and report prose',
    'had changed; numerical pipeline functions were unchanged. The incomplete',
    'models/reservoir_path_v121 bundle and original source copies remain preserved.',
    'Completion reused its coefficients and normalization without another fit.',
    'Two exact reviewed provenance transitions allow the corrected pipeline and',
    'the verification-only ridge loader edit. Other hashes still fail closed;',
    'historical manifests were not rewritten. New dependencies are sealed.',
    'All207 sensor-only predictions and per-record optical/identity poisoning',
    'checks pass. See research_state/v121_package_review.json for package review.',
    '', '## Comparison scope and next evaluation','',
    'Recorded inventory:125 complete207-ID historical candidate groups,116 with',
    'v34 frame counts. New selected score is below their recorded means, including',
    'rejected v33tilt0.3 at131.460088mm. Exact paired baseline support is verified',
    'for v34; equal counts alone do not prove every historical mask/time mapping.',
    'See research_state/v121_comparator_inventory.json for all paths/hashes/groups.',
    '', 'v34 historical validation remains100.702119399mm on71 exposed recordings.',
    'Do not compare that directly to129.739811 TRAIN. Candidate is frozen and ready',
    'for one explicitly authorized matched validation comparison, with no retuning',
    'or reserved-test use. No promotion/commit/push occurred. Independent clocks',
    'remain unresolved; offline/future-context/crop/calibration inheritance persists.']
report='\n'.join(lines)+'\n';(ROOT/'research_docs/reservoir_path_results_v121.md').write_text(report,encoding='utf-8')
path=ROOT/'README.md';previous=path.read_text(encoding='utf-8').split('\n\n# v121: nonlinear temporal model',1)[0];path.write_text(previous+'\n\n'+report,encoding='utf-8')
checkpoint='''# Current checkpoint â€” v121 stronger model complete

User requested a model beating all attempted models. v121 improves the strong
frozen v34 matched TRAIN baseline132.240200->129.739811mm, all207/12people/15No20.
Penalty10 passes every person/maneuver/tail/heading/support guard; penalty1's
127.490837mm fails participant guards and is rejected. Exact baseline reproduction
and independent screen review passed. Full-TRAIN candidate model sealed at
models/reservoir_path_v121_completed; callable reservoir_inference_v121.load_reservoir_model.
All207 full-TRAIN inference reproductions pass; do not call these held-out scores.
README and research_docs/reservoir_path_results_v121.md document methodology.
Inventory125 prior groups supports lower TRAIN mean in bounded inventory, not
universal superiority. Historical validation v34100.702119399mm not comparable.
Ready for one frozen matched71-record validation comparison once explicitly
authorized; no reservedtest/retuning/promotion/commit/push. No live job after fit.
Earlier running/exhausted-budget checkpoints are historical. Preserve artifacts.

---
'''
for name in ('NEXT_SESSION','STATUS','TODO','BEST_RESULTS','EXPERIMENTS','FAILED_IDEAS'):
    path=ROOT/f'research_state/{name}.md';previous=path.read_text(encoding='utf-8')
    if previous.startswith('# Current checkpoint â€” v121 stronger model complete'):previous=previous.split('\n---\n',1)[1]
    path.write_text(checkpoint+previous,encoding='utf-8')
