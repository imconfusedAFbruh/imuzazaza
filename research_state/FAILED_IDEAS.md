# v126: v125 rejected on frozen validation — 15 October 2026

The stronger TRAIN result did not beat the retained model on the71-record
development-validation comparison. V125 ATE99.70035227471696mm versus
v12199.30373516586415mm (+.396617109mm /+.399398%). All four participants
worsen versus v121 (+.293174% to+.545403%). OS/v121 ratio1.0527649671060733
fails the unchanged5% maneuver guard; the mean-lower requirement also fails.
V125 passes against historicalv34, which does not override the stronger control.
Retain frozenv121. Do not promote v125 using its TRAIN127.531627048mm score,
better routeRMSE48.612489mm, or10sRTE68.685769mm (only4records/twopeople).

No refit, retuning, second candidate or test use occurred. Do not tune the speed
penalty, target OS, choose exclusions, alter clocks or assemble maneuver-specific
winners from these outcomes. The single frozen comparison is consumed; preserve
all71/105821frames and original guards. Further inference/scoring is not needed
to document this result. Independent review and README/state closure follow.

---

# Historical v125 rejected alternatives and remaining limits — 15 October 2026

Separating speed/yaw regularization works only in the tested stronger-yaw setting.
Speed10/yaw1 ATE128.156224431mm is rejected despite its lower mean than v124:
No6 ratios1.072868653(v34),1.079589249(v121),1.074681047(v124); No8/v34
1.058988709. Symmetric3/3 ATE127.563048188mm is rejected for No8/v34
1.054332801. Do not select these attractive averages, relax the5% guards or
retune them using validation. Fixed speed1/yaw10 127.531627048mm passes all guards.

The accepted model improves11/12 people versus v124, but No4 worsens.544726%,
PS2.038908%, ST.147215%. No8/v34 still+4.929492%, very close to5%.
Bootstrap95 benefit[.476606539,2.312106231]mm and26/4096 exact signs remain
conditional post-selection TRAIN evidence, without independent significance or
generalization. No new v124/v125 validation result. All outcomes retained;
screen/package/reviews complete and must not be repeated without a new reason.

---

# Historical v124 rejected readouts — 15 October 2026

The trial-RMSE/prior hypothesis produced an eligible penalty10 improvement,
but lower regularization does not provide a guard-passing win. Lambda1 ATE
126.775357782mm fails No.6 (+7.719603% vs v121; +7.049033% vs v34), plus
No.8+5.913610% vs v34. Lambda.1 ATE129.250414691mm fails several people,
10x5(+14.709357% vs v121) and heading(+7.926655% vs v121). Both rejected.
Do not select their attractive aggregate or retune these penalties from validation.
Selected lambda10 ATE128.872854348mm passes both-control guards but No.8 vs v34
is already+4.956036%; preserve this narrow margin. 8/12 people improve vs v121,
bootstrap95 benefit[-.126796,1.940807]mm includes zero. Conditional TRAIN only.
All outcomes and independent reviews preserved; no repeat of the completed grid.

---

# Historical v124 hypothesis boundary — 15 October 2026

Completed v121-v123 work will not repeat. Direct user request authorizes a
distinct TRAIN loss/prior experiment: mean trial RMSE rather than squared path
error. .1/1/10 only; preserve original guards against both v34/v121. Record all
rejections; no validation-based tuning or relaxed timing claims.

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

## v94-v96 rejected conclusions / unavailable artifacts

Do not certify a single No13lag from two correlated channels: six yaw/four
informative speed windows disagree;159raw Pareto points/one yaw event unresolved.
Empty joint-gate support list does not prove raw optima lose support; both lose0.
Do not revive failed speed models from smallerATE: e.g.v64gain.5 142.051mm vs
control147.747mm but5sRTE108.079 vs99.627mm and frozen slope guard fails.
No motion-from-pose velocity backfill, guessed genuine endpoints, regeneration
of missing828v60/1656v63arrays, or unchangedv61trajectory as new candidate.
v95initial availability v63undercount corrected only in immutablev96supplement.
Checkpoint code/dependency limitations explicit; noblind incomplete-output resume.

