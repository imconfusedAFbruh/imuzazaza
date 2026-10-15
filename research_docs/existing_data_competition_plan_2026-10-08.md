# Existing-Data-Only Wheelchair IMU Research Implementation Plan

> For agentic workers: implement task-by-task using superpowers:executing-plans or superpowers:subagent-driven-development when available. Use the local project's instructions. Review each evidence gate before advancing. This is a research plan, not a promise of a winning result.

**Goal:** Determine whether an IMU-only wheelchair trajectory estimator can outperform faithfully reproduced relevant methods on the same existing recordings, without additional acquisition, extra sensors, test-set tuning, or easier evaluation.

**Architecture:** First reproduce the current pipeline and establish data/calibration/evaluation provenance. Then use training-only error-isolation experiments to choose between calibration repair, local motion residual learning, and uncertainty-aware fusion. Keep the simplest method that passes the predeclared comparisons; do not build every proposed component automatically.

**Tech stack:** Reuse the verified local Python, numerical, ML, C3D and plotting environment. Reuse current integrations, loaders and tests. Do not replace the stack or add a heavyweight optimization framework until a measured need exists.

**Spec:** The user's constraints, the uploaded `trajectory_research_accuracy_audit(1).pdf` (revised 5 October 2026), verified local continuation records, and the primary research references below. Local later evidence supersedes the PDF only with identifiable artifacts and reproducible commands.

## 1. Non-negotiable constraints

- Three available sensor roles: left-wheel IMU, right-wheel IMU, and frame/center IMU. There are NO physical wheel encoders.
- No new participants, measurements, calibration sessions or sensor purchases. Do not make progress depend on new acquisition, cameras at inference, GNSS, UWB, LiDAR, or additional markers.
- Existing optical C3D data may supply training targets and offline evaluation. Preserve the existing allowance for one optical initial position and heading. Do not supply later optical motion to the estimator.
- Use only existing, accessible recordings. Historical two-IMU recordings may be useful, but their roles, labels, provenance and previous inclusion are not yet established by this plan.
- Preserve the raw acquisitions, historical predictions, failed experiments, manifests and prior reports. Never overwrite the retained method with an unpromoted result.
- Do not optimize clock lag, sign, rotation, scale, reflection, endpoint or route correspondence against a scored trajectory.
- No future optical resets, known-route snapping, assumed loop closures, known 5 m distances as inference inputs, or per-trial ground-truth calibration.
- No training, normalization, self-supervised pretraining or early stopping on reserved evaluation participants in an inductive experiment.
- This is primarily offline reconstruction. Report noncausal filtering/future context honestly and distinguish it from a causal deployment result.
- A lower RMSE on a different mask, initial pose, clock convention or participant weighting is not an improvement claim.

## 2. Source-grounded starting point

The uploaded audit documents the following, not necessarily the latest local state:

| Item | Audit evidence |
|---|---|
| Training | 473 recordings: 266 earlier plus 207 target-training recordings |
| Target-training people | No.1/3/4/6/7/8/13/15/16/17/19/20 |
| Validation | No.5/10/14/18; 71 accepted recordings |
| Reserved test | No.2/9/11/12; not accessed during that audit window, but historical exposure is acknowledged |
| Retained candidate | 100.702 mm synchronized 2D RMSE on its documented own-clock evaluation |
| Matched native-common comparison | Old blend 100.593 mm versus signal-arbitrated refit 94.662 mm |
| Refit status | Not promoted: No.8 regressed 5.80%, exceeding the frozen 5% training-participant guard |
| Retained route RMSE | 49.726 mm; a different quantity from synchronized position RMSE |
| Fold limitation | Correction folds excluded held participants, but inherited calibration/base had already seen them |
| Historical identity limitation | Earlier trial-to-person mapping is incomplete |

References: uploaded audit pp. 1-3, 7-10. The atlas primarily illustrates the unpromoted refit, not the retained candidate. Do not mix their figures and headline numbers.

