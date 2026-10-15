# Current best — v121 validation retained after rejecting v125

15 October 2026 frozen comparison v126: v12199.30373516586415mm remains best
completed guard-passing validation. V12599.70035227471696mm is rejected for
OS/v121 ratio1.0527649671060733 and higher mean; all4 participants worsen.
V34100.7021193993738mm is the historical control. Same71/4people/105821frames.
All142 controls reproduced; v125 scored once; independent review PASS for all
213 paired predictions/core masks/guards and2556 grouped rows/denominators.
Retained models/reservoir_path_v121_completed/model.json SHA256
6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b.

Best accepted matched TRAIN remains v125127.53162704843507mm on207/12people/
15No20/314498frames, but its validation rejection prevents replacement of v121.
Descriptive validation benefit[-.607679,-.252149]mm,0/4improve,exact2/16=.125;
no independent significance/generalization claim. No refit, retuning or test use.
README leads with retained validation model and full progression. See
frozen_validation_results_v126.md /frozen_validation_review_v126.md.

---

# Historical best — v125 TRAIN, v121 completed validation

15 October 2026: v125 speed prior1/yaw prior10 is the accepted matched TRAIN best:
127.53162704843507mm vs v124128.87285434811182, v121129.73981099429272 and
v34132.24020010362922mm. Same207/12people/15No20/314498frames. All original
guards pass against all three controls;11/12 people and5/7 maneuvers improve
vs v124. Worst person vs v124 No4+.544726%; worst maneuver PS+2.038908%.
No8/v34 ratio1.049294920 remains close to1.05. P95/last-supportedendpoint/heading
ratios vs v124 .992965326/.975484316/.999217493. Both other configs rejected.

Frozen model models/axis_prior_v125, SHA256
7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2.
All207 actual-loader inference reproductions exact0 and all optical/identity
poisoning checks pass. Both independent reviews PASS. Descriptive bootstrap95
benefit[.476606539,2.312106231]mm; exact26/4096; conditional post-selection TRAIN.
LOO mean1.036014..1.514637mm. No independent significance/generalization claim.

Best completed exposed validation remains v12199.303735166mm vs v34100.702119399mm.
No new v124/v125 validation/test result. See axis_prior_results_v125.md,
axis_prior_review_v125.md and next frozen_validation_decision_v125.md.

---

# Historical best — v124 TRAIN, v121 completed validation

15 October 2026: v124 penalty10 is the accepted matched TRAIN best:
128.87285434811182mm vs v121129.73981099429272mm and v34132.24020010362922mm.
Same207/12people/15No20/314498frames; all guards against both controls pass.
Six/seven maneuvers and8/12people improve vs v121. No.8 vs v34+4.956036%
is close to5%; worst maneuver PS+0.554636% vs v121. P95/last-supportedendpoint/
heading ratios vs v121 .994376765/.989726191/.993528568. Independent reviews PASS.
Frozen full207 model models/trial_rmse_v124, SHA256
ac46f8b82096214da181624f7be0362ddc8494f1b44fa4827c68f01d41421ce7.
All207 inference reproductions exact0 and all optical/identity poisoning pass.
Descriptive bootstrap95 benefit[-.126796,1.940807]mm; no significance claim.

Best completed exposed validation remains v12199.303735166mm vs v34100.702119399mm.
No v124 validation/test score. See trial_rmse_results_v124.md and
trial_rmse_review_v124.md; separate next decision frozen_validation_decision_v124.md.

---

# Historical best while v124 develops — 15 October 2026

Accepted v121:129.739810994mm matched TRAIN;99.303735166mm exposed development
validation. New direct request authorizes v124 TRAIN-only improvement screen;
no new result claimed before execution/review. Exact frozen controls and guards
required. See research_docs/trial_rmse_v124.md.

---

# Current checkpoint — v123 frozen validation passed and independently reviewed

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

# Current checkpoint — v122 independent review complete; validation decision ready

13 October 2026: completed the outstanding independent read-only v122 review.
All five input hashes, source/output seals, 12 unique paired participants,
207 recordings/all15 No20 and independently reconstructed statistics pass.
Mean benefit2.500389mm;9/12 improve; omission range1.538987..3.111803mm;
bootstrap95[-.068061,5.368020]mm; exact486/4096 sign flips. Conditional
post-selection TRAIN only. See research_state/v122_independent_review.json.
No new fit, prediction evaluation, validation/test access or model change.