## v86-v90: denser coarse bins alone cannot restore missing clocks

Of20investigatedchannels,10lacktwoexistingpeaks,4failmotiongate and2have
atmostonechronologicalmatch anywherewithin+/-5s at200mstolerance despite
twopeaks/list (No15AR3yaw/No7CR1yaw). All4eligibleevent-feasiblechannels already
havecandidates. Do notrepeatcoarsebinsearch torescuesevenemptycases orlower
gates fromtheirresults. This rulesout onlycurrentfeature/peak definitions,
not everyalternative clockmethod. Opticalfragmentation alone isinsufficient:
weakOSrecords havecontinuousreference support. No boundaries invented aspeaks.
Relativecontrast doesnot certifyclock: No7CR1loses101scoredframes andspeedcorr
.5215fails. No13freshbasin winsagainstaliasbutexactoffset hitsrefinementbound;
No19onewindow inconclusive. Ten/twelveboundaryrefinements remain unresolved.
Do not promote reducedsupport or treat two correlatedmotionchannels as timingtruth.
v89firstJSONserializationfailure preserved; nativecountconversion/self-check fixed.

## v80-v82: crop correctness is not sufficient accuracy recovery
Reject universalATEbenefit: fullnativeprojection oldclock156.001639->156.018832mm worsens. Newclock gains only0.131942mm; originalcontrolNo13+9.0216% andNo17+7.9888% stillfail5%guard. CropfixhelpsNo13ST2(165.642->135.982mm), butlong10x5Trial1changesnegligibly430.053->430.033mm. Do not attribute mainclock regressiontofilteredgesalone orpromotecorrectnessbasedonlowermean. Fullnative path retained for next provenanceaudit, historicalwinner untouched.
Abortedattempts preserved: inverseclock cancellation-2.08e-17s invalidatedfirstgrid sample (snappedwithin1e-9s only); Windowsrelative-manifestseparatorKeyError beforefit (nativePathkeyused). Conservative gapinterpolation can rejectvalidfirstsample aftergap; real207support assertionspass. No relaxedresearchguard, no localizationselectedlag, no larger model proposed. Separatecontextreview agrees diagnostic-only.

## v78-v79: reject universal pure clock interpretation
Identical initial poses and coefficients do not guarantee a pure timing intervention: optical-dependent crop precedes offline gravity projection. Raw and wheel channels agree at matched sensor time, while slope projected yaw differs up to0.863376deg/s. First-order phase explains most but not all cases. Do not hide slope exceptions, use after-crop optical poisoning as proof of upstream independence, or declare a new estimator gain before full-native preprocessing/fold refit. Historical recovered-supervisionv32 still rejects on extended metrics.

## v74-v76 exclusions / failed assumptions - 8 October 2026
- Cropped comparison-array last sample is NOT automatically the genuine acquisition endpoint: all207v73comparisonarrays lack it. Old201.238131/193.837472mm values are last-supported errors. Genuine endpoint/drift null; never silently reinterpret them.
- Stored residual-zero positions are not independently observed reference. Expanding support raises new/new147.697253->165.376107mm without estimator changes; unknown reconstruction provenance and visible spur block strict added-supervision justification. Do not repeat already rejectedv32 processed training without new evidence.
- Legacy filter-position-then-gradient creates small constant-speed synthetic boundary bias (~0.000101m/s in the tested case). New diagnostic uses gradient then filter; unchanged historical targets retained. Do not silently compare old/new derivative-defined metrics.
- Better mean still fails5%participant guard and multiplemaneuvers; no promotion/Git push. Metric extension applies currently to frozenv73cells, not all previous models. Availability flags are not a frozen catastrophic-error definition.