The primary score is the arithmetic mean of participant means of trial RMSEs, not pooled-frame RMSE:

`score = mean_over_people(mean_over_trials(sqrt(mean_over_supported_frames(||p_pred - p_ref||^2)))))`.

The 473 recordings are NOT established to come from only 12 people. Twelve is the number of identified target-training participants; the earlier recordings have incomplete identity provenance.

## 3. Primary research references and comparison rules

1. Van der Slikke et al. (2015), *Opportunities for measuring wheelchair kinematics in match settings; reliability of a three inertial sensor configuration*. DOI: `10.1016/j.jbiomech.2015.06.001`.
   https://pubmed.ncbi.nlm.nih.gov/26141162/
   Three IMUs and optical reference. The abstract reports frame-displacement RMSE at or below 0.05 m except for three vigorous tests. This does not establish equivalence to our full synchronized 2D position score.
2. Van der Slikke et al. (2015), *Wheel Skid Correction is a Prerequisite to Reliably Measure Wheelchair Sports Kinematics Based on Inertial Sensors*. DOI: `10.1016/j.proeng.2015.07.201`.
   https://www.sciencedirect.com/science/article/pii/S1877705815014502
   Algorithm source for the related skid-correction approach. Treat these two papers as related evidence, not two independent replications.
3. Wu, Kuang and Niu, *Wheel-INS2: Multiple MEMS IMU-Based Dead Reckoning System With Different Configurations for Wheeled Robots*. DOI: `10.1109/TITS.2022.3220508`.
   https://arxiv.org/abs/2012.10593
   https://arxiv.org/pdf/2012.10593
   Multi-IMU constraints and body/wheel configurations. Published drift percentages are not interchangeable with millimeter trajectory RMSE. Its original Wheel-INS companion implementation is at https://github.com/i2Nav-WHU/Wheel-INS . Do not label that single-wheel code as an official Wheel-INS2 implementation. Check licensing and mounting assumptions before reuse.
4. Liu et al. (2020), *TLIO: Tight Learned Inertial Odometry*. DOI: `10.1109/LRA.2020.3007421`.
   https://arxiv.org/abs/2007.01867
   https://arxiv.org/pdf/2007.01867
   Methodological reference for learned local displacement and uncertainty in an estimator. Its pedestrian results/weights are not wheelchair benchmarks.
5. Pinnock Branford (2026), *Multi-Sensor Fusion for Manual Wheelchair State Estimation*.
   https://researchrepository.wvu.edu/etd/13492/
   An MS project report, not a peer-reviewed journal article. It reports four IMUs and indoor 2D position RMSE as low as 0.116 m for a repeated-turning trial. That best-case number cannot be ranked directly against a multi-participant aggregate.

Create a source matrix recording metric formula, dimension, reference point, alignment, filtering, trial duration, path length, averaging, sensor placement, initial-pose use and test independence. Missing information must remain marked unverified. Obtain full methods before claiming a faithful implementation. An incomplete implementation must be called an adaptation.

**Winning criterion:** beat the strongest relevant reproduced baseline on the SAME data under a locked protocol, with credible paired improvements and no hidden coverage or failure-rate tradeoff. A 20% relative reduction is an ambitious development objective, not an observed result or publication threshold. Absolute 50 mm and 30 mm are exploratory goals, not promised endpoints.

## 4. Workspace, artifacts and interfaces

First inspect the active workspace. A previously identified recovered research location is:

`C:\Users\poon1\Desktop\kight_recover`

The older location `D:\project\WheelAthelse` may contain the acquisition repository/audit rather than the current research project. Verify using actual files and continuation records. Do not silently work in the wrong copy. The public acquisition source is https://github.com/NnopponS/WheelAthelse . Its production application model is not automatically the three-IMU research model.

Read, in order:

