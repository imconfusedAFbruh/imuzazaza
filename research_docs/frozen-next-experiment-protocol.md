# Frozen next-experiment protocol - 4 October 2026

## Current status correction — 15 October 2026

This is a historical proposal, not an active authorization for the model sweep
below. The completed v123 comparison now establishes frozen v121 at 99.303735166
mm versus v34 at 100.702119399 mm on matched exposed validation; all guards pass.
See [review closure](frozen_validation_review_v123.md). Do not repeat that
comparison or use its outcomes to tune another candidate. The v21/v31 status,
unverified serialization and +/-2 g statements below describe the October 4
knowledge state and are superseded.

The [completed firmware audit](firmware_receiver_audit_2026-10-05.md) and
[release verification](firmware_primary_audit_2026-10-08.md) establish a raw int16
receiver path and support +/-4 g, +/-2000 dps, 104 Hz sensor ODR and approximately
102.4 Hz recorded polling. They do not establish each board's exact flashed
binary or runtime range registers. Do not rescale frozen inputs or replace device
timestamps with nominal row timing.

The remaining acquisition work is to link firmware/binary identity and runtime
register readback to each recording, preserve original START/STOP/SYNC journals,
and record shared hardware timing events near both ends of each capture.
Full mounting/marker geometry and independent reference uncertainty measurements
also remain necessary. Existing metadata searches did not establish independent
clock mappings; repeat them only when new linked evidence arrives. A new final
cohort must remain unopened until its model, acquisition/QC protocol, sample-size
justification and analysis are frozen. The historical ablation list below is not
a newly approved search budget. No new acquisition evidence was supplied in this
continuation, and no numerical task was executed.

## Decision and status
Stop additional fitting or candidate selection against the reused 71 recordings. Freeze v21, v24, v25 and all completed v26-v31 candidates. v21 remains the lowest observed overall RMSE comparator; v31 is a stricter conditional pivot candidate, not a new blind best model. No final test data were accessed during this diagnostic update. Prior historical test exposure remains disclosed and cannot be undone by a new split label.

## Physical acquisition gates before another model sweep
1. Archive the actual acquisition firmware and CSV receiver/packing source, versions, sensor range registers and timestamp definitions. Actual ranges reported by the user: +/-2 g and +/-2000 degrees/s. Integer CSV encoding remains unverified; do not substitute the older 16 g default.
2. Collect six-orientation stationary accelerometer measurements and controlled known-rate gyro rotations, including rest bias and saturation checks. Determine count-to-SI conversion from source and measurements; record uncertainty rather than inferring it solely from the approximately 8200 rest norm.
3. Measure full 3-D IMU lever-arm vectors and mounting rotation matrices. Wheel sensors are off-axis, outward and mirrored; the center faces backward. These descriptions alone do not define numeric transforms. Use gravity and controlled wheel rotation to constrain independent axes, document signs and residuals.
4. Add a uniquely identifiable physical-front marker or calibrated rigid 3-4-marker cluster; validate hub-midpoint geometry and global coordinate convention against an independent measurement. Quantify absolute reference uncertainty; camera reprojection residual is not that quantity.
5. Add common events observed by every IMU and Qualisys near the start and end; estimate offset and clock-rate drift. Save synchronization residuals and uncertainty. Do not choose alignment from the final trajectory error.
6. Start each recording with 5-10 s deliberate quiet rest. Collect balanced normal rolling, pivot, slalom and mild/medium/aggressive braking/coasting, with independent participant coverage and logged acquisition changes.

## Development participant nesting
Target training participants only: No.1,3,4,6,7,8,13,15,16,17,19,20. Keep every date/recording for a person together before windows. Outer folds: A=3,8,15,20; B=1,4,13,16; C=6,7,17,19. For each outer fold, use the other two groups as two inner participant folds. Refit the complete original neural stack, calibration, normalization, feature fitting and learned preprocessing in every inner fit and then on all eight outer-training participants. No inherited full-training weights or fitted calibration. Deterministic reference/QC rules are frozen; any data-derived choices are made only within the fitting partition. Optical initial pose and per-recording timing remain explicitly declared evaluation inputs; deployment needs independent pose/timing.

The 266 earlier recordings have unmapped identities. Exclude them entirely from nested CV rather than retaining them in every fit. Map identities before considering later use. The historical final population and all repeatedly inspected validation people are development/exposed data, not a fresh blind cohort.

## Finite objective ablation in training folds
A: only endpoint pairs wholly contained in continuously observed optical segments, including all interior frames; no interpolated gap heading.
B: A plus gap-spanning XY endpoint constraints as a separate objective; omit gap-spanning heading unless rotations are independently observed. Wrap observed endpoint angles where appropriate and do not infer hidden complete turns.
Use equal participant -> equal available maneuver -> equal recording -> normalized endpoint weighting. Record missing cells. Compare A/B with the same initialization, epochs, optimizer schedule and architecture. Freeze a finite hyperparameter list before inner runs; no adaptive sweeps against outer or existing validation scores.

## Next physical model
Calibrated wheel/body estimator with body forward/lateral velocity, yaw rate and gyro bias, and bounded wheel-slip states. A small temporal residual predicts constraint relaxation/slip and positive uncertainty; fuse via a consistent SE(2) filter or offline smoother. Handle wheel-stop/body-coast explicitly and require quiet-state evidence for bias updates. Do not manufacture XY corrections or use reference trajectory at inference. Compare physics-only, slip-only, yaw-bias-only, combined and combined-with-uncertainty additions under the same fully refitted nested protocol. Architecture and hyperparameters are selected in inner folds only.

## Predeclared reporting and selection
Primary: equal-participant mean recording XY Euclidean RMSE on observed frames. Also report equal-participant/equal-available-maneuver RMSE, trial P90, worst participant and worst maneuver, heading error, coverage, endpoint drift and uncertainty calibration. Do not score missing cells as zero. Require no more than 5% regression against the matched physics control for any outer held participant or participant-maneuver cell; a failed guard cannot be overridden by lower aggregate RMSE. Use participant bootstrap intervals as descriptive uncertainty, with limited participant count disclosed. Report every accepted recording and every QC exclusion by predeclared reason.

## Blind evaluation
Collect a new participant cohort with complete intended maneuver coverage after measurement gates pass. Freeze code/model hashes, QC thresholds, metrics, synchronization rules and selection decisions before opening that cohort. A custodian retains the data until one final evaluation. No post-evaluation hyperparameter changes or replacement of failures; any later development requires another independent evaluation cohort. Required participant count should be set prospectively from target precision and observed participant variance, not from achieving a desired score.

## Diagnostic limitations
Current official full-recording scores remain unchanged. Counterfactual integrations reset at each continuous observed segment after 0.2 s edge trimming, using segments at least 1 s long and a second-order 6 Hz XY lowpass for reference velocity. All substitutions within a recording share scored frames. The reference-all reconstruction floor describes numerical derivative/integration consistency, not absolute optical accuracy. Initial heading is already optical; there is no independent reference-initial-heading improvement. Yaw +/-0.1/0.5/1 degree, fixed motion time queries +/-10/25/50/100 ms, and forward/yaw motion scales +/-1% are sensitivity hypotheses only. Time queries outside the trace clamp to endpoint values; scoring excludes the first/last 0.1 s. Motion scales are surrogates, not measured geometric error. No best offset or pose is selected. Error components interact and cannot be summed as additive RMSE contributions.
