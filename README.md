# Wheelchair trajectory reconstruction

## Repository contents

Source code, configuration, research notes, and the latest trajectory PDF are included. Raw recordings (`c3d/`, `imu3/`, `samplerawdata/`), fitted experiment artifacts (`outputs*/`), and temporary files remain local. Existing inference/report scripts require those local experiment artifacts; cloning this repository alone does not provide a trained model or the dataset.

For a quick directory and script guide, see the [repository map](docs/repository-map.md). Files and paths were preserved because historical scripts and sealed research records refer to them directly.

Research continuation instructions are in `research_state/NEXT_SESSION.md`. The latest TRAIN comparison is `research_docs/axis_prior_results_v125.md`; the latest completed validation comparison is `research_docs/frozen_validation_results_v126.md`. The earlier trajectory PDF is `output/pdf/trajectory_research_accuracy_audit.pdf`.

Offline three-IMU reconstruction of the 2D wheel-hub midpoint, evaluated against Qualisys. Current code implements protocol amendment v2. The original evaluated artifacts remain immutable in `outputs/`; their source snapshot is in `experiments/v1_source/`. Current runs default to `outputs_amended_v2/`. The same participant assignments are preserved. Because the original test was inspected, amended test results are retrospective and cannot be described as a new blind evaluation.

## Latest result and research methodology

**Best completed validation model: v121 at 99.303735 mm equal-person XY ATE.** On 15 October 2026, the frozen v125 comparison returned **99.700352 mm** and failed the original acceptance criteria. V125's lower TRAIN error did not transfer to this validation cohort. All 71 validation recordings, four participants and 105,821 scored frames were retained.

**Primary metric for comparison:** equal-person XY ATE RMSE in millimetres. For each recording, it is the root mean square of the 2D distance between the reconstructed and Qualisys midpoint positions on matched supported frames; participant results are weighted equally. Lower is better. Compare models only on the same recordings, frames, clocks and scoring protocol.

| Frozen model | Matched validation ATE, mm | Decision |
| --- | ---: | --- |
| v34 | 100.702119 | Historical control |
| **v121** | **99.303735** | **Retain as best completed validation model** |
| v125 | 99.700352 | Rejected: mean error and OS regression versus v121 |

V125 is 0.396617 mm (0.399%) worse than v121; all four participants worsen by 0.293% to 0.545%. Its OS maneuver worsens **5.276%**, above the unchanged 5% limit. V125 passes the guards against the older v34, but acceptance also requires passing the stronger v121 comparison. The slightly lower route RMSE and 10-second RTE do not override this decision; 10-second RTE covers only four recordings/two people. See the [full comparison, per-person/maneuver results and availability](research_docs/frozen_validation_results_v126.md).

### How the final comparison was made

1. **Freeze after TRAIN selection.** V125's speed/yaw prior strengths (1,10), full-TRAIN weights and model hash were fixed before this comparison. The completed TRAIN experiment, package checks and independent reviews are preserved below.
2. **Reproduce both controls first.** Reconstruct original IMU startup and all 142 public v34/v121 predictions on the 71 recordings. Compare with the sealed v123 reference, clock/crop/time grid, motion, position, heading, metrics and support. The largest motion/position difference is 2.23e-16, inside the original unchanged tolerances; reference arrays and finite support match exactly. Match the original four-thread CPU calculation.
3. **Evaluate one candidate once.** Predict v125 using only sensor/setup/IMU initialization and integrate from the same single observed initial pose. Preserve every supported frame, all historical/v74 metrics and availability denominators. No fitting, alternative candidate, retuning or reserved-test use occurs in the comparison.
4. **Apply the original decision.** Require lower mean ATE and all participant/maneuver/P95 position/last-supported endpoint/heading guards against both controls. V125 fails the stronger v121 comparison and is rejected. Retain the unchanged [frozen v121 model and usage](models/reservoir_path_v121_completed/README.md), loaded by `reservoir_inference_v121.load_reservoir_model()`.

The runner's nine synthetic contracts passed, and the guarded evaluation/report completed successfully. **Independent review passed:** all 213 saved motion integrations, exact support, core metrics, both guard decisions and all 2,556 grouped rows/availability denominators were verified. It checked 156 output files and 524 input pins: 169 permitted inputs were independently rehashed, while 355 protected raw/cache/older-trajectory entries were compared with sealed v123 hashes without reopening those contents. See `research_state/v126_independent_review.json` and the [review closure](research_docs/frozen_validation_review_v126.md). The protocol and contextual user direction were recorded before scoring in [v126](research_docs/frozen_validation_v126.md). This consumed the proposed single comparison; the earlier proposal's future-tense wording is historical.

The four-participant descriptive benefit interval for v125 versus v121 is **-0.608 to -0.252 mm**; 0/4 participants improve and the exact sign-flip fraction is 2/16 = 0.125. This previously exposed development validation does not establish independent significance or blind final generalization. All three model bundles remain unchanged. Original independent timing, firmware/runtime identity, geometry and final-acquisition evidence remain unresolved.

### How v121 became the retained validation best

V121 was selected on TRAIN, not by searching the exposed validation set. Its
fixed 16-state recurrent reservoir encodes central gravity/rotation IMU features;
a joint forward-speed/yaw readout is fit against accumulated XY and heading
trajectory error. Fit-only normalization, seeded recurrent weights, correction
caps, participant-held folds and the frozen v34 parent were retained. Of three
predeclared ridge penalties, penalty 10 passed every participant, maneuver,
position-tail, endpoint and heading guard; penalty 1's lower mean failed the
participant guards. It reached 129.739811 mm on matched TRAIN (v34: 132.240200
mm), with all 207 recordings and 12 participants retained. See the [v121 method
and selection report](research_docs/reservoir_path_results_v121.md).

The later frozen v123 evaluation compared that unchanged candidate once against
v34 on all 71 exposed validation recordings, reproducing the control first and
keeping the original support and guards. It measured 99.303735 mm versus
100.702119 mm for v34, passing every guard. V126 then compared one frozen v125
candidate against both v121 and v34; v125 was rejected because its mean was
worse than v121 and its OS regression exceeded 5%. Therefore v121 remains the
best completed validation model. The validation is previously exposed
development evidence, not a blind or independent final evaluation.

### TRAIN development result — v125

**V125 remains the best accepted matched TRAIN model at 127.531627 mm XY ATE**, improving v124's 128.872854 mm by **1.341227 mm (1.041%)**. Eleven of twelve TRAIN participants improve. All 207 recordings, 12 participants, 15 No.20 recordings and 314,498 scored frames remain present; every original TRAIN guard passes against **all three controls: v34, v121 and v124**. Its subsequent validation rejection is recorded above. The TRAIN and validation figures describe different cohorts.

| Matched TRAIN readout | Equal-person ATE, mm | Decision |
| --- | ---: | --- |
| Frozen v34 | 132.240200 | Historical control |
| Frozen v121 | 129.739811 | Best completed validation model |
| Frozen v124 | 128.872854 | Previous TRAIN best |
| **v125 speed prior 1, yaw prior 10** | **127.531627** | **Selected: every guard passes** |
| v125 speed prior 10, yaw prior 1 | 128.156224 | Rejected: No.6/No.8 participant guards |
| v125 speed prior 3, yaw prior 3 | 127.563048 | Rejected: No.8 versus v34 |

### How we obtained v125