## v70-v73 decisions
Reject dropping unseen No.20 geometry:15accepted trials would disappear. Reject promotion of arbitrated-clock simple full predictive refit despite156.002->147.697mm mean gain: No.13+10.48%, No.17+8.04%. Changing inherited synchronization coefficient magnitudes is not a useful correction for these signals: normalized yaw cancels positive affine scale/offset and no alignment shift>1ms. v73 shows the participant regression persists with a fixed model, so another calibration/network fit alone is not the evidence-selected remedy. Do not revert clocks by choosing localization RMSE.

## v66-v69 correctness milestone
Rejected: a large within-labelled-run numerical integration error. Cached body derivatives close local observed segments to0.410798mm; global v63 residual is not a numerical accuracy floor. Rejected inference: worse global absolute-heading oracle means yaw is unimportant. v67 demonstrates improved observed1s motion and altered gap/run cancellation. No heading oracle is deployable. Do not rerun completed closure/accounting/reproduction jobs without a different falsifiable question.

## 8 October 2026 â€” competition plan and final numeric checkpoint
v62/v63/v64 finished; no expired sessions remain to poll. v62/v64 reject all speed candidates: ST regressions persist after removing center acceleration, dynamic gravity and nonlinear/direction-aware wheel features. v63 TRAIN-only derivative counterfactual suggests forward-motion opportunity but does not close 10x5 paths; absolute-heading diagnostic still missing. v65 inventories supplied historical two-IMU folder: 49 metadata recordings, 37 July wheelchair-marker C3Ds, 21 empty C3Ds, one static pair; no split changes. Unknown identities/semantic duplication block strict-track inclusion.
Latest user adopts bounded competition plan (eight new families, three prespecified configs), existing data only, no remote push. Parallel agents hit workspace credit limit. Numeric artifacts saved; retained result unchanged. See research_docs/competition_execution_checkpoint_2026-10-08.md and NEXT_SESSION.md for exact commands and next10 priorities.

# Failed ideas â€” preserve evidence

- v58 projected yaw plus v56 residual improves147.747->143.447mm but ST+38.48%.
  Reject. v56originalgain.25 itself fails new STmaneuverguard+32.76%.
- v60 exact intervalspeedloss improves mean141.996mm but ST+55.44%; allfour
  nonzero speed corrections fail maneuver guard. Jacobian checked, not a mathbug.
- v61 timingaware disagreement improves ranking but worsens NLL and varianceMAE;
  worstperson2.27x/PS3.04x. Do not treat its variance as calibrated filter confidence.

- v11 already tested acceleration-assisted velocity smoothing with asymmetric
  braking prior and rejected every candidate. New uncertainty research must
  isolate added slowbias/timing-uncertainty predictiveness first, not repeat it.

- Firmware Info gyro correction is not a trajectory improvement for these CSVs.
  v57 verifies unchanged raw-count inputs; multiplying them by1.14688 would be
  an unjustified change to an empirically calibrated pipeline. Exact firmware
  version/range cannot be recovered from packet cadence alone.

- Newclockv38 mean96.329mm cannotbepromoted: trainingworstperson+55.96%;No13periodic4.8517s clockalias independentlysupportedold. Same-newclockdampingguardpassisnotanoveralloldclockguardpass.
- Strongestmatchingeventalonecanpickawrongperiodiccycle; first/last eventordinal acrossfullIMUandfragmentedoptical peaks isundefined unless correspondingacquisitionboundariesarevisible. Twochannels onfixedsupport plusdistributedwindowsneeded.
- Purephysicalwheelyaw remains979.634mm afterindividualfits; nonzero yawblends fail. Jointmidpointwheelcoefficients aren't physicalindividualrimvelocities.
- Pertrialstartupwheelbiasmechanism unsupported:only1/207train+1/71valquiet; almostall usefallback. Laterquietexistsbutdoesnotvalidateautomaticbodyvelocityzeroing.
- Root fullrecordquiet predicted-yawbias interpolationv41 worsens everypredeclarednonzerotraininggain;worstpersonratios1.124/1.264/1.559. Zerochosen. Do notrepeatsamegate/cap/interpolation.

