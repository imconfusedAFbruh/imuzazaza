# V9 build record

The authorized build implements the observed-reference improvement plan. All original pipeline sources, model selections, caches and historic test results are preserved. New development uses only training and validation signals.

## Comparisons

1. `observed_sync_experiment.py`: observed-only peak alignment, trained bootstrap calibration, unchanged acceptance gates, and a paired comparison on native observed reference timestamps with an identical initial pose. Coverage and calibration effects are reported separately.
2. `long_horizon_experiment.py`: matched network and training budget, short loss versus 1/3/5/10-second endpoint pose losses, with the same stitched 512-frame model contexts used at inference. Intermediate reference gaps are allowed only when endpoint poses are observed and IMU support is uninterrupted. Three predefined seeds are reported individually and as a motion ensemble.
3. `physics_state_experiment.py`: bounded empirical chassis-yaw bias state and wheel/chassis agreement comparator. Unknown CSV encoding and mounting rotations prevent claiming a calibrated full inertial navigation system. Parameters use a training participant fold before the validation comparison.

The 116.898 mm observed-reference ridge model remains the control. The primary metric is equal-participant mean trial position RMSE; SL, participant regressions, coverage and seed spread accompany the aggregate. Synchronization results that change timestamps or acceptance are reported separately from the loss comparison on the unchanged 71-recording reference cohort.

## Interpretation

The validation cohort has already guided earlier work. These results are exploratory. The original test recordings are not reopened. A target below 100 mm overall and on SL remains a target until measured. The generated-point reference correction is not counted as a new model improvement.

## Build artifacts

Each runner preserves its own source identity, settings, fitted artifacts, comparison tables and report. `build_comparison_v9.py` combines explicitly supplied matched trial tables without opening acquisitions. It rejects changed trial IDs, participant assignments or scored-frame counts; shared sealed cache provenance establishes actual mask identity.

## Completed results

| Comparison | Overall RMSE (mm) | SL RMSE (mm) |
|---|---:|---:|
| Existing ridge | 116.898 | 145.482 |
| Matched short-loss ensemble | 128.938 | 180.940 |
| Endpoint-loss ensemble | 114.057 | 147.682 |
| Inner-selected endpoint seed 43 | 123.002 | 138.525 |
| Empirical bias state | 230.680 | 232.591 |

The endpoint ensemble improves the aggregate by 2.840 mm (2.43%), but SL and two participant averages worsen. All three endpoint seeds score 118.247–142.175 mm (median 123.002 mm), versus 118.870–157.649 mm for short loss (median 138.503 mm). The predeclared inner-fold choice remains seed 43; the ensemble is reported as a separate predeclared candidate. Retain the current ridge selection. No stable below-100 mm or millimeter result was obtained.

The separate native-frame synchronization comparison is 116.823 → 116.508 mm, with a No.14 regression and eight additional training exclusions. Preserve its clocks/caches as an experimental protocol rather than promoting this tiny aggregate change.

Joint report: `outputs_build_v9/report.md`. Paired trajectories: `outputs_build_trajectories_v9/sl_comparison.png`. Drift, turn/straight and last-observed diagnostics are in the same folder. Prediction reproduced every sealed candidate trial RMSE within 1e-8 m using IMU-only predictor inputs and one separately supplied initial pose.

Checkpoint/model loader: `long_horizon_inference.load_long_horizon()` loads the inner-selected model; `load_endpoint_ensemble()` loads the mean motion of the three endpoint seeds. Both keep the original 1.28-second future IMU context. Original ridge inference remains `observed_ridge_inference.load_observed_ridge()`.

Sources, settings, all six checkpoints, seed results and artifact manifests are preserved in `outputs_long_horizon_v9/`. Incomplete coverage/padding attempts were archived before final validation and are not counted as valid final runs. Review findings and corrections are documented in `docs/build-v9-audit.md`. Fusion was not added because the physics state comparator failed to generalize; the full attitude INS still requires verified acquisition/mounting evidence.