- Local `AGENTS.md` and workspace instructions.
- `research_state/NEXT_SESSION.md`, `STATUS.md`, `TODO.md`, `BEST_RESULTS.md`, `EXPERIMENTS.md`, `FAILED_IDEAS.md`.
- The latest audit and any later acquisition, timebase, calibration, loader and full-fold reports. Inspect `research_docs/sensor_timebase_v46.md` if present; do not assume v44 is latest.
- The October 5 firmware/receiver audit and any successor. The older known audit path is `D:\project\WheelAthelse\.project\local\firmware_receiver_audit_2026-10-05.md`; use its provenance carefully if it concerns a different workspace/data set.

Use existing source modules after mapping their actual paths. Do not invent existing entrypoints. Add proposed documentation/artifacts under:

- `research_docs/existing_data_competition_plan_2026-10-08.md`
- `research_docs/competition_source_matrix.md`
- `research_docs/experiment_preregistration.md`
- `research_docs/acquisition_conversion_contract.md`
- `research_docs/error_isolation_report.md`
- `research_docs/final_same_data_comparison.md`
- A new, versioned experiment-output directory containing manifests, configurations, predictions, metrics and logs.

Define boundaries in the local implementation map:

1. **Acquisition loader:** raw arrays, native device timestamps, sensor role, unit conversion provenance and validity; no optical features.
2. **Fold fitter:** training IDs/configuration -> calibration, normalization, models and hashes, with fitted-ID provenance on every artifact.
3. **Motion predictor:** IMU data plus permitted setup metadata -> timestamped local motion/uncertainty; no reference input.
4. **Pose integrator:** motion, one initial pose -> continuous predicted pose on valid IMU support; no reference resets.
5. **Evaluator:** predictions, immutable reference, locked clock mapping and mask -> metrics and coverage.
6. **Diagnostic oracle:** an explicitly separate development-only program; cannot be imported by the production predictor.

## 5. Review focus: mistakes that must have tests

1. A mask, interpolation gap or reinitialization makes a candidate appear more accurate by scoring less data.
2. Fitted calibration, cached targets, normalization, pseudo-labels or overlapping windows cross participant partitions.
3. A gyro metadata issue is corrected twice because the numerical loader already used the proper raw-count conversion.
4. Missing center-IMU data is mistaken for a measured zero signal, or historical recordings are counted twice.
5. A rigid-wheel, no-slip or slope assumption silently creates optical-looking motion that was not observable from the IMUs.

## Phase 0 - Reproduce and inventory before changing research

**Inputs:** existing continuation records, artifacts and acquisitions. **Outputs:** resolved workspace map, reproduction log, hashed data manifest, completed-work ledger.

- [ ] Resolve the actual workspace and list completed, failed, pending and genuinely blocked tasks.
- [ ] Reproduce the retained model and latest unpromoted model with their own original definitions. If reproduction fails, diagnose it before comparing improvements.
- [ ] Record participant/session/setup IDs, sensor roles, raw-file hashes, C3D pairs, label support, clock lineage and software/firmware evidence per acquisition.
- [ ] Identify which old two-IMU recordings are already among the 266 earlier recordings. Deduplicate by acquisition identity, not just filename.
- [ ] Never infer the identity of the missing sensor. Inspect whether the pair is L/R, L/C, R/C or another arrangement.
- [ ] Archive original configurations and predictions; create a separate continuation branch/output area without destructive cleanup or an unsolicited remote push.

**Gate:** reproduce documented controls or produce a concrete discrepancy report. No new-model gain is credible before this gate.

## Phase 1 - Lock honest comparison tracks

**Outputs:** exposure ledger, immutable splits, preregistration, fixed metric/coverage contract.

Maintain TWO tracks:

**Historical continuation:** preserve the 473/71 benchmark and retained artifacts for continuity. State inherited calibration and historical exposure limitations.

**Strict provenance track:** exclude a held participant from every fitted stage. Include legacy data only when participant overlap can be ruled out. Quarantine unknown-identity legacy recordings from this track, including self-supervised pretraining. Keep them in a separately labelled exploratory legacy-data experiment rather than deleting them.

