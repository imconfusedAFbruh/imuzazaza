# Trajectory failure research v33

Research date: 2026-10-04. Scope: read-only examination of the existing v14/v16/v21/v32 implementation and primary literature. No test signals were opened, no model was trained, and no prior artifact was changed. Proposed experiments below are hypotheses, not results.

## Current evidence and priority

The current selected v21 correction gives **102.585 mm** equal-participant mean trajectory RMSE and **1.362 degrees** heading RMSE over 71 exposed validation trials. Equal-weight restoration of stored training endpoints gives 105.172 mm; additionally restoring derivative velocity/yaw targets gives 110.932 mm. Source: `outputs_recovered_training_v32/run.json`.

The largest maneuver aggregates are PS 190.231 mm, 10x5 144.270 mm and SL 122.943 mm; uphill ST is 59.298 mm. Source: `outputs_recovered_training_v32/original_v21_maneuvers.csv`. Therefore a slope intervention alone is unlikely to dominate the overall improvement. It is still necessary for a defensible uphill model.

Implementation findings:

- `stationary_gravity_experiment_v14.py:feature_matrix` performs a **fixed startup gravity rotation** and subtracts startup gravity throughout the recording. Its gyro projection uses that startup direction. This is not a continuously updated attitude estimator.
- The center gyroscope scaling there is the magnitude of an empirical selected-axis raw-to-yaw fit. It is not established as a three-axis factory SI calibration. Feeding it to a physical attitude filter as verified rad/s would be unjustified.
- `trajectory_calibration_v10.py:integrate` integrates a planar forward/lateral/yaw prediction. Its learned forward target is already horizontal C3D velocity; multiplying the selected learned speed by cosine of an estimated pitch could double-correct a learned effect.
- `recovered_training_experiment_v32.py:restored` treats accepted stored processed points as valid added endpoint targets. The rates option differentiates trajectories containing such points. `motion_endpoint_experiment_v16.py:normal_system` gives these targets no explicit provenance confidence weight.
- All experiments still inherit a base/calibration previously fitted on the training participants used for conditional correction selection. Those folds do not independently evaluate the complete pipeline.

## What the primary sources establish

### Wheelchair-specific skid correction has direct evidence

Van der Slikke et al. compare wheel-derived forward acceleration with chassis acceleration for concurrent skid, and compare two wheel-specific midpoint-motion estimates using frame rotation for single-wheel skid. They favor the less decelerated/faster rotating wheel in the latter case. Their 20-participant sports study reports large error reductions during skid, while normal-speed and collision cases can worsen. Their published displacement/speed metrics do not establish millimeter whole-trajectory XY RMSE. Its absolute 2.5 m/s² trigger is inappropriate to import before this dataset's scale and gravity correction are established. [Institution-hosted original paper](https://repository.tudelft.nl/file/File_a9e38cd0-ca20-48ae-ab3a-f8056b64a4ee).

### Body attitude is needed to lift the horizontal-motion assumption