Best accepted matched TRAIN remains v121129.739811mm versus v34132.240200mm;
historical retained validation v34100.702119399mm is a separate scope.
README methodology and stale v112-v114 review/usage wording corrected.
Concrete next decision: research_docs/frozen_validation_decision_v121.md,
one frozen71-record matched comparison; candidate hash, exact support,
baseline reproduction and all guards specified. Evaluation-only runner is
not yet implemented; do that after explicit validation authorization.
Generic automation continuation does not authorize this gate. No retuning,
reservedtest, promotion, commit or push. No new architecture search justified.
No STOP or live Python/ACTIVE_RUN at entry. Existing dirty files preserved.
Do not repeat v121 fitting/package/inventory, v122 resampling or its now-complete
independent review. Continue when explicit validation authority or new linked
independent timing/provenance evidence arrives. Campaign remains incomplete.
Earlier checkpoints below are historical, not current pending work.

---
# Current checkpoint — v121 complete; v122 stability audit complete

12 October 2026: recovered stale handoff; v121 screen and package had already
completed with saved independent reviews. Did not refit or repeat predictions.
Ran preregistered v122 on sealed summaries and generated missing v121 report.
v121 accepted matched TRAIN ATE132.240200->129.739811mm; all207/12people/15No20,
all original guards pass. Full-TRAIN model models/reservoir_path_v121_completed
is frozen; exact207 inference reproduction was already complete, not held-out accuracy.
v122:9/12people improve; leave-one-out benefit1.538987..3.111803mm;
bootstrap95[-.068061,5.368020]mm; exact sign-flip fraction.118652344.
Conditional post-selection TRAIN evidence only; root reconstruction is not an
independent review. See research_state/v122_verification.json and
research_docs/reservoir_stability_results_v122.md. README now leads with best
TRAIN methodology and preserves historical v34 validation100.702119399mm.

Next justified accuracy task: one frozen matched validation comparison after
explicit authorization under the saved v121 protocol; do not infer validation
permission from generic continuation. No retuning/reservedtest/promotion/push.
No new architecture search justified by this descriptive audit. Do not repeat
v121 fits, packaging, inventory or v122 resampling. Independent clock/provenance
and independent-final-data gates remain unresolved. No active numerical job.
Prior checkpoints below are historical. Campaign not declared complete.

---
# Current checkpoint â€” v121 stronger model complete

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
# Current checkpoint — accepted TRAIN model v120

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
Independent final review passed.

---
# Authorized TRAIN-only robust motion screen v119

User authorized one additional family/max3 configurations. Guarded run completed
all207 TRAIN recordings/12participants/all15 No20, three participant folds.
All207 frozen v52 baseline scores/counts reproduced before candidate scoring.
No new validation/test evaluation, promotion, commit or push.

| Delta | Equal-person XY ATE (mm) | Heading RMSE (deg) | Worst person ratio | Worst maneuver ratio | Eligible |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 147.746508 | 1.836665 | 1.000000 | 1.000000 | True |
| 1.5 | 144.230173 | 1.822717 | 1.001187 | 1.126090 | False |
| 3 | 143.926074 | 1.822725 | 1.003298 | 1.148412 | False |
| 6 | 144.063281 | 1.826479 | 1.004674 | 1.180894 | False |


See research_docs/joint_robust_motion_results_v119.md.
Independent final review passed: all207x4 supports/guard metrics, fit exclusions,
source/output hashes and eligibility verified. All3 candidates rejected by ST guard.
Extra numerical budget exhausted; no new family/configuration/validation/promotion
authorized. No live job. Earlier awaiting-approval/running checkpoints are historical.

---
# Current checkpoint — 11 October 2026, authorized v119 running

User approved the bounded TRAIN-only branch. One family/three preregistered
deltas1.5/3/6 now executes under research_docs/joint_robust_motion_v119.md.
All207 baseline trial scores/counts reproduced before candidate scoring.
Guarded writer owns ACTIVE_RUN; no duplicate jobs. Outputs save each held trial
and checkpoint each fold. No new validation/test, promotion/commit/push.
Independent final review pending. Earlier awaiting-approval instructions below
are historical; the numerical budget remains one family/max3 configurations.

# Historical checkpoint — 11 October 2026, v117-v118 timing metadata complete

Heartbeat entry: native Goal absent; ordinary usage allowed; no STOP C/D and no
active Python/training jobs/ACTIVE_RUN. No Goal create/reset/resume/complete.
Two new guarded audits exit0 and independent reviews pass. This supersedes the
v115-v116 checkpoint for next action; all prior outputs remain immutable.