- [ ] Use grouped inner folds within training data for selection. Begin with the existing three groups if their identities are verifiable, but refit every learned stage.
- [ ] For final development estimates, run nested participant-held-out evaluation for the selected shortlist. Declare the folds, seeds and search space before scoring them.
- [ ] Refitting folds now does NOT erase previous human/model-design exposure. Label the work retrospective.
- [ ] Keep No.2/9/11/12 or the latest manifest's reserved test group closed until the method and reporting rules are frozen. Do not replace the current participant manifest with the stale Sep 9/Sep 11 date-only split.
- [ ] Freeze equal-participant weighting, reference semantics, common initial pose, masks, filters and failure handling for each comparison.
- [ ] Define a bounded budget: at most eight new hypothesis families initially; at most three prespecified tuning configurations per family. Screen on training folds; confirm finalists across at least three seeds. Extend the budget only with an explicit, logged justification before more experiments, never because test results disappoint.

**Gate:** automated ID/provenance checks pass, and all methods in a comparison can be scored on identical reference support.

## Phase 2 - Finish only unresolved acquisition and calibration checks

**Outputs:** conversion contract, unit/timing tests, calibration identifiability report.

- [ ] Trace raw sensor counts -> firmware packet -> receiver/journal -> export -> research loader for actual recorded examples.
- [ ] Determine the acquisition-era configuration from available evidence; current repository defaults or release dates are not proof.
- [ ] Explicitly test whether an advertised gyro-scale discrepancy changes the numbers used by the model. The loader may already use the proper sensitivity. Do not automatically multiply gyro by approximately 1.147 or reuse a historical learned gain after changing units.
- [ ] Audit timer wrapping, packet-tail versus per-sample timestamps, batching, device/receiver mapping, loss, saturation and duplicate samples. Reuse completed timebase tests.
- [ ] Keep device-to-receiver clock reconstruction separate from C3D-to-recording alignment. Lock an evaluator-only motion-signal alignment procedure; never choose lag by localization RMSE.
- [ ] Check repeated-cycle aliases using distributed signed motion/events and common support. Preserve explicit ambiguous-alignment fallbacks and quantify sensitivity.
- [ ] Estimate only calibration components supported by existing data. Distinguish scale, bias, axis direction, axle sign, wheel phase, lever arm, effective radius and body attitude. Document confounding and fit conditioning.
- [ ] The audit's two axle markers provide midpoint and axle direction, not full body pitch/roll. Do not invent full-attitude optical labels.
- [ ] Do not assume every trial starts stationary. The report found only 1/207 target-training and 1/71 validation recordings satisfied the strict initial 5 s quiet gate. Handle initialization uncertainty explicitly without a test-ID exception.
- [ ] Do not reinterpret jointly fitted midpoint-speed coefficients as separately calibrated physical wheel rates. The audit already rejected that substitution.

**Tests:** signed-int decoding, scale round trip, timestamp wraps/batches, sensor-role swap, unit perturbation, no-double-correction and calibration-fit-ID assertions.

**Gate:** a reproducible input contract. If a calibration component is unidentifiable, retain a labelled empirical treatment and sensitivity range rather than blocking every subsequent experiment or claiming it is physically calibrated.

## Phase 3 - Find where improvements are actually available

**Outputs:** training-only error-isolation tables and ranked hypotheses.

This is the first new experiment I would prioritize after reproduction. Use directly observed C3D targets and training-only out-of-fold predictions to answer: is the dominant error travel, heading, lateral motion, synchronization, or reference/frame interpretation?