1. **Use the previous failures to define one change.** V124's lower scalar regularization improved the mean but failed participant guards. Speed and yaw corrections have different scales and effects on path integration. Preregister exactly three separate speed/yaw prior strengths: (1,10), (10,1), (3,3). Keep v124's smoothed trial XY/heading RMSE objective and the same fold's frozen v121 weights as the prior. See the [fixed hypothesis, equation and acceptance criteria](research_docs/axis_prior_v125.md).
2. **Preserve the full comparison.** Keep the fixed 16-state reservoir, normalization, 17-by-2 readout per setup, correction caps of 0.05 m/s and 0.02 rad/s, v34 motion, original participant folds, clocks, crops and support. Reproduce all 207 v34/v121/v124 motions, positions, headings and primary metrics before any new fit. Each held participant stays outside the readout, prior and normalization fitting. No identity or optical labels enter motion prediction.
3. **Fit and select once.** Use up to twelve GN/IRLS iterations, every original integration timestep, the inherited every-tenth supported fitting samples and fitting-only line search. One fold/setup stops after ten iterations under the unchanged zero-step rule. Select the lowest ATE only if it improves v124 and passes the original participant, maneuver, P95 position, last-supported endpoint and heading guards against all three controls. The speed-1/yaw-10 readout passes; both alternatives are rejected.
4. **Freeze a callable model and verify it.** Fit that pair once on all 207 TRAIN recordings using the frozen full-TRAIN v121 prior/normalization. Save `models/axis_prior_v125`; the existing `reservoir_inference_v121.load_reservoir_model('models/axis_prior_v125')` loads it directly. Every public sensor-only prediction matches the fitted motion exactly (maximum difference **0**), and all 207 optical/identity poisoning checks pass. Full-TRAIN package reproduction is distinct from participant-fold accuracy.

Independent screen review verifies 224 output, 642 input and 20 source hashes, all 1,242 prediction sets, 1,863 exact control-array comparisons, saved-motion integration, 64,584 direct metric values and every selection guard. Independent package/report review verifies six bundle outputs, 451 inputs, 36 dependencies, all 207 saved inference records, all **8,520 grouped metric rows**, explicit availability denominators and paired uncertainty. The synthetic checks cover all 34 gradient columns including saturation, exact equivalence to scalar regularization, monotone deterministic fitting and an exact prior. See the [full results](research_docs/axis_prior_results_v125.md), [independent review closure](research_docs/axis_prior_review_v125.md) and [model usage](models/axis_prior_v125/README.md).

The improvement is broad across people but not universal across maneuvers. Versus v124, No.4 worsens 0.545%, PS worsens 2.039% and ST worsens 0.147%; five of seven maneuvers improve. No.8 remains **4.929% worse than v34**, close to the fixed 5% limit. P95 position, last-supported endpoint and heading improve versus all three controls. All candidate outcomes and supplementary metrics are retained.

The descriptive participant bootstrap interval for improvement over v124 is **0.477 to 2.312 mm**; the exact sign-flip fraction is **26/4096 = 0.006348**. Mean benefit remains positive after omitting any one participant (1.036 to 1.515 mm). These are **conditional, post-selection TRAIN summaries**, with repeated development exposure, and do not establish independent significance or validation performance. The inherited 266 parent training records, offline future context, optical-dependent crops, calibration inheritance and unresolved clocks/acquisition/runtime identity remain limitations. The TRAIN experiment included no validation/test scoring; the subsequent one-candidate v126 comparison is recorded above. No deployment, commit or push occurred.

Frozen v125 model JSON SHA256: `7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2`. The [single frozen v125 comparison proposal](research_docs/frozen_validation_decision_v125.md) has now been executed as v126; it does not authorize repeating evaluation or tuning from its outcomes.

### Previous accepted TRAIN model — v124

Earlier on 15 October 2026, v124 reached 128.872854 mm XY ATE, improving v121's 129.739811 mm by 0.866957 mm (0.668%). All 207 recordings, 12 participants, 15 No.20 recordings and 314,498 scored frames remain present. Every original guard passes against both v121 and v34. V124 has no validation result. Its development route is preserved below.

| Matched TRAIN readout | Equal-person ATE, mm | Decision |
| --- | ---: | --- |
| Frozen v34 | 132.240200 | Historical control |
| Frozen v121 | 129.739811 | Previous accepted model |
| v124 prior penalty 0.1 | 129.250415 | Rejected: participant, maneuver and heading guards |
| v124 prior penalty 1 | 126.775358 | Rejected: participant guards |
| **v124 prior penalty 10** | **128.872854** | **Selected: all guards pass** |

### How we obtained v124

1. **Review the current best.** V121 combines the frozen v34 motion model with a fixed 16-state recurrent reservoir and a 17-by-2 forward/yaw readout per acquisition setup. Its fitting objective averages squared trajectory errors, while selection averages trial RMSE equally within each participant. The [source review](research_docs/model_review_v121_2026-10-15.md) documents the input features, inference path and inherited limitations.
2. **Preregister one bounded change.** Keep the same features, normalization, random state, correction caps (0.05 m/s and 0.02 rad/s), clocks, crops, participant folds and support. Replace squared path loss with smoothed trial XY RMSE plus heading RMSE, with a quadratic penalty centered on the frozen v121 weights. Test exactly three prior strengths: 0.1, 1 and 10. See the [fixed protocol and loss equation](research_docs/trial_rmse_v124.md).
3. **Reproduce both controls before fitting.** All 207 saved v34 and v121 motions, trajectories, headings, support arrays and primary metrics reproduce. Fit each candidate only on the other participants in its fold, using twelve GaussNewton/IRLS steps and a fitting-only line search. Integrate every timestep; use v121's every-tenth supported fitting samples. No maneuver or participant identity enters inference.
4. **Select with the original guards against both controls.** Penalty 10 improves six of seven maneuvers and eight of twelve participants versus v121. PS worsens 0.555%; the largest participant regression is No.8 at 2.159%. Against v34, No.8 worsens 4.956%, close to the fixed 5% limit. Position P95, last-supported endpoint and heading all improve versus v121. The lower mean at penalty 1 is rejected: No.6 worsens 7.720% versus v121, and No.6/No.8 exceed the v34 guard.
5. **Fit once, freeze, and check the actual loader.** Fit selected penalty 10 on all 207 TRAIN records using the frozen full-TRAIN v121 prior/normalization and v34 parent. Save a separate bundle at `models/trial_rmse_v124`. The existing `reservoir_inference_v121.load_reservoir_model('models/trial_rmse_v124')` loads it directly. All 207 sensor-only predictions reproduce with maximum motion difference **0**, and every optical/identity poisoning check passes. These package checks are distinct from the participant-fold accuracy scores.

The independent screen review reconstructs all 1,035 paired prediction sets, 314,498 frames per model, every core metric and guard, and verifies 224 output, 636 input and 17 source hashes. See the [screen review](research_state/v124_independent_review.json), [complete results and per-person/maneuver tables](research_docs/trial_rmse_results_v124.md), and [bundle usage](models/trial_rmse_v124/README.md). All supplementary metrics and their availability denominators are retained in `outputs_trial_rmse_v124_report/grouped_metrics.csv`.

The descriptive paired bootstrap interval for improvement over v121 is **-0.127 to 1.941 mm**; the exact sign-flip fraction is 0.1533. Mean improvement remains positive after omitting any one participant (0.555 to 1.102 mm). These are conditional, post-selection TRAIN results and do not establish independent significance or validation performance. Repeated development exposure, the inherited 266 additional parent training records, offline context, optical-dependent crops, and unresolved acquisition/clock provenance remain limitations. No new validation/test scoring, deployment, commit or push occurred.

Frozen v124 model JSON SHA256: `ac46f8b82096214da181624f7be0362ddc8494f1b44fa4827c68f01d41421ce7`.

Independent package/report review also passes: all 207 saved inference checks, bundle dependencies, 7,100 grouped metric rows, denominators and paired uncertainty calculations were verified. Its [review closure and supplemental provenance](research_docs/trial_rmse_review_v124.md) preserve the sealed report. The earlier [v124 validation proposal](research_docs/frozen_validation_decision_v124.md) was not executed; v125 now supplies the next frozen candidate.

