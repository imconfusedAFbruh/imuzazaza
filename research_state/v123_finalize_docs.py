"""Consolidate verified v123 outcome into living docs without editing sealed data."""
import datetime
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
run=json.loads((ROOT/'outputs_frozen_validation_v123_exact/run.json').read_text())
review=json.loads((ROOT/'research_state/v123_independent_review.json').read_text())
assert run['decision']['eligible'] and review['passed'] and review['distinct_records']==71
now=datetime.datetime.now(datetime.timezone.utc).isoformat()

section='''## Latest result and research methodology

**Frozen v121 passes matched validation: 99.303735 mm equal-person XY ATE versus v34 at 100.702119 mm**, a 1.398384 mm (1.39%) improvement across the same 71 exposed validation recordings, four participants and 105,821 scored frames. All predeclared guards pass. This is the new guard-passing validation candidate; deployment promotion is not included. See the [full comparison and methodology](research_docs/frozen_validation_results_v123.md).

| Matched validation metric | v34 | Frozen v121 |
| --- | ---: | ---: |
| XY ATE RMSE, mm | 100.702119 | 99.303735 |
| Position P95, mm | 159.335255 | 156.125865 |
| Last-supported endpoint error, mm | 127.772313 | 124.258881 |
| Heading RMSE, degrees | 1.260899 | 1.203765 |
| Geometric route RMSE, mm | 49.726227 | 48.715699 |

Each figure averages participant means of trial metrics. Last-supported endpoint error is not genuine acquisition endpoint error. Three of four participants improve; No.5 worsens 0.434%. PS and SL worsen 0.494% and 1.273%, respectively. All remain below the frozen 5% regression limit; the favorable mean does not mean every recording improves.

We obtained this result by first reproducing the strong v34 baseline, then adding a fixed 16-state temporal reservoir over gravity-rotation IMU features. The bounded forward-speed/yaw readout was fitted against exact integrated trajectory error in three participant folds. Of three preregistered penalties (0.1, 1, 10), penalty 10 passed every guard; penalty 1's lower TRAIN mean was rejected for participant regressions. Accepted matched TRAIN ATE was 129.739811 mm versus v34 at 132.240200 mm on all 207 recordings/12 participants. The selected readout was subsequently fitted on all 207 TRAIN records and frozen. See the [training method and results](research_docs/reservoir_path_results_v121.md).

The v122 stability audit found improvement for 9/12 TRAIN participants and a positive mean benefit after omitting any one participant. Its descriptive bootstrap interval includes zero (-0.068 to 5.368 mm), so it does not establish independent significance. The TRAIN-fold score, full-TRAIN package reproduction, and new validation score are distinct evidence. See the [stability audit](research_docs/reservoir_stability_results_v122.md).

On 14 October 2026, after explicit authorization, the evaluation-only v123 runner reproduced all 71 historical v34 motions, trajectories, headings and exact reference/support arrays before scoring v121 once. It retained the original clocks, crops, IMU startup initialization, single optical initial pose and all metrics. Prediction received only sensor/setup/IMU initialization. One baseline numerical discrepancy was traced to using two CPU threads; restoring the original four-thread producer setting gave exact reproduction without loosening any tolerance. Both earlier implementation failures are preserved and evaluated zero candidate records.

Acceptance required lower equal-person ATE, no participant or maneuver ATE regression above 5%, and no more than 5% regression in equal-person position P95, last-supported endpoint or heading error. Exact recording/frame support was mandatory. Six synthetic contract tests passed. Independent review verified 153 output hashes, 429 input hashes, exact v34 reproduction, all 71 paired supports, core metric arithmetic and every guard. Supplementary route/RTE values use the unchanged v74 evaluator; they were not independently recalculated in that core review. See [independent verification](research_state/v123_independent_review.json).

The unchanged model is `models/reservoir_path_v121_completed`, loaded with `reservoir_inference_v121.load_reservoir_model`; SHA256 of model.json is `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`. Paired predictions and full trial tables are sealed in `outputs_frozen_validation_v123_exact`. Supplementary overall/participant/maneuver tables, with explicit availability denominators, are in `outputs_frozen_validation_v123_report/grouped_metrics.csv`.

This is previously exposed development validation, not a new blind test or proof of superiority to published methods. Frozen parent models retain an inherited dependence on 266 additional training records. Offline future context, optical-dependent crops, calibration inheritance and unresolved independent clocks/firmware provenance limit interpretation. No refitting or retuning followed validation, no reserved-test data was evaluated, and no deployment promotion, commit or push occurred. The authorized comparison is complete; independent final data and provenance evidence remain needed for stronger claims.

'''
path=ROOT/'README.md';text=path.read_text(encoding='utf-8-sig')
start=text.index('## Latest retained result and research methodology')
end=text.index('### Earlier research and retained validation methodology',start)
text=text[:start]+section+text[end:]
text=text.replace('### Earlier research and retained validation methodology',
    '### Historical research and v34 validation methodology\n\nThe following chronological notes describe earlier checkpoints. Any pending-validation or best-model statement below is superseded by the completed v123 comparison above.')