v117 checked header/parameter metadata in eight rejected TRAIN C3Ds:18blankzero
header event slots each, no named sync/event parameter group,12force/moment
analog channels, creation/crop metadata. Parser loads arrays but no sample analysis.
Header firstframe0 versus cropstart1 is index convention, not an IMU clock shift.
First Header serialization failure preserved research_state/v117_header_attempt;
corrected wrapper conversion passes. v118 checked first timing CSV row only per
sameeight TRAIN files: deviceus/PCmonotonicns/session fields; no verified shared
wall epoch/event linkage. Zero independent mappings established, not proof none
exists elsewhere; unlabeled analog pulses untested. All source/input/output hashes
reviewed. No clock acceptance, fitting, waveform/validation/test analysis or push.

Read research_docs/reference_timing_results_v117_v118.md. Retained v34 remains
100.702119399mmATE/49.726226563mmroute; README methodology/results updated.
v112-v116 independent reviews previously passed. Broad per-maneuver minima are
retrospective mixed-support reports; same-support selector gain only0.198992mm.

Actual remaining gate: current contract forbids new predictor/comparator fits
before all207 clocks/provenance pass; fixedreference constraints bound IMU-only
recovery201/207. New metadata route did not unlock it; do not repeat feature/peak/
firmware/journal searches or infer epochs from creation strings. Existing firmware
journal/Info searches already found no linked evidence; preserve those conclusions.

Concrete exception saved for user review ONLY:
research_docs/proposed_train_only_exception_2026-10-11.md. It proposes one extra
family/max3preregistered configs, all207TRAIN, frozen inherited clocks/support,
TRAIN folds only/no new validation/test scoring, no promotion/push, final review.
Do NOT fit under this exception until explicit user approval. If approved, first
preregister a distinct nonduplicate hypothesis and exact checks before execution.
Otherwise continue only if new independent linked timing evidence becomes available.
Campaign unfinished; HEAD87b85e6/preexisting dirty files preserved. No live job.

---
Earlier checkpoints are historical evidence, not current ownership.
# Current checkpoint — 10 October 2026, v115-v116 reporting audits

This supersedes the earlier native usageLimited status below: get_goal now
returns null (no attached native Goal) and ordinaryUsageAllowed=true. No Goal
was created, reset, resumed or marked complete. No STOP in C/D, no active jobs
at entry; guarded v115/v116 completed exit0. Retained v34 and gates unchanged.

Independent review of v112 source, v113 reference bound and v114 aggregate
uncertainty completed without substantive defect; reviewer verified hashes,
source methods/equations, six blockers/upper201 and exact256resamples/16flips.

The user's explicit request for per-maneuver cherry-picked reporting was carried
forward. v115 uses only sealed v77 summaries for six common-native v42 models:
426rows/71IDs, fixed person/maneuver labels/frame counts. Retrospective maneuver
selector94.462747445mm vs fixed refit94.661739566mm: only0.198992121mm gain.
Independent review passed; AR margin0.0000701943mm is practically meaningless.
No deployed/trained selector or validation-based promotion. No raw/test reads.

v116 reproduces all seven broad minima from sealed trial tables with identical
71IDs/person/maneuver labels, while reporting different support counts. AR winner
whole-model142.175376mm, CR116.878910mm, OS233.620690mm (3trials/2people).
AR/CR equal counts cannot certify equal masks/clocks/poses; winner manifests
lack saved trajectory arrays. Do not regenerate them for retrospective selection.
v116 independent review passed:15input/twooutput hashes, IDs/scores/counts verified. Read matched_maneuver_results_v115.md
and maneuver_minima_results_v116.md. README and source requirement matrix updated.

Next: continue only work that addresses an
actual unresolved prerequisite. All207 strict clocks remain impossible under
IMU-only feature changes with current reference gates (upper201). Independent
existing timing evidence or explicit clock-contract revision is required for
new predictor/comparator fitting; no gate relaxation,199subsetfit or repeated
projection/peak/source-retrieval/quiet-bias/residual experiments. Unknown legacy
identity stays quarantined. Coupled turn/gap and acceleration/tilt opportunities
are hypotheses, not validated improvements. No commit/push; HEAD87b85e6 and
preexisting dirty sources/config/data preserved. Campaign is not complete.

---
Earlier checkpoints follow as historical evidence, not current job ownership.
# Scheduled checkpoint — v110–v114 complete; native Goal usageLimited