### Best completed matched validation — v121

**Frozen v121 passes matched validation: 99.303735 mm equal-person XY ATE versus v34 at 100.702119 mm**, a 1.398384 mm (1.39%) improvement across the same 71 exposed validation recordings, four participants and 105,821 scored frames. All predeclared guards pass. This remains the best completed guard-passing validation comparison; deployment promotion is not included. See the [full comparison and methodology](research_docs/frozen_validation_results_v123.md).

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

The unchanged model is `models/reservoir_path_v121_completed`, loaded with `reservoir_inference_v121.load_reservoir_model`; SHA256 of model.json is `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`. Paired predictions and full trial tables are sealed in `outputs_frozen_validation_v123_exact`. Supplementary overall/participant/maneuver tables, with explicit availability denominators, are in `outputs_frozen_validation_v123_report/grouped_metrics.csv`. Independent review also verified all 1,704 aggregate rows and their denominators. RTE at 1/5/10 seconds covers 71/39/4 recordings respectively; the 10-second result includes only two participants. See [review completion and metric availability](research_docs/frozen_validation_review_v123.md).

This is previously exposed development validation, not a new blind test or proof of superiority to published methods. Frozen parent models retain an inherited dependence on 266 additional training records. Offline future context, optical-dependent crops, calibration inheritance and unresolved independent clocks/firmware provenance limit interpretation. The completed v123 comparison included no refitting or retuning, reserved-test evaluation, deployment promotion, commit or push. The subsequent v124 TRAIN experiment above has its own direct user authorization and protocol. Independent final data and provenance evidence remain needed for stronger claims.

The direct development request on 15 October 2026 authorized the completed v124 TRAIN experiment above. Its frozen candidate requires a separate matched validation decision under the preserved evaluation boundary. The completed v123 comparison must not be repeated or used to retune v124; the strict independent timing and final-acquisition requirements remain unresolved.

### Historical research and v34 validation methodology

Continuation on 15 October 2026 corrected the historical acquisition evidence
and next-experiment documents so their old +/-2 g/unverified-serialization
statements cannot be mistaken for current findings. The source/data audit supports
raw int16 at +/-4 g and +/-2000 dps; exact per-recording firmware/runtime settings,
independent timing, geometry and new final data remain unresolved. See the
[remaining acquisition gates](research_docs/frozen-next-experiment-protocol.md).
No new fit or evaluation was run; the best guard-passing result and the method
above remain unchanged.

The following chronological notes describe earlier checkpoints. Any pending-validation or best-model statement below is superseded by the completed v123 comparison above.

Latest continuation (v97-v114) recovered the skid-correction equations and
checked their literal domain on all 207 TRAIN recordings. Among 429,583 eligible
resampled sensor frames, 600 weights are undefined and 153,330 fall outside
[0,1]. These are **conditional proxy diagnostics**: wheel bias/sign remain
supervised, radius/scale nominal, and the inputs are resampled rather than native.
No clipping or fallback was silently added, and this is not physical skid prevalence.
See [source/domain audit](research_docs/skid_source_domain_results_v97_v99.md).

WISDOM camber equations pass 216 synthetic cases (maximum recovery error
2.22e-16), and the recent three-IMU paper's affine trigger map passes synthetic
endpoint checks. Its external 300 m calibration and GPS task are incompatible
with a direct optical ATE comparison. WISDOM equations remain text-derived;
its PDF screenshots failed. An incorrect agent curvature derivation was caught,
preserved and corrected by the check; no source error is claimed. See
[verified source checks](research_docs/wheel_source_results_v100_v101.md).

The official repository is single-wheel Wheel-INS, with explicit initialization,
fixed-rate and gap-handling issues to resolve before comparison; its link to
Wheel-INS2 does not supply multi-IMU code. Sixteen pinned source/config files
match Git blob hashes and a separate read-only review agrees. See
[implementation audit](research_docs/wheel_implementation_v102.md) and the
[primary-source comparison matrix](research_docs/competition_source_matrix.md).
The delegated Fuss source passes 54 ideal rolling checks; its literal yaw
formula is undefined at zero camber (18 cases), without implying that all yaw
information is unavailable. The source typography remains text-derived. The
input audit verifies all 429,790 common-grid sensor frames are valid and all
207 trials have a complete first 500 ms, which does not establish stationarity.
Nominal geometry, supervised scalar axis fits and missing physical calibration
remain explicit in the [input evidence and results](research_docs/wheel_source_results_v103_v105.md).
Clock coverage stays 199/207. No trajectory refit, validation/test access,
promotion or competitor outperformance followed. The retained best and its
training-selection methodology below remain unchanged.

The 2023 mobility paper and 2025 MASSWU full papers/supplement now have a
reviewed metric and implementation audit. Their wheel/task outcomes do not
supply comparable midpoint XY ATE. Participant-specific calibration and
mechanical synchronization are prerequisites in the 2023 method; MASSWU's
published code snippets do not supply its prose processing or synchronized
sample interface. Mixed statistical coefficients and unresolved angular units
are explicit in the [reviewed source results](research_docs/mobility_source_results_v106_v107.md).
Neither method has been reproduced on this dataset.

The preregistered full-record projected-yaw clock diagnostic (v108/v109)
retains the same 199/207 accepted clocks and adds 21 unsupported frozen scored
frames relative to the scalar baseline; it does not unlock refitting. Independent
feature reconstruction is exact. The historical No13 4.8517 s value is a clock
**change** from -0.7000 to +4.1517 s, not the returned offset; v108 remains on
that positive alias at +4.1566 s. See [clock diagnostic and correction](research_docs/projected_clock_results_v108_v109.md).
No new trajectory result or promotion followed. A logical audit of the sealed
reference metadata (v113) finds six trials that cannot satisfy the frozen
motion/two-peak reference requirements: any IMU-only feature search has an
upper bound of 201/207 accepted clocks. This is an algorithm-contract limit,
not proof that physical timing is unobservable; further IMU-only searches stop.

The retained v34 versus v21 benefit is **1.883 mm (1.836%)** across four already
exposed validation participants. Exact paired participant resampling gives an
empirical sensitivity interval **−0.104 to 4.380 mm**, and the conditional
two-sided sign-flip result is **p = 0.375**. No.10 worsens, and omitting No.14
reduces the mean benefit to 0.584 mm. These are retrospective aggregate analyses,
not a prospective significance claim. See [current same-data evidence](research_docs/final_same_data_comparison.md)
and [uncertainty result](research_docs/retained_uncertainty_results_v114.md).
The 2023 single-wheel rotation and 2022 optical-reference sensor-reduction papers
now have full-method/metric audits; mounting, units, reference and implementation
differences prevent a faithful local comparison. The earlier usage-limit and
pending-review notes were superseded by the 10 October checkpoint: v112–v114
independent review completed without substantive defect. The campaign remains
incomplete; independent timing/provenance and final-data requirements remain.

Retained historical v34: **100.702119 mm** mean participant-balanced trial synchronized XY ATE RMSE, on 71 previously exposed validation trials. Its documented geometric route RMSE is 49.726 mm. This is retrospective evidence, not a prospective blind result or a demonstrated victory over published methods.

The progression was calibrated wheel/frame physics, training-fitted residual and interval corrections, then frozen inference reproduction (v36). Later native-clock refits and simple estimator experiments exposed participant regressions and reference/clock dependencies, so they did not replace the retained model. Participant partitions precede windows; deployment motion uses IMUs, with the permitted initial optical pose only. Original observed C3D remains primary; no post-hoc alignment, scale fitting or optical resets.

