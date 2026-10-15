# Review of the current best v121 model

15 October 2026. Source review before v124 candidate fitting. This is an
architectural review of the saved model and its existing evidence; it does not
repeat the completed v121/v123 experiments.

## What prediction does

1. Read left/right/center IMU arrays, increasing timestamps, acquisition setup,
   validity and original IMU startup initialization. Retain the inherited ridge
   and v34 predictors and their sealed calibration/artifact checks.
2. v34 blends the original physical-product motion and dynamic-tilt motion at
   fixed weight .75. These use offline temporal context/filtering. They supply
   forward/lateral/yaw motion, with a single initial pose used later to integrate.
3. Add a fixed16-state leaky tanh reservoir over the current-time15-feature
   block of `stationary_gravity_experiment_v14.feature_matrix`. Its inputs are
   gravity-rotated center acceleration3/gyro3, calibrated wheels2, ridge forward
   and yaw2, wheel/chassis yaw disagreement, wheel acceleration, vertical gyro,
   vertical/ridge yaw disagreement and the startup-initialization eligibility flag.
4. Normalize/clip inputs using fitting-person statistics for that setup, advance
   deterministic fixed random state, and append an intercept. A17x2 readout per
   acquisition setup adds clipped forward/yaw corrections capped at .05m/s and
   .02rad/s. Lateral motion is inherited. No optical or identity fields enter
   the prediction function. Invalid IMU resets the state; integration stops at
   the first unsupported IMU interval.

Sources: `reservoir_path_v121.py`, `reservoir_inference_v121.py`,
`dynamic_blend_inference_v34.py`, `stationary_gravity_experiment_v14.py`,
`trajectory_calibration_v10.py`. Public loader verifies model and dependency seals.

## Why it is the retained best

The v121 comparison reproduced strong v34 on all207 matched TRAIN records, then
optimized bounded forward/yaw readouts through exact full-path integration.
The three fixed ridge penalties were selected with participant folds and the
original person/maneuver/tail/endpoint/heading/support guards. Penalty10 produced
129.739810994mm equal-participant TRAIN ATE versus132.240200104mm for v34.
Penalty1's127.490837mm mean failed participant guards and was rejected.

After a full207 TRAIN fit and artifact freeze, v123 reproduced all71 v34
validation records and scored v121 once. Its99.303735166mm ATE improves the
matched100.702119399mm control, with all guards passing. TRAIN and validation
remain distinct cohorts. v122's existing descriptive TRAIN uncertainty interval
includes zero; this does not establish independent significance.

## The next testable weakness

The training objective averages squared path errors, whereas candidate selection
averages trial RMSE within each person. Squaring gives difficult/high-error
trials more influence in fitting than their contribution to the selected metric.
This is a mismatch visible in the code, not proof that changing it will improve
generalization. The first new test changes only the loss and anchors the weights
to v121, retaining the validated features and correction limits. Three fixed
prior strengths and guards against both retained controls bound the experiment.
See `trial_rmse_v124.md` for the preregistration and its decision boundary.

## Limits that another readout cannot repair

The complete model remains offline. Startup gravity alignment does not observe
mounting yaw or certify actual stationarity. Acquisition setup selects inherited
calibration/readout; parent models retain266 other training-record dependence.
Original optical crops, clock mappings and an initial optical pose remain part
of the evaluation contract. Independent clocks, exact per-recording firmware/
runtime identity, physical geometry and new final acquisition evidence remain
unresolved. The development folds and validation have repeated research exposure;
further conditional gains cannot certify independent final generalization.

Existing evidence: `reservoir_path_results_v121.md`,
`reservoir_stability_results_v122.md`, `frozen_validation_results_v123.md`,
`frozen_validation_review_v123.md` and `research_state/v121_review.json`.