9 October2026,06:52Bangkok. Heartbeat arrived in this SAMEchat, no duplicatejob.
Native get_goal verified status usageLimited (tokensUsed1164483,no tokenbudget).
Do NOT claim resumed, reset allowance, repeatedly retry, purchase usage, or mark
complete/blocked/paused. Native controls must permit continuation; scheduler
cannot perform a user-controlled Goal resume. Campaign remains unachieved.
STOP absent C/D, no livePython/training process or ACTIVE_RUN. LAST_RUNv114
complete/exit0. No new source/model/experiment after this limit check; checkpoint
only. Previous goal turn changed research evidence/state (progress), no wait.

Completed v110primary2023singlewheelPDF11pages/rendered3–7;v11181ideal cases
figure recovery2.22e-16,9undefined printedratio/48disagreements underour explicit
interpretation, not authorcodebug. SI/gpathsagree; idealcamber approximation
not empiricalerror. Independentreviewer verified allhashes/methodpages/arithmetic.
FailedJSONint64attempt preserved, correctedguardexit0.
v112primary2022sensorreductionPDF7pagesinclcover/rendered4/5/7: opticalvelocity
metrics, distinctgap/SVD/reference/selection, AppendixAunits/geometry unresolved.
No faithfulcomparator or local prediction. See sensor_reduction_source_v112.md.
v113sealedmetadata logicalbound:6reference-gate blockers, permissiveupper201/207
for ANYIMU-only change underfrozenrefmotion/peaks. This is not physicaltiming
unobservability. Stop additionalIMU-only clockfeature attempts; no gate relaxation.
v114ONLYsealedv34participantaggregateCSV/runreads, no raw/predictions/test.
Fourpeople/71exposedvalidation, pairedbenefit1.883060004mm/1.835606288%;256exact
pairedresamples interval[-.104118611,4.379743550]mm;16signflipsp=.375conditional.
No.10worsens, omitNo.14benefit.584452522mm. No significance/SOTA/promotionclaim.
Independentreview requestv112/v113/v114 failed workspaceoutofcredits; pending,
not completed. Rootanalytic checks/hash checks pass, do not relabelself-review.

Read research_docs/final_same_data_comparison.md and
retained_uncertainty_results_v114.md, rotation_source_results_v110_v111.md,
reference_clock_bound_v113.md. READMEbestmethodology/limits updatedthroughv114.
Retainedv34100.702119399mmATE/49.726226563mmroute unchanged. v108/v109independent
reviewcomplete:199/207unchanged;baseline12unsupported vsprojected33,new21/restore0.
No13historical4.8517is DELTA from-.7000to+4.1517;v108+4.1566sameconvention.
Completedoutputs immutable, do notrerun. No raw/split/test edits/commit/push.
HEAD87b85e6/preexistingdirtyfiles preserved; exactdeployment/physicalfront/
legacy/referenceuncertainty and strictclock gates unresolved.

Exact next permitted action: after nativeallowance/resume permits, read this
handoff/contract/checkSTOP/livejobs, independently reviewv112source,v113bound
andv114aggregate statistics withoutdata/modelselection. Then consolidate
requirement-level/source-to-local prerequisites for faircomparison, using
existingevidence. No repeated failedretrievals, firmwarehunts,peakcounts,
projection/gate searches, accepted199subsetfits or newarchitecture beforegates.

---
Earlier checkpoints (historical status, not current job ownership) follow.

## v108-v109 projected clock hypothesis rejected — 9 October 2026

207TRAIN/12people/15No20 preserved.199accepted/8same rejections/zero transitions;
all8rejection diagnostics unchanged. Independentv108 review verifies212hashes,
protocol/dependencies/parents/readscope. v109directprojection maxerror0counts.
Baseline12unsupported frozen scored frames vsprojection33:21new/0restored.
Medianabsoluteoffset delta.6ms/max77.7ms;3over25ms,1sourcechange. No refit,
clock promotion, XY/ATE/predictor, validation/test or push. JSONint64 failure
preserved/corrected; correctedguard exit0. Reviewer checkingv109finalevidence.
CORRECTION: v85No13value4.8517s is offset CHANGE from-.7000 to+4.1517,
not returnedlag. v108alias+4.1566 is+4.9ms vs v84 in same native convention.
Earlier notes calling4.8517offset are superseded; do not invent originchange.
Read research_docs/projected_clock_results_v108_v109.md. Bestv34unchanged.
Next: primarysource2023 single-wheel rotation method discovered in the source
search, exact mounting/gravity/metric prerequisites before any local adaptation.
No repeated projection/gate relaxation or accepted199subset fit.