Latest v74-v76 audits add tested metrics and separately evaluate stored processed C3D. TRAIN207 simple old/old versus new/new is 156.001639 versus 147.697253 mm, rejected by participant guards; these are a different dataset/evaluation scope from the retained score. Their 201.238131/193.837472 mm drift values are **last-supported endpoint errors**, because cropped predictions do not reach the genuine acquisition endpoint. Expanded lower-confidence processed support changes new/new to 165.376107 mm without improving the estimator. See [full metric and reference audit](research_docs/metric_contract_processed_reference_v74_v76.md) and [continuation state](research_state/NEXT_SESSION.md). Historical targets/evaluators are preserved; the new velocity diagnostics and RTE definitions are explicitly versioned. Only qualifying promoted estimator improvements may be committed/pushed under the latest authorization.

### Latest mechanism audit: v77-v79

The complete metric audit reproduces retained v34 at 100.702119399 mm and rejected historical candidates without refitting. TRAIN-only diagnostics show clock changes also alter optical-dependent IMU crop boundaries: the offline gravity filter changes projected yaw by up to 0.863376 degrees/s despite identical time-matched raw and wheel channels. The next controlled fix is full native IMU preprocessing before optical cropping, followed by matched participant-fold evaluation. No accuracy improvement or model promotion is claimed yet. See [clock/crop mechanism audit](research_docs/clock_crop_mechanism_v77_v79.md).

### Full-record preprocessing result: v80-v82

The crop dependency is now removed in the versioned experimental path: full-record sensor filtering reproduces identical raw samples and projected yaw across evaluator crops on all 207 TRAIN recordings. Under fixed participant folds, clocks, observed-reference masks and initial poses, native preprocessing changes the new-clock simple estimator from **147.697253 to 147.565311 mm ATE**. The old-clock control slightly worsens, and No.13/No.17 still fail the original 5% participant guard. Therefore the best retained result remains **v34, 100.702119 mm**, obtained through calibrated wheel/frame physics, training-fitted residual/interval corrections and the frozen 0.75 dynamic-tilt blend, then reproduced by v36 and independently audited by v77. These are different evaluation scopes; the latest preprocessing result does not replace the retained model.

The controlled method and exact route to these findings, including full metrics, failed attempts, independent numerical checks and separate-context review, are documented in [native preprocessing research](research_docs/native_preprocessing_v80_v82.md). Next priority is removing inherited clock-bootstrap participant dependencies with the invariant features. No validation/test tuning, estimator promotion or Git push occurred.

### Seed-free clock bootstrap: v83-v85

The latest experiment removes historical held-participant seed calibration from
clock fitting: unfitted full-record gyro magnitudes generate 190/207 accepted
TRAIN seeds, then other participants alone fit each fold's signed channels.
Held-clock coverage is 199/207. A 4.8517 s repeated-cycle alias reappears and
would lose 458 frozen support frames; therefore this remains diagnostic only,
with no estimator refit or promotion. Independent label reconstruction agrees
exactly, and a separate reviewer confirms provenance and the failed coverage
gate. See [seed-free clock methodology and reproduction](research_docs/seedless_clock_v83_v85.md).

The best retained result remains **100.702119399 mm synchronized ATE** and
**49.726226563 mm geometric route RMSE**, obtained by calibrated wheel/frame
physics, training-fitted residual and interval corrections, and the frozen
0.75 dynamic-tilt blend (v34), then reproduced by v36 and audited by v77.
Subsequent fixes have not passed the required coverage and regression checks.
Next work is distributed signal/event basin evidence using fresh fold fits;
no position-error-selected clocks, changed scoring masks or reserved-test tuning.

### Distributed clock evidence and observability: v86-v90

Fresh fold signals now expose the No.13 repeated-cycle alias without using
position error: an alternative basin has stronger yaw and speed correlation
in six common-support windows. Its exact offset is still unresolved, ten of
twelve candidate refinements reach their boundary, and seven investigated
cases produce no candidates. A continuous-lag event audit explains the limits:
ten channels have too few peaks, four have insufficient motion and two cannot
match two existing events at any allowed lag. Independent source reconstruction,
dynamic-programming matching and correlation checks pass. Clock coverage stays
199/207, so no estimator is refitted or promoted. See the
[completed method, evidence and failures](research_docs/distributed_clock_results_v86_v90.md).

The route to the **retained best v34 result** is reproducible: start with the
observed-reference IMU ridge/calibrated wheel-frame motion; fit stationary
gravity features (v14), integrated endpoint corrections (v16) and bounded
nonlinear kinematic products (v21); add the 0.3 Hz dynamic-gravity feature model
(v33). v34 compares motion-blend weights 0, 0.25, 0.5 and 0.75 in three
participant-held TRAIN folds. It selects **0.75** before validation, with worst
training-person ratio **0.993947477** against the same-fold v21 control.
Blend forward/lateral/yaw motion vectors, then integrate once from the permitted
initial pose; reference positions never correct the prediction. Frozen
validation ATE changes **102.585179403 to 100.702119399 mm** over 71 trials/four
people. v36 reproduces IMU-only inference; v77 backfills and independently
checks the saved metrics, including **49.726226563 mm route RMSE**. See
`dynamic_tilt_blend_v34.py`, `dynamic_blend_inference_v34.py` and the local
sealed `outputs_dynamic_blend_v34/selection.json` and `run.json`.

This selection refits correction features and weights within folds but inherits
base calibration, reference geometry and clock preparation; it is conditional
development evidence with offline future IMU context. Subsequent lower means
have failed frozen regression or coverage requirements and have not replaced
it. Acceptance gates, all 207 identities and all fifteen No.20 records remain fixed.

### Bounded basin and geometry-role audit: v91-v93

The latest preregistered audit evaluates the twelve existing fresh event basins
within the frozen 200 ms event tolerance, at 1 ms spacing on common support.
Eleven have interior optima; one remains at a boundary. No.13's speed optimum
is **-0.859 s**, with .958315 speed/.913656 yaw correlation and zero support
loss. This is a signal-objective tradeoff, not a certified clock. No.7's best
basin still loses 91 scored frames. Clock coverage remains **199/207**.

A separate diagnostic contract keeps frozen evaluator references, support and
initial poses distinct from train-fitted geometry. All **207 records, fifteen
No.20 trials and 318,034 scored frames** are retained. Applying train geometry
to held evaluator support would exclude No.20; inherited instrument/QC/selection
provenance remains conditional. Independent arithmetic checks reproduce 9,122
grid/channel scores (maximum difference 1.11e-15), all event counts and all 207
reference arrays. No estimator refit or new accuracy claim followed.

The best result and its training-selected v14/v16/v21/v33 to v34 methodology
above remain unchanged. See [bounded audit, verification and reproduction](research_docs/basin_geometry_results_v91_v93.md).
Next is a prespecified two-channel consistency audit within the sealed intervals;
no wider clock search or predictive refit before coverage and provenance gates.

## Run

Python 3.10+ with the packages in `requirements.txt` is required. The current workspace already has these packages.

```powershell
python pipeline.py inventory
python pipeline.py baseline
python pipeline.py learn --epochs 12
python pipeline.py report
python test_pipeline.py
```

`inventory` freezes a seeded participant split before loading signals. `baseline` calibrates on training data and evaluates validation data. `learn` compares the baseline, a regularized linear residual, and two small causal TCN residual models; checkpoints are chosen by equal-participant mean validation trajectory RMSE. This establishes the best of the tested candidates, not a globally optimal model.

After the estimator and evaluation protocol are frozen, run:

```powershell
python pipeline.py final-test
```

This runs the amended retrospective test and writes a lock preventing further development in that output directory. It reports the baseline and selected model. Do not use final test results to revise the estimator, filtering, calibration, split, or model selection. A new output directory does not make an already-inspected participant set unseen again.

Optional `--root PATH` and `--out PATH` select the dataset and output directories. Keep the frozen split and manifests with the paper materials.

## Outputs