- [ ] Decompose synchronized position error into along-track and cross-track components in the reference heading frame, where that heading is valid.
- [ ] Report per-person/per-maneuver errors, speed/turn/braking dependence, error versus time and distance, and endpoint deficits.
- [ ] Run diagnostic substitutions: predicted local velocity with reference heading; reference local velocity with predicted heading; reference velocity and heading as a numerical integration check. Add a lateral-motion substitution only where reference support supports it.
- [ ] Keep substitutions OUT of final inference and validation/model selection. They are non-deployable diagnostics, not achieved accuracy or guaranteed error bounds. Components interact and their improvements are not additive.
- [ ] Repeat timing diagnostics using locked signal evidence, not an RMSE-minimizing time warp.
- [ ] Investigate the failed No.8 training-fold case. Investigate previously exposed validation failures descriptively, but derive and select any repair on training analogues, never on a participant-ID rule.
- [ ] Check initial-front/axis semantics for opposed-route errors. Do not fix them by choosing the sign that best fits the scored trajectory.

The audit's page 22 shows a particularly informative pattern: heading curves can look close while spatial paths disagree. Conversely, a small global heading RMSE does not show that heading contributed little to position drift. Use the substitutions to test, not guess.

**Gate:** choose the next component from measured training-side evidence. If travel, heading or calibration dominates, prioritize that branch rather than building an all-purpose large network.

## Phase 4 - Construct strong, fair competitor baselines

**Outputs:** source-linked baseline implementations, unit tests, matched-data results.

Mandatory comparisons:

- **B0:** retained current research method, unchanged, plus a separately labelled full-fold refit.
- **B1:** calibrated wheel-IMU rolling kinematics with frame gyro heading; explicitly conditional on its rolling/attitude assumptions.
- **B2:** Van der Slikke-style three-IMU skid correction, with each implemented equation, filter and threshold tied to full-method evidence.

Additional strong baseline when feasible:

- **B3:** Wheel-INS-family estimator, using official available code or a documented adaptation. Do not mislabel Wheel-INS as Wheel-INS2, silently assume constant off-axis wheel-sensor lever arms, or force flat-ground assumptions onto slope trials without disclosure.

- [ ] Report published-parameter and training-tuned variants separately where appropriate. Give competitor methods a fair tuning budget, initialization and timing treatment.
- [ ] Extend a kinematics-only method into trajectory integration using the SAME integration convention, and call that extension an adaptation.
- [ ] Separate matched-front-end algorithm comparisons from end-to-end comparisons that also change calibration/timing.
- [ ] Report causal baselines and offline/smoothed variants distinctly; do not pass a future-looking method off as a real-time superiority result.

**Gate:** do not advance an alleged competitor victory based solely on 50 mm or 116 mm quoted from another data set.

## Phase 5 - Refit the entire inherited pipeline under validated clocks

**Outputs:** matched full-fold experiments, provenance logs, retained/rejected decision.

- [ ] Refit conversion-dependent calibration, normalization, physics coefficients, base network and correction layers inside each training fold.
- [ ] Compare original versus signal-arbitrated clocks with otherwise matched full-pipeline training.
- [ ] Retain the old correction-only refit as a diagnostic control; it is not equivalent to the full refit.
- [ ] Use common native evaluation timestamps/support and a common initial pose for paired comparisons. Apply the same locked alignment procedure to all methods.
- [ ] Enforce the original 5% training-participant regression guard. A No.8-specific exception or threshold change is not an acceptable promotion.

**Gate:** promote a genuine full-pipeline improvement only if the original checks pass. A more rigorous score may initially worsen; do not conceal that or compare it directly with a historically optimistic score.

## Phase 6 - Test ONE compact local-motion correction, not a giant replacement

**Outputs:** small residual model, uncertainty diagnostics, ablation table.

Only proceed if Phases 3-5 leave a learnable residual and the candidate is not a repeat of a documented failed method.

Recommended proposed target for a short interval `[i,j]`:

`d_ij = Rz(-yaw_i) * (p_j - p_i)_horizontal`

`t_ij = [d_forward, d_lateral, delta_yaw]`.

Predict a bounded residual relative to a verified physical baseline, not absolute global XY. A proposed initial window shortlist is 0.25, 0.5 and 1.0 s, selected on training folds. Use the smallest existing TCN/1D network that passes the tests; compare it with a regularized linear residual on the same features.