## v106-v107 source audit reviewed — 9 October 2026

Two full mobility papers and MASSWU S1 sealed; independent read-only reviewer
verified all hashes/method pages. Neither supplies comparable midpoint XY ATE.
2023 requires participant quiet/straight calibration and before/after rigid-beam
sync. 2025 coefficients mix Pearson/Spearman/rater analyses; S1 lacks supplied
processing, timestamp transmission and frozen samples; angular units unresolved.
No build/data/predictions or faithful reproduction. Failure-count attempt saved.
See research_docs/mobility_source_results_v106_v107.md and comparison matrix.
Best v34 remains100.702119399mmATE/49.726226563mmroute; clocks199/207.
Next: preregister one existing full-record gravity-projection clock diagnostic
with fresh fold calibration and unchanged synchronization gates; no ATE selection,
new predictor family, reduced-support fit, promotion, validation/test or push.
Previous goal turn verified schedule/destination evidence (progress), no experiment.

## v103-v105 verified — 9 October 2026

Fuss source text-derived only;54idealcambercasespass,18zero-camberliteralEq6
undefined but yawnotgenerallyunobservable.423parenthash inputaudit retains
207TRAIN/15No20:429790sensorgridframes allvalid/207complete500msprefixes.
No quietprefixclaim/calibration/trajectory/accuracygain. Independentreview
verifiesv101/v104hashes and limits. Bestv34 unchanged; README updated.
Nextprimary2023/2025metric audit perNEXT_SESSION, noPMCchallengebypass.
See research_docs/wheel_source_results_v103_v105.md / wheel_inputs_v105.md.

## v100-v102 completed source checks — 9 October 2026

216synthetic camber cases pass(max2.22e-16),4curvaturecases andaffine endpoints.
Agent's initial radius-factor error falsified/preserved; no published typo.
OfficialWheel-INS is singlewheel;16Gitblob-verifiedsource/configfiles show
initialization/rate/mounting/gap portability limits. Independent reviewer agrees.
2026PDF rendered; WISDOMtextonly. No builds or recording/prediction/scoring.
Bestv34 unchanged; no promotion/push. Read NEXT_SESSION.md and
research_docs/wheel_source_results_v100_v101.md / wheel_implementation_v102.md.
Next Fuss2012fullmethod andexistinginputmapping;199/207gate unchanged.

## v97-v99 completed; v100 source audit active — 9 October 2026

Literal source-weight audit:600 undefined /153330 out-of-range among429583
eligible TRAIN207 resampled frames; all15No20 retained. Independent639hash
review and2analytic tests pass. Proxies have supervised fold bias/sign and
nominal geometry; no physical skid rate or faithful reproduction established.
No trajectory prediction/refit, val/test access, promotion or push. Retained
bestv34 unchanged100.702119399mmATE/49.726226563mmroute.
Next: WISDOM fusion/camber and2026 primary-method compatibility extraction;
see NEXT_SESSION.md and skid_source_domain_results_v97_v99.md.

## Completed v94-v96 continuation — 9 October 2026

Sealed clock profiles reveal158ms No13 yaw/speed tradeoff,159raw Pareto points,
zero supportloss at raw optima but only1yaw event; clocks remain199/207.
2898sealed TRAIN rows/14cells backfilled; no genuine endpoints, only207saved
motion rows. Missingv60/v63arrays explicit;v61variance-only notapplicable.
v96 verifies1352hashes/40794window scores/2898ATE; supplementary280summary rows/
828source masks/90unique complete window keys. No refit/promotion/val/test/push.
Bestv34100.702119399mmATE/49.726226563mmroute unchanged ondistinct71validation.
See research_docs/consistency_backfill_results_v94_v96.md and NEXT_SESSION.md.

## 9 October 2026 v91-v93 checkpoint
Retainedbest unchanged: **v34 100.702119399mmATE/49.726226563mmroute** on71previously
exposedvalidation. Latest boundedbasin/geometryrole diagnostics and9122scorechecks
produce no trajectorypredictions oraccuracyclaim; clocks199/207 preventrefit.
All207records/15No20/scoringsupport retained. See research_docs/basin_geometry_results_v91_v93.md.

