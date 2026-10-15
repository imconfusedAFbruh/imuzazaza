# Preprocessing provenance and paired-clock refit: v70-v73

8 October2026. TRAIN207/12 identified participants, fixed three folds, no validation or reserved-test access. No unknown-identity legacy training and no model search.

## v70: inherited preprocessing is not fully nested

Geometry and v9 synchronization bootstrap artifacts contain every held participant's accepted IDs:68/69/70 held acquisitions in the three folds. v49/v52 calibration and predictive fits exclude held IDs, but their seed references/clocks remain inherited. This distinguishes predictive fitting exclusion from complete preprocessing independence.

Refitting the unchanged geometry algorithm on each fold's fitting IDs removes27,580 observed frames from15accepted No.20 recordings. No.20's marker pair is approximately0.746m apart; the remaining fold0 training marker band is approximately0.635-0.683m. Other folds retain the wide band because No.20 is then in fitting. This is an acquisition/reference geometry domain difference, not evidence that those trials are invalid. No trials were discarded, no estimator was scored on this reduced support, and no new accuracy claim is made.

**Contract:** preserve the historical reference mask for continuity; separately declare fold-dependent preprocessing. Never call a reduced-mask score a gain. All fitted artifacts must list fitting IDs and exclude held IDs; unknown identities cannot enter strict fitting/pretraining. Reference inclusion and predictor fitting are separate contracts. Existing learned geometry and inherited clock seeds remain unresolved for a completely nested track.

## v71: fitted synchronization-term sensitivity

Same frozen observed reference policy and full native IMU streams, comparing inherited v9 terms with provisional fold-fitted terms. Both accept199trials; the same8reject under both. Every trial retains the same selected center axis/sign. Maximum normalized yaw-signal difference6.217249e-14: positive linear scale/intercept cancel under normalization. No offset change exceeds1ms; maximum0.6ms occurs in No.17 CR using calibrated-speed alignment.

**Decision:** inherited coefficient magnitudes do not materially change these alignments. This numerical sensitivity result does not erase provenance or prove axis/sign selection independent of historical data. Eight alignment failures remain recorded rather than removed. Original archived alignment fallbacks remain in the frozen comparison.

## v72: original versus arbitrated clocks with complete simple predictive refit

Fixed physics forward speed plus offline dynamic-gravity projected yaw. Calibration, axes/scales/bias/gravity and yaw regression are refitted from fitting participants for each clock; no inherited neural/base model or correction. This is a complete SIMPLE predictive-estimator refit, not a full historical v34 neural/residual refit. Evaluation uses shared native observed C3D support and one shared initial pose. All207trials retained. Geometry/QC, cached clocks and arbitration remain inherited evaluator dependencies; do not claim complete preprocessing independence.

Equal-participant means of trial metrics:

| Metric | Original clock | Arbitrated clock |
|---|---:|---:|
| Synchronized XY RMSE |156.001639mm|147.697253mm|
| Position MAE |134.399212mm|127.546708mm|
| Synchronized P95 |255.912082mm|241.922918mm|
| Route RMSE |62.691260mm|60.292338mm|
| Route P95 |125.990366mm|119.228108mm|
| Supported-run max discrete Frechet |267.772167mm|256.951001mm|
| Sampled Hausdorff |227.725899mm|216.893339mm|
| Last-supported endpoint |201.238131mm|193.837472mm|
| Absolute supported length error |356.447549mm|337.009541mm|
| Heading RMSE |1.861919deg|1.834858deg|
| Contiguous1s world-displacement RPE |81.257408mm|75.045257mm|
| Contiguous5s world-displacement RPE |108.131742mm|104.651604mm|
| Contiguous10s world-displacement RPE |78.902595mm|79.463064mm|

Reference/reconstruction common scoring coverage87.310343% as an equal-person mean of trial supported fractions, identical for both methods. RPE averages only eligible trials/persons; counts are saved, absence is not zero. RPE has no heading-normalizing alignment and differs from legacy distance-window metrics.

Worst participant regression: No.13+10.476104%,141.299947->156.102676mm. No.17+8.037741%,133.102785->143.801242mm. No.15 improves215.351077->85.658616mm. Worst maneuver regression10x5+3.726394%; ST+3.665988%. No.13 endpoint143.427997->174.897854mm, route56.152730->62.344244mm. Thus average improvement fails the frozen5%participant guard. **Reject promotion.** Historical retained v34 remains unchanged.

## v73: timing versus fitted calibration

Fixed2x2 diagnostic using the already fitted v72 models. No refitting, tuning or candidate selection:

| Model / clock | Equal-person XY RMSE |
|---|---:|
| Old model / old clock |156.001639mm|
| Old model / new clock |147.386863mm|
| New model / old clock |156.538460mm|
| New model / new clock |147.697253mm|

No.13:141.299947(old/old),157.247594(old/new),140.888474(new/old),156.102676(new/new)mm. No.17:133.102785,143.011011,134.331366,143.801242mm. The regressions persist when only the clock mapping changes; replacing fitted coefficients alone does not explain them. No.15's large improvement also persists with the old model/new clock. This isolates a clock-dependent effect in this estimator/evaluation, not proof that the signal-selected clock is physically wrong. Do not pick the old clock merely because localization RMSE is lower.

828 optical-input poisoning checks passed for motion prediction; all fitting IDs exclude held IDs. Both diagonal predictions exactly reproduce v72(max XY difference0), and masks remain identical.23two-panel trajectory/yaw figures saved, IMU red/C3D black. No.13 10x5Trial1 visually reviewed: similar repeated-turn yaw timing with outward route/length mismatch; no posthoc fit or reset applied.

## Budget and artifacts

Family2 has original-clock, inherited observed/arbitrated-clock and fold-term sensitivity configurations; v70 geometry support and v73 fixed-model decomposition are correctness analyses, not extra tuned models. No new architecture family consumed. All versioned output directories preserved. Tests include deliberate fit-ID collision rejection, positive affine normalization invariance, matched-mask assertions, exact baseline reproduction and optical-input poisoning.

Commands(all completed): `python strict_preprocessing_v70.py`; `python fold_sync_sensitivity_v71.py`; `python paired_clock_refit_v72.py`; `python clock_calibration_decomposition_v73.py`. Outputs are corresponding outputs_*_v70/v71/v72/v73 directories with protocols, fitted IDs/models, metrics, coverage, trajectories, figures and manifests. Do not rerun into existing directories.

Next priority: inspect distributed speed/yaw event evidence and moving initial-pose sensitivity for No.13/No.17 clock-dependent failures, using training analogues and no RMSE-based clock choice. Complete a strictly nested initial clock bootstrap without inherited fitted seeds and a reference-inclusion policy that preserves wide-geometry acquisitions. Do not proceed to larger networks or claim superiority over published methods.