- `outputs_amended_v2/split.json`: participant assignments and identity confirmations.
- `outputs_amended_v2/inventory.csv`: pairing inventory, including unpaired recordings.
- `outputs_amended_v2/qc_train.csv`, `qc_validation.csv`, and eventually `qc_test.csv`: accepted/excluded trials and reasons.
- `outputs_amended_v2/calibration.json`: empirical raw-to-motion scales, intercepts, axes, and training trial identities per acquisition date.
- `outputs_amended_v2/run.json`: settings, split and source hashes, versions, and calibration provenance.
- `outputs_amended_v2/baseline/validation_*`: trial metrics, participant means, maneuver means, and summary.
- `outputs_amended_v2/baseline/validation/trajectories/`: trajectory CSV exports and PNG plots.
- `outputs_amended_v2/selection.json`: candidate comparisons and validation checkpoint history.
- `outputs_amended_v2/validation_report.md` and `validation_comparison.png`: comparison report and figure. `report` refreshes validation exports without refitting models.
- `outputs_amended_v2/normalization.json`, `ridge.npy`, and `tcn*.pt`: training-only normalization and fitted corrections.
- `outputs_amended_v2/final_test_lock.json`: final evaluation freeze record, created only by `final-test`.
- `outputs_amended_v2/final_test_report.md` and `final_test_summary.json`: frozen held-out results and coverage limitations.
- `outputs_amended_v2/geometry_policy.json`: reference-separation bands and rigidity thresholds derived from training C3Ds only.
- `outputs_amended_v2/protocol_amendment.json`: parent experiment hashes, changes, and already-inspected-test disclosure.

## Evaluation protocol

Sept. 24 and Sept. 25 each contribute six training, two validation, and two test participants: 12/4/4 total. All maneuvers and repetitions follow their participant. Earlier sessions supply training data only, based on the researcher's confirmation that these participants do not overlap with the 20 target participants. Their trial-to-person mapping is incomplete and remains a provenance limitation.

The baseline converts left/right wheel gyro signals into wheel speeds and frame gyro into yaw rate using robust training-only regressions. Training fits midpoint speed jointly from the selected left/right gyro channels, avoiding a fixed hub-width assumption in forward-speed calibration. Their average supplies speed; center gyro supplies yaw. Configured track width is still used for the diagnostic wheel-yaw feature and is not claimed to be independently measured. Integration receives the initial reference position and heading. No later reference positions or headings correct the estimate.

Clock mapping uses per-device timestamps and packet arrival timestamps. A training-only bootstrap uses gyro magnitudes to fit axes and scales. A second training pass freezes projected signed center-yaw and calibrated wheel-speed channels for multiple-peak alignment; the same channels are used in validation and amended test. Peak support is chronological and one-to-one. Matches with insufficient correlation, insufficient peak support, or competing offsets are excluded. This is offline evaluation with external clock alignment, not an independent live navigation result. QC reports distinguish reference, clock, and synchronization rejection stages and retain correlation, runner-up, and peak-timing diagnostics.

The reference requires valid left/right markers, separation inside bands learned from training acquisitions, and within-trial rigidity. The wider band is supported by training participant No.20. These are optical-marker distances, not measurements of actual hub width. Derivatives are filtered independently within valid segments. Reference gaps are masked; missing reference never resets reconstruction. An IMU timing gap stops reconstruction rather than inventing motion, and reconstruction coverage is reported. Endpoint percentages are withheld when gaps prevent a complete reference path length.

Primary metric is position RMSE without fitting trajectory rotation, translation, or scale after initial-pose alignment. Supporting metrics include circular heading RMSE, valid endpoint drift, and 1/5/10 m segment displacement errors aligned at each segment's starting heading. Segment alignment is used only for the relative metrics; it never corrects the full reconstructed path. Participant and maneuver tables expose uneven trial coverage.

## Learned corrections

Twenty causal features contain calibrated wheel/center rates, wheel-versus-frame yaw disagreement, trailing rate derivatives, gravity-normalized acceleration magnitudes/projections, and off-axis gyro magnitudes. Gravity scales, biases, feature normalization, and residual bounds are fitted on training only. Gyro isotropy and configured radius remain assumptions. Windows and normalization balance known participant groups; older unidentified participants are grouped by date and must not be called individually balanced. The TCN combines pointwise residual loss with short integrated position/heading loss on complete training reference spans. Residual gains of 0.25/0.5/1 and checkpoints are selected on validation; final model choice includes the physics baseline.

## GRU and uncertainty-filter comparison

The separate `alternatives.py` comparison reads the frozen v2 calibration, normalization and fingerprinted accepted signals without changing that experiment. It trains a 32-unit causal GRU with the same residual targets, participant grouping, loss and epoch budget. A diagonal Kalman rate filter uses learned measurement variance fitted on training only; validation selects its process-variance multiplier. This is a speed/yaw filter, not a full pose-and-bias navigation estimator. It never receives reference motion during reconstruction.

```powershell
python test_alternatives.py
python alternatives.py train --epochs 12
python alternatives.py retrospective-test
```

Outputs are in `outputs_alternatives_v3/`: `selection.json`, `gru32.pt`, `uncertainty.json`, candidate metric tables, `report.md`, and a frozen retrospective test lock. Model selection includes the existing TCN and physics baseline. Previously inspected test participants remain retrospective. The training command refuses to overwrite an already selected comparison.

## Parallel accuracy experiments (v4)

The consolidated findings are in `outputs_accuracy_program_v4/report.md`. New train/validation-only comparisons include a CUDA RoNIN-inspired ResNet, supervised skid proxies, mean-square process covariance, explicit lateral-velocity ridge corrections, and a CUDA forward/lateral/yaw neural residual. The best development candidate scores 0.3685 m versus frozen TCN's 0.3747 m on the same 72 validation recordings/four participants; it improves three participants and worsens one. This is exploratory reused validation, not new independent test performance or millimeter accuracy.

The neural planar candidate uses 1.28 seconds of future IMU context for offline reconstruction. Its training-fitted normalization, weights, full checkpoint history, source hashes and GPU runtime are preserved in `outputs_planar_neural_v4/`. Frozen earlier experiments remain unchanged. Scripts preserve selected runs and refuse to overwrite them.

```powershell
python test_ronin_experiment.py
python test_skid_experiment.py
python test_planar_experiment.py
python test_planar_neural_experiment.py
```

Acquisition firmware/units, marker and sensor geometry, synchronization uncertainty, and independent reference uncertainty must be established before pursuing a millimeter accuracy claim. The oracle diagnostic's submillimeter reference integration error is a numerical consistency check, not achieved IMU accuracy.

## Synchronization refinement (v5)

Run `python synchronization_experiment.py` to build a separate development experiment. It refuses to overwrite `outputs_synchronization_v5/`. After the frozen coarse peak alignment passes, the experiment searches its local basin at 1 ms and then 0.1 ms using native-rate correlation on identical valid samples. It retains the existing peak, correlation and ambiguity gates; position RMSE never selects a lag. The experiment uses only the parent's accepted training/validation recordings and does not revisit exclusions.

On the same 72 validation recordings/four participants, the frozen planar neural model changes from 368.499 to 366.248 mm RMSE (0.61% improvement); three participants improve and one worsens. Frozen TCN changes from 374.739 to 372.276 mm. The physics baseline refitted on 477 refined training recordings changes from 468.933 to 465.705 mm. Original alignment scores reproduce the parent results. No test signals were opened and neural models were not retrained. The report and per-recording alignment diagnostics are in `outputs_synchronization_v5/`.

This local lag resolution does not establish synchronization accuracy or correct residual clock drift. The original pipeline/configuration and evaluated experiments stay frozen; the new script supplies the refinement settings explicitly in its versioned preparation configuration. Actual acceleration range remains researcher-confirmed +/-2 g and CSV encoding remains unverified.