## 8 October 2026 â€” competition plan and final numeric checkpoint
v62/v63/v64 finished; no expired sessions remain to poll. v62/v64 reject all speed candidates: ST regressions persist after removing center acceleration, dynamic gravity and nonlinear/direction-aware wheel features. v63 TRAIN-only derivative counterfactual suggests forward-motion opportunity but does not close 10x5 paths; absolute-heading diagnostic still missing. v65 inventories supplied historical two-IMU folder: 49 metadata recordings, 37 July wheelchair-marker C3Ds, 21 empty C3Ds, one static pair; no split changes. Unknown identities/semantic duplication block strict-track inclusion.
Latest user adopts bounded competition plan (eight new families, three prespecified configs), existing data only, no remote push. Parallel agents hit workspace credit limit. Numeric artifacts saved; retained result unchanged. See research_docs/competition_execution_checkpoint_2026-10-08.md and NEXT_SESSION.md for exact commands and next10 priorities.

# Best results - current checkpoint

9 October 2026 v86-v90: retainedbest remains **v34 100.702119399 mm ATE /
49.726226563 mm route** on71previously exposedvalidationtrials. No new
trajectorypredictions or eligibleimprovement:199/207freshclockcoverage and
unresolvedbasinboundaries preventrefit. Independent distributed/event/source
arithmetic checks pass; theseare diagnostics, notnewlocalizationmetrics.
README now records exact trainingselected0.75motionblend, worstfoldpersonratio
0.993947477 andv36/v77reproduction. TRAINv81native/new147.565311mm isadistinct
scope. No newvalidation/testaccess orcommit/push.

Oct8 resume: retained best unchanged while v58-v61 run. Existing v56 fully
refit TRAIN207 result216.033mm vs219.002physics, worst participant1.010555;
not a headline improvement and maneuver/route guard still under audit.
Superseding audit: v56 fails ST+32.76%, v58/v60also fail slopeguards. Keep
v52as TRAIN full-refit control147.746508mm; route60.521354/P95119.404180/
maxsupported-runFrechet257.007912/endpoint193.852803mm, heading1.836665deg.
Retained v34headline100.702119mm remains a different conditional validation scope.

| Candidate | Synchronized RMSE | Decision |
| --- | ---: | --- |
| Original v21 | 102.585179 mm | Reference benchmark |
| v34 tilt blend .75 | 100.702119 mm | Retained conditional development candidate |
| v38 naive corrected-clock refit | 96.329 mm own / 96.172 mm common | Reject: worst conditional training-person ratio1.559583 |
| v42 signal-arbitrated clock refit | 94.834759 mm own / 94.661740 mm common | Not promoted: No.8 ratio1.058004869 exceeds1.05 guard |

Comparisons across own-clock and common-native support are not interchangeable. Old v34 common-native comparator in v44 is100.592598mm.

v42 route diagnostics: symmetric RMSE46.124049mm, P9589.031705, sampled Hausdorff139.983334, max-run discreteFrechet155.161866, endpoint122.307880, absolute length113.305502, within-run arc85.805480. Old common-native route49.680804mm; absolute length105.713574mm. Smaller geometric mean coexists with worse length and participant regressions.

Evidence: outputs_clock_arbitrated_v42, outputs_clock_arbitrated_folds_v43, outputs_clock_arbitrated_loader_v44, outputs_clock_routes_v44. Retained v34 evidence: outputs_dynamic_blend_v34 and outputs_dynamic_loader_v36. All evaluation remains development/conditional; full calibration/base fold refit and fresh independent acquisition are outstanding. Test untouched.

## Later conditional results â€” do not replace headline
| Candidate | Result | Decision |
| --- | ---: | --- |
| v50 full-refit physics | 219.002 mm TRAIN folds | Selected baseline; alternatives fail robustness |
| v50 linear endpoint | 214.171 mm TRAIN folds | Reject: worst participant ratio 1.769287 |
| v52 projected-gravity yaw | 147.747 mm TRAIN folds | Passes guard (worst 0.961159), conditional simple-estimator result |
| v54 frozen v52 validation | 153.607 mm validation | All 4 participants improve vs same refit-physics baseline; no retuning; still worse than v34 |

v54 is useful mechanistic evidence, not a new best trajectory candidate. v55 is diagnostic rather than a candidate: No.18 PS2 405.191mm drops to60.344mm with observed speed only, while observed-yaw-only remains405.114mm, identifying a ~0.485m forward-travel deficit.
# 2026-10-08 acquisition verification note
v57 independently verifies all544accepted raw CSV hashes, sequence integrity and
device timing. No inputs rescaled or models retrained: retained v34 remains
100.702119mm conditional development. Firmware Info scale bug has zero effect
on this raw-count pipeline. Exact acquisition binary/range remains unproven.