- Equal-weight stored processed endpoint labels: 105.172 mm; plus rates 110.932 mm vs 102.585 control. outputs_recovered_training_v32. Rejected.
- Confidence weighting processed endpoints v33: training-selected weight .5 gives 103.212 mm. Weight .1 gives only .00145 mm validation gain. Do not choose .1 from validation. outputs_weak_labels_v33.
- Undamped dynamic tilt: 100.565 mm but >5% training-person guard violated. Damping .75 selected on training resolves this conditional guard; separate experiment.
- Braking acceleration bridge v34: .25=114.483 mm, .5=136.825 mm. Training selects zero. Gate fires 597 events including ordinary turns/ascent; gravity/tilt confounding. Improves No.18 PS2 but creates large regressions elsewhere. outputs_braking_bridge_v34. Do not repeat broad gate.
- Joint forward/lateral/yaw interval v35: training-selected .3 lateral regularization/.25 lateral gain gives 102.610 mm and worsens heading 1.362 -> 1.398 deg. Other validation-selected grid scores are ineligible substitutes. No material improvement. outputs_joint_planar_v35/report.md.
- Larger training/epochs alone previously reduced loss while trajectory accuracy worsened.
- No.5 AR2/AR3: optical-front/180-degree ambiguity unresolved; no independent physical evidence. Never choose a sign flip by minimizing evaluated error.

- Residual affine clock skew v36: no heldout signal-correlation advantage over residual constant offset. Training .000976439 affine/.001008942 guarded vs .001027325 offset; validation likewise favors offset slightly. No deployed clock-skew improvement established. Do not repeat an unguarded skew fit without distributed independent timing events. Short trials are unidentifiable in this8s protocol, not proven drift-free. Source `outputs_affine_clock_v36/`.
- v37 offset reassignment has regressions despite99.506231mm aggregate synchronization-counterfactual RMSE: No14long10x5Trial1 +21.578mm, several No5/No10 long trials +1â€“3mm. This is not a replacement production model; refitting corrected training labels and preserving initialization/coverage must precede an estimator improvement claim.

- Unguardedv9corrected-clock residualrefitv38 validation96.329mm is NOTrobustlypromoted: same-fitting-ID conditionalfolds v39 worstpersonNo13+55.96%,No8+5.80%; headingworsens. No13long10x5Trial3 v9clock+4.8517s repeatedcyclealias causes1.589m vs182mm. NativeCOMMONsupport signalcorrelation favorsoldclock(.99786vs.66475yaw;.85886vs.29529speed), so thisis referenceclockfailure ratherthanmerely modelgeneralization.
- Same-newclock refitdampingv40 .75 passesrelative-to-frozennewclock5%guard andgives96.561mm nativecommonvalidation, butoldclockguardfails58.04% dueunchangedalias. A badnewclockbaseline mustnot hideclockregressions. Do notpromote untilbasinadjudicationfixed.
- Hardrejectingalllargeclockjumps wouldloseNo15PS1legitimaterepair: oldâˆ’4.925â†’newâˆ’.7652s, commonspeedcorrâˆ’.96344â†’.99866, trainingtrialâˆ’1.834m. Needfixed-support multichannel/event evidence, not blanketjumpthresholdorposition-minimizing clocks.


Restored individual wheelgyro calibration againstvÂ±L*yaw/2,v38: purewheel yaw979.634mm/39.01deg; allnonzero yaw blends failparticipantguard. Zero-wheel-yaw midpoint refit has no validationgain. Do not add wheel yaw to v34 as a trusted physicalconstraint. Stationary wheelbias is a different futurehypothesis. Evidence: outputs_physical_wheel_v38/report.md.