## Planar retraining on refined labels (v6)

`python refined_training_experiment.py` retrains the planar residual using the frozen v5 synchronization caches and refuses to overwrite `outputs_refined_training_v6/`. Feature normalization, target scales and clipping bounds are fitted from refined training recordings only. The inherited TCN and physical calibration stay frozen. The run uses CUDA, the same architecture and a fixed 12 epochs; validation selects checkpoint and gain from 0.25/0.5/1.0. Known participant groups have equal sampling weight; older unidentified participants are grouped by date.

The best retrained checkpoint (epoch 7, gain 0.5) scores 366.318 mm versus the reproduced frozen model's 366.248 mm on the same 72 validation recordings/four participants. The frozen model remains selected. Two participants improve and two worsen; OS/PS errors remain around 1.6 m. This single-seed experiment does not establish an improvement or statistical significance. All 477 refined training recordings and 3,641 eligible windows are used; no test signals are opened. Results, checkpoint, normalization, history, hashes and participant/maneuver comparisons are preserved in `outputs_refined_training_v6/`.

## Observed-reference validity correction (v7)

The former reader accepted zero C3D residuals, including generated leading coordinates with false initial headings. The C3D format marks these as processed points. Across 646 readable training/validation C3Ds, zero residuals exactly match missing camera support. `observed_reference_experiment.py` corrects the rule before reference filtering, requires positive residuals and camera support when the export populates it, and initializes from the first observed synchronized pose. Later reference gaps remain masked and never reset reconstruction.

The controlled correction uses fixed v5 clock alignment and unchanged neural weights. On identical observed frames from 71 validation recordings/four participants, the old reconstruction scores 373.243 mm and corrected initialization scores 118.490 mm. OS changes from 1,574.721 to 109.488 mm; PS from 1,920.428 to 193.911 mm. This is a reference/initialization protocol correction, not improved neural accuracy on the old full-duration benchmark. Four training recordings and one validation recording lack sufficient observed data, leaving 473/477 training and 71/72 validation recordings from the parent's accepted set. See `qc.csv` for duration/heading changes and exclusions. No test signals are opened.

The new reader and output are separately versioned; the original pipeline, sources, results and historic test locks are preserved. Results are in `outputs_observed_reference_v7/report.md`; observation support is audited in `outputs_reference_support_audit_v7/`. Do not use the earlier full-duration RMSE as verified accuracy against original MoCap measurements. Independent optical uncertainty, CSV encoding and clock accuracy remain unresolved. ADR 0003 records the rule and coverage implications.

## Observed-reference model comparisons and corrected trajectories (v8)

On the same corrected 71 validation recordings, a 12-epoch retraining run scores 117.791 mm versus 118.490 mm for the corrected frozen planar model. A training-fitted group-balanced ridge residual over that frozen model scores 116.898 mm (alpha 0.1, gain 0.25), the best of these candidates. All four participant averages improve with the ridge residual, although PS and 10x5 condition averages worsen slightly. These additional model gains are small; the substantial recovery comes from correcting reference validity and initialization.

The report and 71 corrected trajectory plots are in `outputs_reference_recovery_v8/`; `before_after.png` shows the same previously failing OS/PS recordings on identical observed score frames. `observed_ridge_inference.load_observed_ridge()` loads the selected IMU motion predictor, with sealed dependencies and no reference feature access. It outputs forward/lateral/yaw motion; integration still receives one observed initial pose. Models retain 1.28 seconds of future IMU context and inherited v5 clock mapping. Results remain exploratory, not millimeter accuracy or a new blind test. The runner/weights are in `observed_ridge_experiment.py` and `outputs_observed_ridge_v8/`; the independent neural retraining is in `observed_training_experiment.py` and `outputs_observed_training_v8/`.

## Limits to state in the paper

The researcher confirms accelerometer +/-2 g and gyro +/-2000 degrees/s. CSV integer encoding remains unknown; conversion is empirical and must not be described as verified factory scaling. Legacy scale/delay values in the YAML are not used. Geometry starts from configured values, including radius 0.30 m, hub distance 0.52 m, and symmetric reflector offsets 0.066 m.

The reference currently projects onto C3D XY. Confirm the acquisition's Z-up coordinate convention before publication. With symmetric outboard markers and zero camber, their midpoint supplies the hub midpoint. More complex geometry requires additional acquisition evidence.

Reported accuracy is conditional on accepted synchronization/reference quality. Always publish attempted counts, exclusion reasons, reference/reconstruction coverage, and participant-level results alongside averages. Validation results guide development and are not final test performance. Architecture and tuning budget can be revisited using validation only, before opening final test data.

The agreed design and terminology are in `docs/design.md`, `docs/adr/`, and `docs/GLOSSARY.md`.

## Observed-reference improvement build (v9)

`long_horizon_experiment.py` compares the same residual network with short loss and observed endpoint SE(2) losses at 1/3/5/10 seconds. Three predefined seeds use a training participant fold for epoch/gain selection, then refit all training recordings before final validation. The inherited TCN/calibration saw the inner fold previously, so this is conditional selection, not independent whole-pipeline evaluation. Short recordings use supported horizons; empty beyond-record contexts are excluded from BatchNorm. Optical gaps need no invented intermediate poses. Incomplete attempts and their executed sources are preserved.

On identical 71-recording observed validation support, the endpoint ensemble scores 114.057 mm versus the existing ridge's 116.898 mm, but SL worsens from 145.482 to 147.682 mm and two participant averages regress. Endpoint individual seeds score 118.247/123.002/142.175 mm; matched short-loss seeds score 118.870/157.649/138.503 mm. Retain the existing ridge. The preselected endpoint seed 43 scores 123.002 mm overall and 138.525 mm on SL; its selection predates validation.

`observed_sync_experiment.py` rebuilds clocks using observed-only optical features and train-only bootstrap calibration. On a separate paired native timestamp benchmark, ridge scores 116.823 → 116.508 mm, with one participant worsening. Accepted coverage is 465 training/71 validation. `physics_state_experiment.py` implements a bounded empirical yaw-bias comparator; it scores 230.680 mm versus static empirical physics 222.128 mm and does not justify fusion. Unverified sensor encoding/mounts prevent claiming full calibrated attitude INS.

Reports and comparison tables: `outputs_build_v9/report.md`. All twelve paired SL plots and drift/turn/straight diagnostics: `outputs_build_trajectories_v9/`. Build record and audit: `docs/build-v9.md`, `docs/build-v9-audit.md`. Six checkpoints and all seed histories: `outputs_long_horizon_v9/`. `long_horizon_inference.load_endpoint_ensemble()` supplies an IMU-only candidate predictor; the current ridge loader stays selected. No test signals were reopened; below-100 mm overall/SL and global millimeter accuracy remain unproven.

## All trajectories, image diagnosis and correction comparisons (v10–v11)

`outputs_trajectory_report_v10/gallery.html` contains all 71 accepted validation trajectories, with reference, ridge, endpoint ensemble and training-fitted calibration comparison. The folder includes a 71-page PDF, seven maneuver overview sheets, individual trajectory/position/heading panels, cached trajectories, CSV metrics and SHA256 manifests. Plot legends and missing-recording labels were corrected after visual review. Thirteen planned repetitions remain unaccepted; coverage is only 3 OS and 8 PS recordings.

`research_docs/trajectory-findings-v10.md` gives the primary-source method review and image findings: late SL yaw drift, unresolved physical-left/right or initial-heading ambiguity in No.5 AR2/3, genuine near-in-place CR motion, and persistent PS braking displacement loss. Calibration scores 116.255 mm overall / 140.446 mm SL, but worsens PS, OS and one participant, so ridge stays selected. The v11 acceleration smoother failed all 24 nonzero training-fold candidates; its best rejected full-training refit scores 116.918 mm, versus ridge 116.898 mm. Reports, coefficients and braking plots are preserved in `outputs_chassis_acceleration_v11/` and `outputs_chassis_acceleration_v11_rejected_comparator/`. These are exploratory validation comparisons, not final test results or evidence of millimeter accuracy.