Wheel-INS2 explicitly explains that wheel-only navigation cannot supply vehicle pitch, and introduces body-IMU attitude to lift the horizontal-surface assumption. It uses velocity/nonholonomic constraints and relative positions across sensors in distributed EKFs. Its experiments calibrated mounting misalignments, measured lever arms, and initialized headings from the reference system. Its reported vehicle drift percentages are not transferable wheelchair accuracy bounds. This is the strongest physical foundation here, but it is not a drop-in replacement with the current unknown encoding/mounting information. [Authors' paper, sections IV–VI](https://arxiv.org/html/2012.10593).

WiCHINS separates body attitude, wheel phase/speed and body position/velocity into three estimators. It explicitly models an IMU's offset from the wheel hub and centrifugal acceleration, and compares predicted no-skid wheel angular velocity to the measured value. This is relevant to the stated off-axis wheel mounts. The car dataset, geometry, sensor calibration and outcome metrics differ from this project; this source supports an experimental mechanism rather than an expected numerical gain. [Authors' 2026 paper](https://arxiv.org/html/2601.00275v1).

### Processed C3D coordinates are weak labels, not new camera observations

C3D defines zero residual as processed data, which may have been interpolated, filtered or otherwise produced; a negative residual denotes invalid data. The numeric zero does not identify the processing algorithm or its uncertainty. Camera masks are optional. Complete stored XYZ can restore a display without establishing independently measured truth. Confidence weighting is our proposed use of uncertain labels, not a C3D-standard guarantee. [C3D residual definition](https://www.c3d.org/HTML/Documents/gloss_residual.htm), [floating-point layout](https://www.c3d.org/HTML/Documents/3ddatafloatingpointformat.htm).

### Interval uncertainty and bias estimates can improve fusion

TLIO predicts relative displacement and uncertainty, and incorporates them in an EKF estimating pose, velocity and bias. Its authors show that increasing prediction context can reduce window MSE without improving trajectory metrics, because overlapping errors become more correlated. Its author page explicitly shows rolling-on-a-chair failure outside the pedestrian training distribution. A wheelchair-specific uncertainty model and measured cross-correlation are therefore required; pretrained pedestrian performance does not support this dataset. [Authors' paper](https://arxiv.org/html/2007.01867), [authors' project page](https://cathias.github.io/TLIO/).

VQF provides magnetometer-free orientation estimation, rest/motion gyro-bias estimation and an offline variant. It is a useful attitude comparator after gyro scale is established. Without a magnetometer it does not create an absolute heading reference; acceleration during propulsion can also contaminate inclination estimates. [Authors' documentation](https://vqf.readthedocs.io/en/stable/), [authors' implementation](https://github.com/dlaidig/vqf).

## Three concrete falsifiable experiments

All three preserve the locked participant split, identical observed validation masks, initial-pose-only reference use at inference, and every accepted validation case. No participant/date lookup can be used to select an inference correction. Include the unchanged v21 candidate and select before examining the 71 validation outcomes. Record worst-participant regression, per-maneuver RMSE, heading error, final-observed error and local displacement, as well as the mean. The inherited base caveat must remain explicit unless every fold refits it.

### 1. Confidence-weight processed endpoints; keep observed rates

**Hypothesis:** v32's extra targets provide useful coverage when prevented from overruling reliable observed derivatives/endpoints.

Start from v21's exact basis, horizons, alpha and gain. Preserve original derivative labels, original observed-label feature normalization/clipping/caps, and original observed endpoint equations. Add a separate normal-equation contribution from newly enabled endpoint pairs. Use confidence 1 for an observed endpoint and q for a processed endpoint, with pair weight min(q_a, q_b). Predeclare q in {0, 0.1, 0.25, 0.5}; optionally restrict the added endpoint's processed run to at most 0.5 or 1 s, chosen within training folds. Do not add differentiated processed targets in this experiment.

Normalize the observed and added contributions separately within participant/maneuver groups: adding many processed intervals must not silently dilute the total observed-label weight. The zero-weight candidate must exactly reproduce the original fit and score. Report processed duration and actual weighted pair counts. A useful result is lower training-participant fold trajectory RMSE with at most 5% worst-person regression, followed by improvement on the unchanged observed validation score. Failure is flat/worse folds or improvements visible only when scored against the processed labels.

Implementation location: a new experiment script around `endpoint_normal`/`normal_system`; provenance is already available from v32's `original_observed_valid`. Never edit the original v21/v32 sources or caches.

### 2. Slip-gated short-interval velocity correction

**Hypothesis:** braking errors are caused by a temporary collapse of wheel-derived velocity while the chair still translates, or by one-wheel disagreement during turning.

Calculate separately signed wheel speeds using only training-derived mappings. Two implied midpoint velocities under no slip are v_L + (L/2) yaw and v_R - (L/2) yaw. Their disagreement, wheel deceleration and chassis acceleration consistency become the gate's inputs. They are diagnostic features, not verified slip labels. Fit a bounded forward-only interval residual on observed endpoint displacements, retaining v21 yaw and lateral predictions.

Compare two explicitly separated variants: (a) reweight the two implied midpoint estimates during asymmetric disagreement; (b) permit a short concurrent-slip bridge anchored to the pre-event velocity, with chassis acceleration controlling its change. Predeclare duration caps such as 0.25/0.5/1 s and include zero gain. Train thresholds/scales in empirical units until SI calibration is verified. This differs from the rejected always-on acceleration smoother: it operates only on short declared inconsistency events, and returns to the inherited estimator afterward.

Acceptance requires smaller braking-window displacement errors on held-out training participants and lower unchanged-mask validation RMSE without worsening ordinary no-skid turns. If the detector cannot distinguish tilt/scale/timing artifacts from skid or produces false-stop bridges, reject it. Do not enforce zero chassis velocity simply because both wheels are nearly stopped.

### 3. Dynamic gravity/tilt features and wheel-body angular coupling

**Hypothesis:** startup-only tilt features fail when ST pitch changes and when wheel axial measurements contain body rotation.

First add a conservative IMU-only dynamic inclination feature: low-pass normalized center acceleration direction, its change relative to startup gravity, and center gyro projection onto the current direction. Gate acceleration-based updates with wheel/body acceleration disagreement and norm deviations; compare 1/3 s smoothing constants in training folds. These are empirical features, not a proven attitude reconstruction. Fit bounded forward/yaw interval corrections, keeping the zero-feature v21 candidate eligible.

On the wheel-based physical comparator, account for body angular velocity projected onto the wheel axle before treating axial gyro as wheel spin. For a genuinely rolling forward body speed, horizontal projection is speed*cos(pitch). Apply this to the physical wheel-speed baseline only, not blindly to a learned prediction trained on horizontal targets. The wheel gyro measures wheel-relative spin plus the wheel-axis projection of body angular velocity; pitch at ramp transitions and camber/misalignment can therefore couple into apparent wheel spin. Off-axis accelerometer compensation additionally needs wheel phase and a full lever-arm vector.

After gyro scale and mounting calibration are confirmed, compare a proper 6D VQF/body-attitude estimate to the empirical inclination features. Use the recovered MoCap XYZ only as training supervision and read-only observed validation diagnostics, never as inference terrain input. Axle-pair XYZ alone cannot validate full body pitch. A useful result specifically reduces ST horizontal drift/ramp-transition error and preserves flat CR/AR performance. Improvement only after inserting validation-derived pitch or selecting a heading flip is invalid.

## Identifiability and accuracy limits

Absolute translation and yaw require an external reference or a declared initial gauge. Gravity constrains tilt and cannot supply global heading. Observability analyses of aided INS retain global-yaw/global-position unobservable directions even with local geometric features. [Authors' observability analysis](https://arxiv.org/abs/1805.05876). The project's allowed initial optical pose fixes the coordinate gauge, but a physically mislabeled left/right axle pair introduces a separate possible 180-degree semantic error. It must not be resolved by choosing whichever orientation minimizes the evaluated trajectory error.

Two markers define midpoint and axle direction, leaving rotation about the axle free. Thus they cannot uniquely identify full wheelchair pitch, sensor mounting rotations or a missing partner from pair distance alone. Wheel/body disagreement is also compatible with scale error, temporal misalignment, lever-arm acceleration and tilt; it cannot uniquely label tire slip without further assumptions.

An illustrative first-order error budget is e_lateral ≈ distance * heading_error_radians. At 5 m, a constant 0.1-degree error contributes about 8.7 mm; 1 mm would require about 0.0115 degrees under that isolated model. This calculation is not a trajectory error guarantee. No primary source reviewed establishes millimeter absolute position for the current three-IMU wheelchair data. Unknown reference uncertainty and calibration still limit such a claim.

## Recommendation

Run **experiment 1 first** because it directly tests the new C3D information while isolating label confidence from rate differentiation and normalization changes. Run **experiment 2 next** because PS/braking is the largest current aggregate and has direct wheelchair-specific mechanism evidence. Treat **experiment 3** as the route to a scientifically justified slope model, with a small empirical comparator now and calibrated full attitude fusion later. Large new architectures, RL or more epochs do not supply the missing physical references; promote them only after controlled participant-fold evidence.