- [ ] Permit a regularized lateral correction instead of hard-coding zero lateral velocity. Slalom/skidding may violate a perfect no-sideways-motion assumption. Do not assume lateral observability is complete.
- [ ] Inputs may include raw IMUs, calibrated physical features, sensor-availability masks and permitted setup metadata. No participant ID, filename, route length or optical feature is allowed as a shortcut.
- [ ] Generate displacement labels from directly observed endpoints and valid IMU intervals. Interior optical gaps do not authorize invented paths; endpoint-only labels across such gaps must be separately identified. Derivative labels require adequate contiguous optical support.
- [ ] Train bounded local mean corrections first. Add covariance prediction only after the mean model helps; include the full likelihood penalty and eigenvalue bounds to prevent variance inflation.
- [ ] Use out-of-fold residuals for training/calibrating reliability so the model does not learn falsely small in-sample errors.
- [ ] Use equal-participant/controlled-maneuver sampling. Keep overlapping windows from each recording in its participant partition.
- [ ] Test modest, physically consistent sensor-coordinate, noise, bias and scale perturbations based on training evidence. Do not independently rotate axes or time-scale channels/labels inconsistently. Avoid time reversal unless the full transformation has been derived and tested.
- [ ] Compare direct integration against fixed-uncertainty and learned-uncertainty variants. Retain the simpler one if uncertainty adds no reliable benefit.

**Gate:** beat the full-fold baseline without breaching the participant guard, hiding coverage loss or worsening endpoint/tail behavior beyond preregistered tolerances.

## Phase 7 - Add reliability-aware fusion only when it earns its complexity

**Outputs:** tested filter/smoother and measurement-correlation analysis, or a documented decision not to use it.

The center accelerometer does not directly measure velocity. Its contribution is a specific-force observation with gravity, attitude, initial-velocity, bias and lever-arm uncertainty. A wheel IMU measures angular motion; rolling speed is a conditional kinematic interpretation, not an encoder ground truth.

- [ ] Begin with a small planar pose/velocity/bias formulation with enough attitude handling for slope-related projections. Keep horizontal trajectory output distinct from unvalidated 3D attitude/position accuracy.
- [ ] Derive wheel/frame transforms and contact-point kinematics consistently. Distinguish total wheel angular velocity from relative wheel-to-frame rotation. Do not blindly subtract frame pitch or apply a flat-ground formula to every maneuver.
- [ ] Use soft wheel consistency, frame-rate/acceleration and local-motion factors. Relax no-slip/lateral constraints when evidence contradicts them.
- [ ] Do not estimate arbitrary per-frame scale, bias and slip simultaneously without an identifiability argument; they can explain the same error.
- [ ] Treat off-axis rotating wheel-sensor lever arms as time-varying unless working with a correctly transformed virtual hub state.
- [ ] A learned reliability score is NOT a validated physical slip probability. Name it accordingly unless independent existing labels support the claim.
- [ ] When both wheels share a rolling error, a weighted average of their velocities cannot by itself fix the error. Test a bounded local residual or uncertain short inertial propagation rather than claiming weighting solves common-mode slip.
- [ ] Avoid double-counting raw IMUs, wheel-derived features and learned predictions as independent sensors. Begin with non-overlapping learned updates or a conservative correlation-aware treatment and assess uncertainty calibration.
- [ ] Keep genuine IMU-only stationary detection distinct from assumed stops. No route-loop constraints, optical endpoint snaps or yaw resets.

**Gate:** matched direct-integration versus filter/smoother ablation, including coverage, tail errors and latency/offline status. No gain means keep the simpler estimator.

## Phase 8 - Historical two-IMU data and external data: a conditional branch

**Outputs:** historical-data provenance/benefit ablation or a justified exclusion.