## Completed trajectory improvement loop (v12–v24)

The measured exploratory minimum is v21: 102.585 mm overall and 122.943 mm SL, versus paired CPU ridge 116.899/145.487 mm (12.24% overall improvement). All participant and maneuver means improve, but individual failures remain, especially No.14 SL and No.18 PS braking. The v24 conservative three-fold candidate scores 108.950 mm overall /131.316 mm SL. Its training selection covers all twelve target training participants and passes a <=5% worst-person guard; v21 does not pass that broader guard. Use v24 for a separately frozen next evaluation; retain v21 as the exploratory minimum-error comparator.

Best measured plots, all 71 cases: `outputs_trajectory_best_v21/gallery.html` and `all_71_trajectories.pdf`. Final findings: `research_docs/trajectory-loop-findings.md`; experiment journal/epoch chart: `outputs_trajectory_loop/`; independent exact reproduction and reference-poison audit: `research_docs/trajectory-loop-audit.md`. More epochs, iterative endpoint refinement, channel blending and stronger endpoint weighting did not establish consistent improvement. All failed comparisons and executed sources remain preserved.

Inference: `nonlinear_endpoint_inference_v21.load_nonlinear_endpoint()` for the exploratory minimum; `participant_folds_inference_v24.load_participant_folds()` for the guarded alternative. Both are CPU predictors using only IMU and optional IMU startup initialization, returning forward/lateral/yaw motion. Supply the initial pose separately to `integrate_planar`; neither uses later optical poses. Most target recordings lack stationary startup. Sensor integer encoding and full mounting geometry remain unverified. No test acquisitions were reopened in this loop; reused validation is not a blind final test. Original frozen pipeline and model artifacts remain unchanged.

## 10 October 2026: maneuver minima checked on matched support (v115-v116)

The retained best method remains v34 (100.702119399 mm synchronized XY ATE;
49.726226563 mm route RMSE), using the methodology documented above. No new
method was promoted. Independent review completed v112 source interpretation,
v113 fixed-reference bound and v114 retrospective uncertainty without substantive
defect. The four-person benefit interval includes zero; no significant gain claim.

For the user's requested cherry-picking, v115 uses only sealed previously exposed
trial summaries for six common-native v42 models. Outcome-informed maneuver
switching gives 94.462747445 mm versus 94.661739566 mm for the fixed refit blend:
only 0.198992121 mm lower. This is retrospective descriptive arithmetic, not a
trained/deployed selector. The common-support control is 100.592598441 mm;
these numbers must not be substituted into the original v34 evaluation.

v116 independently reconstructs all seven broad historical minima from trial
summaries. The AR winner's whole-model error is 142.175376 mm, CR's 116.878910 mm,
and OS's 233.620690 mm. OS has only three trials/two people. Other clock/support
variants also differ. Do not combine these minima into a claimed overall score.
See research_docs/matched_maneuver_results_v115.md and
research_docs/maneuver_minima_results_v116.md for exact scope and source evidence.

Native Goal query now returns no attached Goal; ordinary usage is allowed. This
supersedes the earlier usageLimited checkpoint without claiming the old Goal
resumed. The strict all207 timing/reference gate remains unresolved: six fixed
reference blockers bound IMU-only recovery at201/207. New predictor/comparator
fitting still requires independent timing evidence or an authorized clock-contract
revision; completed projection/peak/gate searches should not be repeated.

Independent v116 review also passed: fifteen input hashes, both output hashes, all seven scores, recording identities, method filters and frame-count differences verified.

## 11 October 2026: independent timing metadata route checked (v117-v118)

Two reviewed audits checked the eight rejected TRAIN C3D headers/parameters and
first IMU CSV timing rows. The C3D event slots are blank zero-time padding;
analog labels describe force/moment channels. Creation strings and 0/1 frame
index conventions do not establish correspondence to device/PC-monotonic clocks.
No independent mapping was established. Analog waveforms and unlabeled pulses
were not tested. Source files remained immutable; no validation/test or fit.

Retained v34 remains the best retained method under its original evaluation:
100.702119399 mm XY ATE / 49.726226563 mm route. Its exact methodology above
is unchanged; no accuracy improvement is claimed from metadata checks. Both
new audits passed independent review. See research_docs/reference_timing_results_v117_v118.md.
The user subsequently authorized the bounded TRAIN-only exception in
research_docs/proposed_train_only_exception_2026-10-11.md. The v119 preregistration
allocates its one-family/max3 configuration budget; the strict timing gate remains.


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

TRAIN guard-selected delta: 0. This is not promotion.

Method: unchanged causal v56 hysteresis features; residual relative to frozen
v52 speed/projected-yaw baseline; TRAIN-fitting group-balanced normalization;
fixed centered target MAD scales, ridge1, eight shared two-component Huber IRLS
updates, delta1.5/3/6 only; correction caps0.1m/s and0.05rad/s, fixed gain0.25.
Held participants excluded from every residual fit and normalization. All four
motions/positions/headings saved per recording for exact support review.

Acceptance requires lower overall ATE and <=1.05 for every person/maneuver,
overall trial P95position, last-supported endpoint and heading. All207 must
remain represented. Missing support is never dropped or assigned a score.

## Guard details

Delta1.5: Position_P95_mm ratio=0.970796; Last_Supported_Endpoint_Error_mm ratio=0.969024; heading_rmse_deg ratio=0.992406
Person/maneuver violations: ST=1.126090
Delta3: Position_P95_mm ratio=0.968402; Last_Supported_Endpoint_Error_mm ratio=0.967943; heading_rmse_deg ratio=0.992410
Person/maneuver violations: ST=1.148412
Delta6: Position_P95_mm ratio=0.968665; Last_Supported_Endpoint_Error_mm ratio=0.968166; heading_rmse_deg ratio=0.994454
Person/maneuver violations: ST=1.180894

## Every maneuver on identical TRAIN support

| Maneuver | Baseline (mm) | Delta1.5 (mm) | Delta3 (mm) | Delta6 (mm) |
| --- | ---: | ---: | ---: | ---: |
| 10x5 | 289.927042 | 282.529849 | 282.358034 | 282.838366 |
| AR | 85.954470 | 81.708057 | 81.334544 | 81.116221 |
| CR | 47.178747 | 44.455737 | 44.297664 | 44.252243 |
| OS | 123.811474 | 106.498545 | 103.924458 | 101.304157 |
| PS | 204.147641 | 200.700965 | 199.978210 | 198.955438 |
| SL | 206.667073 | 196.068346 | 194.408784 | 193.844205 |
| ST | 81.831921 | 92.150138 | 93.976789 | 96.634818 |

Inherited optical crop/initial pose/clocks and offline projected gravity
proxy remain; this does not resolve the strict all207 timing gate or demonstrate
true attitude, genuine acquisition endpoints or deployment generalization.
Retained historical v34 best remains100.702119399mmATE/49.726226563mmroute on
its separate already-exposed validation evaluation. Do not compare that number
directly with this207 TRAIN-fold mean or treat TRAIN selection as validation.

Independent final review passed: all hashes,207 prediction files/828 unique rows,
exact masks/primary guards and eligibility independently reproduced; see
research_state/v119_review.json. Supplementary diagnostics were not all
independently reconstructed. Numeric budget exhausted: no fourth config,
new family, validation scoring or promotion authorized. Next numerical step
requires separate user authorization; strict timing work requires new linked
independent evidence. Completed unsuccessful timing searches should not repeat.


# Conservative robust motion v120: accepted TRAIN development model