v39nativewheelquietbias+zero-intercept fits do not rescue differentialyaw: .25/.5blends474.675/673.158mm. Startupgatequalifies only1heldtrain+1validation record; mostcasesdatefallback. Tiny0.091mmvalidationgain atzero yaw is not usefulphysicsimprovement. Avoid relaxinggates fromevaluatedtrajectoryinspection. Evidence: outputs_wheel_bias_v39/report.md,gate_diagnostics.csv.

## v42 arbitration improves means but does not pass guard
Do not promote94.835mm: No.8conditional fold regression5.80% exceeds frozen5%guard. Clock alias correction is supported; universal improvement is not. Absolute supported path-length error also worsens. Full calibration/base folds are still inherited. Next experiment must isolate No.8, not loosen acceptance thresholds.

Arbitrated-clock dampingv46 fails old-clock guard at every predeclared weight; same-clock guard alone again hides correspondence regression. Do not try additional finely searched weights to evade1.05.

v49 simple fullyrefittedphysics+nonlinearendpoint gain.5 hasNo20+83.28% despiteoverall4mmgain. Reject. Do not revertNo8correctedclocks onpositionRMSE: yaw/speedevidencefavorsnew, opticalboundarymidmotion explains accumulatedtravelshift.

## 2026-10-05 additions
- v50 confirms pointwise/endpoint simplification does not solve full-refit robustness: linear endpoint reduces mean to214.171mm but worst participant ratio1.769287; point models are much worse. Physics remains selected.
- Do **not** apply the firmware Info gyro correction factor (~1.14688) to kight_recover research CSVs. They are raw int16 and empirical calibration already operates on raw counts. Doing so would double-correct a metadata bug that was never applied.
- Do **not** replace recorded device timestamps with row/100, seq/100 or seq/104. Firmware audit proves requested100Hz, sensor104Hz and recorded polling~102.4Hz are distinct; pipeline already uses device timestamps.
- Do **not** repeat v52 projected-gravity yaw as if new for v34: related projection features already exist in v33/v34. v54 validates the mechanism only within the simpler full-refit physics family and still sits153.607mm versus retained v34 100.702mm.
- v55 rejects a yaw-first explanation for No.18 PS2: observed-yaw-only leaves405.114mm versus405.191mm predicted, while observed-speed-only gives60.344mm. Future work should target bounded continuous forward-travel/braking residuals or uncertainty fusion, not another broad yaw correction or the failed v34 braking gate.
## v83-v85: seed provenance alone does not establish clock correctness
Fresh magnitude-only clock seeds190/207; locally nested signedfoldfits199/207held clocks. Rejectcompletecoverage/reliability hypothesis: eightunsupportedheldclocks,No13longT3knownperiodicalias+4.8517s loses458frozenframes,No19OS1+0.5821s. Uniquecorrelationgateacceptancealonecannotcertify correctbasin. Do not fallbacktoinheritedfittedclocks,droprejects,relaxgates,orfit/claimlowerATEon199subset. Localfitprovenancefix supported, fullgeometry/QC/datasetnesting unresolved. Noaccuracyresultpromoted; allnewtrajectorymetrics unavailable since no predictions. Nextnew evidence must be distributedsignedyaw/speedevents from freshfoldfits, not another identicalseedrerun.

## v91-v93: interior optima and role separation are not clock certification
Elevenoftwelve boundedbasinsinterior doesnotmean trueoffsets. No13 -.859s speedmax
reducesyawcorr versusearlier -.825s; channel/objectivetradeoff unresolved. No7best
passes .6speedcorr but loses91scoredframes. No19singlewindow unchanged;seven
candidateemptycases unaffected. Do not widenNo7search,acceptaliasesfrominterior
status,dropunsupportedtrials,orfit199subset. GeometryrolescontractpreservesNo20
but doesnotvalidate unseenmarkerband orerase inheritedinstrument/QC/selection.