- [ ] Determine actual roles, paired C3D availability, calibration domain and identities first. Two sensors are not automatically left and right.
- [ ] Start by masking the corresponding sensor in existing three-IMU recordings as a controlled availability test. Zero padding is acceptable WITH an explicit mask; it is not a measured zero acceleration/rate.
- [ ] Separate the benefit of the architecture from the benefit of extra data using the same final supervised IDs and training budget.
- [ ] Compare no historical pretraining, compatible two-IMU pretraining and joint masked training. Count already-included recordings only once.
- [ ] Use unlabelled historical recordings only for training-partition self-supervision. Do not invent C3D, center-IMU or true slip labels.
- [ ] Unknown-participant data belongs in an exploratory legacy track, not a supposedly independent participant-held-out claim.
- [ ] Generic open pedestrian datasets are not a required branch. External wheel-IMU data may test code or initialization if already accessible and compatible; do not make the result depend on requests for more data.

**Gate:** retain external/historical pretraining only if it improves matched training-side held-participant results. More data is not automatically beneficial.

## Phase 9 - Evaluation, tests and final claim

**Primary:** synchronized horizontal Euclidean RMSE against directly observed C3D, with the audit's equal-person hierarchy.

**Secondary:** Euclidean position MAE, synchronized position-error P95, local displacement/RPE with explicit definitions and fixed 1/5/10 s windows where eligible, wrapped yaw error, velocity/rate errors where reference derivatives are reliable, last-supported endpoint, supported path-length error and normalized drift where the denominator is meaningful.

Keep existing route metrics: symmetric point-to-polyline RMSE, directional route P95, sampled Hausdorff and supported-run discrete Frechet. Route P95 is NOT synchronized position P95. Report both by their proper names.

- [ ] Do not bridge invalid optical gaps, fabricate true recording endpoints, or redefine X/Y axes as forward/lateral unless transformed accordingly.
- [ ] Freeze eligible windows, durations, mask and support per comparison. Report coverage and abstention/failure counts alongside accuracy. A method cannot improve by silently stopping early.
- [ ] Store per-trial, per-person and per-maneuver tables; worst cases; time/path-length distributions; and paired differences versus each baseline.
- [ ] Report participant-cluster uncertainty descriptively with its limitations. Four validation participants do not become thousands of independent observations because frames/windows are numerous. Historical selection and overlapping training folds limit inferential claims.
- [ ] Preserve the original 5% training-participant guard. Prespecify additional endpoint/tail/failure tolerances on development data before candidate selection; never relax them after seeing evaluation results.
- [ ] Freeze one final candidate, all baselines, code/data hashes and evaluation rules before a single batch evaluation on the reserved retrospective test participants. Prior inspection remains disclosed. A rerun after a material bug fix requires an explicit contamination note.

Required automated tests include: perfect synthetic path, known scale error, constant heading error, heading wrap, stationary and pure rotation cases, slope projection, sensor-axis rotations, missing center sensor, timestamp shift and uniform-motion anchoring behavior, dropped frames, invalid C3D, gap/endpoint handling, participant-balanced aggregation, no learned-artifact overlap, and optical-input poisoning. Synthetic tests validate implementation; they are not extra real-world training evidence.

**Final decision:** report `outperforms on this benchmark`, `mixed result`, or `not demonstrated`, with actual numbers and uncertainty. Do not claim universal state of the art, clinical validity, millimeter metrological accuracy, or validated slip detection from this comparison alone.

## 6. Checkpoint and completion contract

After every phase, save the hypothesis, parent artifact hashes, IDs, configuration, commands, seed, runtime, metrics, regressions and decision. Update `research_state/STATUS.md`, `TODO.md`, `EXPERIMENTS.md`, `FAILED_IDEAS.md`, `BEST_RESULTS.md` when justified, and `NEXT_SESSION.md` with the exact next command.

Continue through feasible dependent tasks. If one branch is blocked, record the missing artifact and continue independent work. Do not keep training indefinitely until a favorable result appears. Stop at the preregistered budget and report the evidence honestly.

At handoff, provide a short update: reproduced state; strongest reproduced competitor; promoted or rejected change; before/after primary and tail scores; guard/coverage status; and the next unfinished task. Do not substitute a long narrative for saved reproducible artifacts.