New user request on11October2026 authorized renewed model development afterv119.
Selected fixed global gain0.075 of frozen delta3 robust corrections. No maneuver
labels or optical values enter motion inference. This is a verified improving
TRAIN development model in the frozen v52 family, not a demonstrated replacement
for retained v34 on its separate validation evaluation.

| Gain | Equal-person ATE mm | Heading RMSE deg | ST change | Eligible |
| --- | ---: | ---: | ---: | --- |
| 0 | 147.746508 | 1.836665 | +0.000% | True |
| 0.05 | 146.753294 | 1.831167 | +2.718% | True |
| 0.075 | 146.296429 | 1.829010 | +4.128% | True |
| 0.1 | 145.866966 | 1.827184 | +5.569% | False |

## Selected model by maneuver

| Maneuver | Baseline ATE mm | v120 ATE mm | Change |
| --- | ---: | ---: | ---: |
| 10x5 | 289.927042 | 287.160861 | -0.954% |
| AR | 85.954470 | 84.396641 | -1.812% |
| CR | 47.178747 | 46.170594 | -2.137% |
| OS | 123.811474 | 117.164081 | -5.369% |
| PS | 204.147641 | 202.749152 | -0.685% |
| SL | 206.667073 | 202.491672 | -2.020% |
| ST | 81.831921 | 85.209570 | +4.128% |

## How the model was obtained

1. Freeze v52 participant-fold wheel-speed calibration and offline projected-yaw
   baseline, original clocks, optical initialization and scoring support.
2. v119 fits existing causal hysteresis features to forward/yaw residuals using
   shared robust weights, ridge1, eight IRLS updates and TRAIN-only normalization.
   Delta3 had the lowest overall TRAIN score, but gain0.25 failed the ST guard.
3. v120 preregistered only gains0.05/0.075/0.10; retained coefficients/features
   and caps0.1m/s/0.05rad/s. Gain0.075 is the lowest-ATE eligible candidate.
   Gain0.10 fails ST; there is no maneuver-specific selector or retuning.
4. All207 recordings/12people/all15No20 remain present with exact same masks.
   Every person and maneuver stays within5%; overall P95position, last-supported
   endpoint and heading also pass. This is descriptive TRAIN development evidence.
5. Export models/conservative_robust_v120 with exact three research-fold replicas.
   Sensor-only inference reproduces all207 held motions; maximum difference8.88e-16.

Call conservative_robust_inference_v120.load_fold and predict_motion; bundle
README/model_card document inputs and scope. It is not a full-data deployment
refit, and selecting/averaging fold models for a new user has not been evaluated.

Independent review: passed; see research_state/v120_review.json.
No new validation/test scoring, deployment, commit or push. Retained historical
v34 remains100.702119399mmATE/49.726226563mmroute on71 exposed validation trials.
The all207 independent-clock gate remains unresolved; inherited calibration,
crop and offline filter dependencies remain. No significance/superiority claim.

Next: further development is authorized by the latest user request; do not
repeat completed v119/v120 grids. Preserve the selected model and exact guards.
A validation comparison or full-data deployment milestone requires an explicit
evaluation decision consistent with prior no-validation/no-promotion scope.


# v121: nonlinear temporal model beats the strongest retained TRAIN baseline

Frozen v34 matched TRAIN ATE132.240200mm ->129.739811mm (1.89% lower).
All207 recordings/12people/all15No20 retained; every original guard passes.
This is a measured improvement, not a claim of groundbreaking performance or
universal superiority. No new validation/test evaluation has been performed.

| Penalty | Equal-person ATE mm | Heading RMSE deg | Worst person ratio | Eligible |
| --- | ---: | ---: | ---: | --- |
| 0 | 132.240200 | 2.083097 | 1.000000 | True |
| 0.1 | 131.913282 | 2.278375 | 1.573990 | False |
| 1 | 127.490837 | 2.019101 | 1.118657 | False |
| 10 | 129.739811 | 2.044960 | 1.033559 | True |

Penalty1 obtains127.490837mm but fails participant guards; it is rejected.
Selected penalty10 worstperson+3.356%, worstmaneuver+0.264%; P95position
ratio0.981494, last-supportedendpoint0.980206, heading0.981692.

| Maneuver | Matched v34 ATE mm | v121 ATE mm | Change |
| --- | ---: | ---: | ---: |
| 10x5 | 213.012753 | 200.952444 | -5.662% |
| AR | 82.337381 | 81.279294 | -1.285% |
| CR | 48.908680 | 47.861096 | -2.142% |
| OS | 172.261638 | 165.829649 | -3.734% |
| PS | 212.642211 | 212.649340 | +0.003% |
| SL | 183.757434 | 184.242203 | +0.264% |
| ST | 81.643976 | 80.007338 | -2.005% |

## Method and route to this result

v119/v120 improved a weaker physics baseline. The new comparison directly
reproduces the retained v34 weight0.75 model, all207 exact historical scores
and support counts before scoring candidates. Frozen parent models preserve
their inherited266 additional training-record dependence; new residual fitting
uses only identified TRAIN people, excluding each held participant fold.

A fixed16-state leaky tanh recurrent reservoir encodes central gravity-rotation
IMU features, with fit-only normalization and seeded fixed recurrent weights.
A joint forward/yaw readout is optimized against exact accumulated XY/heading
trajectory error. Eight analytic GaussNewton steps with fitting-only line search
replace short-interval/derivative-only objectives. Caps.05m/s and.02rad/s,
three preregistered ridge penalties.1/1/10; no maneuver labels or identity at
inference. Optical labels are used only for fitting and evaluation.

Independent reviewer checked all34 Jacobian columns (maxerror9.04e-10),
all207x4 trajectory support/core metrics, fitting exclusions and hashes. All
candidate predictions and perperson/maneuver results are preserved. See
research_state/v121_review.json and v121_preparation_notes.md for audit and
the two preserved pre-fit path/manifest lookup failures.

## Actual model artifact

models/reservoir_path_v121_completed contains the full-TRAIN readout fit at selected
penalty10 on all207 identified records, with the frozen full v34 parent.
Use reservoir_inference_v121.load_reservoir_model()(sensor). Startup IMU
initialization is supplied or computed from original startup history; an
optical initial pose is supplied separately only for integration.
Full TRAIN inference reproduction: 207 recordings; maximum motion difference0.
Optical/identity-field poisoning leaves inference unchanged. These package
reproduction checks are not held-out accuracy measurements.

## Package completion and provenance repair

The first package attempt saved the full-TRAIN coefficients, then stopped at
a strict legacy pipeline hash check. Only sensor metadata and report prose
had changed; numerical pipeline functions were unchanged. The incomplete
models/reservoir_path_v121 bundle and original source copies remain preserved.
Completion reused its coefficients and normalization without another fit.
Two exact reviewed provenance transitions allow the corrected pipeline and
the verification-only ridge loader edit. Other hashes still fail closed;
historical manifests were not rewritten. New dependencies are sealed.
All207 sensor-only predictions and per-record optical/identity poisoning
checks pass. See research_state/v121_package_review.json for package review.

## Comparison scope and next evaluation

Recorded inventory:125 complete207-ID historical candidate groups,116 with
v34 frame counts. New selected score is below their recorded means, including
rejected v33tilt0.3 at131.460088mm. Exact paired baseline support is verified
for v34; equal counts alone do not prove every historical mask/time mapping.
See research_state/v121_comparator_inventory.json for all paths/hashes/groups.

v34 historical validation remains100.702119399mm on71 exposed recordings.
Do not compare that directly to129.739811 TRAIN. Candidate is frozen and ready
for one explicitly authorized matched validation comparison, with no retuning
or reserved-test use. No promotion/commit/push occurred. Independent clocks
remain unresolved; offline/future-context/crop/calibration inheritance persists.