text=text.replace('The latest report is `output/pdf/trajectory_research_accuracy_audit.pdf`.',
    'The latest numerical comparison is `research_docs/frozen_validation_results_v123.md`; the earlier trajectory PDF is `output/pdf/trajectory_research_accuracy_audit.pdf`.')
path.write_text(text,encoding='utf-8')

checkpoint='''# Current checkpoint — v123 frozen validation passed and independently reviewed

14 October 2026: explicit user authorization consumed for one frozen v121/v34
comparison. Evaluation-only runner completed exit0 at outputs_frozen_validation_v123_exact.
All71 baseline motions/XY/headings/reference arrays/support reproduce v34 exactly.
Candidate evaluated once: equal-person ATE100.702119399->99.303735166mm (-1.388634%).
All71/fourpeople/105821 scoredframes retained. All guards pass. No.5+0.4341%,
PS+0.4941%, SL+1.2726%; P95/last-supportedendpoint/heading ratios .979858/.972502/.954688.
Independent reviewer verified153output/429input hashes, all paired supports,
core metrics and guard arithmetic. See research_state/v123_independent_review.json.

Frozen full-TRAIN model unchanged at models/reservoir_path_v121_completed;
model SHA6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b.
TRAIN result129.739811mm remains a separate scope. No new fit, retune, alternate
candidate, reserved-test access, deployment promotion, commit or push.
README now documents the complete training-selection/freezing/validation route;
full report research_docs/frozen_validation_results_v123.md. Supplementary metric
tables and explicit availability denominators in outputs_frozen_validation_v123_report.

Failed attempts outputs_frozen_validation_v123 (virtual-source path) and
outputs_frozen_validation_v123_completed (baseline CPU thread discrepancy)
remain preserved. Both candidate_count0. Original v33 four-thread restoration
gave exact baseline reproduction; no tolerance changed. Source snapshots and
diagnosis in research_state/v123_preflight_failure and v123_baseline_failure.

This authorized milestone is complete; do not repeat validation or tune from it.
The broader campaign remains incomplete: exposed development validation is not
independent final evidence. Next accuracy work needs a separately authorized
protocol and/or new independently linked timing/firmware/final-acquisition evidence.
No numerical task is active. Earlier pending-authorization checkpoints are historical.

---

'''
for name in ('NEXT_SESSION.md','STATUS.md','TODO.md','BEST_RESULTS.md','EXPERIMENTS.md','FAILED_IDEAS.md'):
    path=ROOT/'research_state'/name
    path.write_text(checkpoint+path.read_text(encoding='utf-8-sig'),encoding='utf-8')

path=ROOT/'research_docs/final_same_data_comparison.md'
text=path.read_text(encoding='utf-8-sig')
intro='''## 14 October 2026 — frozen v121 matched validation update

The authorized v123 comparison and independent review are complete: v121 improves
equal-person ATE100.702119399->99.303735166mm on the same71 exposed validation
records/fourpeople, with every guard passing and105821 matched scoredframes.
Baseline motion/trajectories/headings/reference/support reproduce exactly.
Route RMSE49.726226563->48.715699mm. No.5/PS/SL worsen slightly within5% limits.
No refit, retuning, reserved-test evaluation, deployment promotion, commit or push.
See frozen_validation_results_v123.md and ../research_state/v123_independent_review.json.
This supersedes earlier pending-validation and best-candidate status below,
without changing historical results or establishing an external-comparator victory.

'''
first,rest=text.split('\n',1);path.write_text(first+'\n\n'+intro+rest,encoding='utf-8')

report=f'''# Frozen v121 validation completed and independently verified

Run time: {now}
User authorization: "Authorize the frozen v121 validation comparison".

Implemented frozen_validation_v123.py and six synthetic support/guard tests.
Preserved two pre-candidate failures; traced CPU arithmetic discrepancy to two
versus original four Torch threads. Restored original producer setting without
changing tolerances. Final guarded run completed exit0 with no active owner.

All71 v34 baselines reproduce exactly before candidate scoring. Frozen v121
evaluated once:100.702119399->99.303735166mmATE,1.388634% improvement, all guards
pass,105821 matched frames. Independent review verifies153output/429input hashes
and all core arithmetic/support/guards. No new fit/retune/reserved-test/promotion.

Generated full results/methodology,1704 supplementary grouped metric rows with
availability denominators, updated README and six state summaries. Preserved
all model/data artifacts and existing dirty/untracked work; no commit or push.

Authorized comparison complete. Broader campaign remains incomplete; independent
timing/provenance and new final data are unresolved. No additional model selection
or validation rerun justified by this result. See frozen_validation_results_v123.md.
'''
(ROOT/'research_state/LAST_RUN_REPORT.md').write_text(report,encoding='utf-8')
memory=Path('C:/Users/poon1/.codex/automations/continue-create-the-best-model-yet-i-trust-you-astra/memory.md')
with memory.open('a',encoding='utf-8') as f:f.write('\n'+report)
print(now)
