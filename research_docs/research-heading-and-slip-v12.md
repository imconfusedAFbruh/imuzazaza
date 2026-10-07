# Heading and slip: executable next experiments

Research date: 2026-10-03. Read-only review of existing v9/v10/v11 artifacts and primary papers. No model fitting or test acquisition access was performed for this note.

## Local evidence narrows the question

- v9 endpoint motion ensemble: 114.057 mm overall versus ridge 116.898 mm, but SL 147.682 versus145.482 mm. Whole-motion endpoint supervision was already attempted; repeating it with more epochs is not a new mechanism.
- v10 image/channel diagnosis: SL September24 improves150.1→85.5 mm, September25 worsens140.8→209.8 mm. On September25, yaw-only substitution worsens140.8→182.5 mm; forward-only substitution improves128.7 mm. Approximately83% of net yaw correction occurs outside derivative-supported intervals. Date/participant confounding prohibits declaring a date-specific sensor fault.
- v10 nine-coefficient motion calibration/fusion:116.255 mm overall/140.446 mm SL, but PS worsens204.660 mm and No.14 worsens. This already tested scale/offset/ensemble-blend corrections, so a repeat needs a genuinely different hypothesis.
- v11 empirical acceleration smoother: all24 nonzero candidates lose on the fixed training fold; unchanged ridge is selected. The rejected comparator remains116.918 mm overall and does not repair No.18 PS2 braking displacement. Do not promote acceleration integration because the geometry looks straighter.
- v9 full-axis empirical wheel/body bias comparator loses230.680 versus116.898 mm. Another static three-axis gyro projection alone is not sufficient novelty.

Sources: `research_docs/trajectory-findings-v10.md`, `research_docs/trajectory-image-diagnosis-v10.md`, `outputs_trajectory_calibration_v10/report.md`, `outputs_chassis_acceleration_v11/report.md`, `outputs_physics_state_v9/report.md`.

## 1. Highest priority: bounded yaw-only integrated correction

**Mechanism:** learn temporal gyro/yaw correction that reduces integrated relative heading error; hold the successful forward and lateral channels fixed. This isolates the measured late bending failure and prevents a yaw intervention from learning a new speed compensation.

Brossard, Bonnabel and Barrau use a small dilated convolution network to correct gyro measurements and train on robust integrated orientation increments rather than high-frequency differentiated orientation. They explicitly caution that very long or whole-sequence orientation objectives can overfit particular trajectory patterns. Their experiments use complete3D orientations; they do not establish this project's wheelchair accuracy. [Authors' paper](https://arxiv.org/html/2002.10718), [authors' code](https://github.com/mbrossar/denoise-imu-gyro).

**Executable adaptation:** zero-initialize a compact yaw residual head on empirical signed chassis gyro/acceleration, wheel-yaw disagreement, existing ridge motion and recent derivatives. Predict `yaw = ridge_yaw + bounded_delta`; freeze ridge forward/lateral. Train robust circular residual of trapezoid-integrated yaw against observed endpoint headings at0.25/0.5/1 seconds and optionally3/5 seconds. Include a valid derivative-rate anchor, correction L2/DC penalty and mild temporal regularization. Select objective weights/gain with training participant folds, not date-specific validation curves. Include unchanged ridge as a candidate.

Both endpoint poses must be observed; the intervening IMU sequence must be uninterrupted. Optical gaps do not require invented heading labels. However, observed relative heading gives rotation only modulo2π. Short-horizon anchors are essential for multiple-turn maneuvers; separately flag intervals where unknown turns across gaps prevent turn-count identification. `pipeline.prepare` unwraps each valid optical segment separately, so raw unwrapped subtraction across distinct segments cannot establish absolute revolution count. Wrapped loss is legitimate but cannot distinguish an extra complete revolution. Never force an unobserved gap to have zero turn.

**First cheaper comparator:** train a regularized yaw-only linear residual on the same endpoint integral constraints, using signed gyro/features and low-frequency summaries rather than only v10 scale/offset/blend. This tests endpoint supervision with fewer degrees of freedom before a neural run. It remains empirical; heading labels cannot identify every full3D mounting rotation.

## 2. Useful controlled comparison: extra epochs versus changed objective

Use matched architecture/data/seeds with fixed maximum budget, evaluate inner participant folds at predeclared checkpoints (for example12/24/48 epochs). Compare rate/short objective and integrated-heading objective. Keep the original1.28-second future context or explicitly declare a changed offline context. Report training-rate loss, relative-heading loss, whole-path RMSE and seed spread. More epochs can reveal underfitting, but decreasing rate loss does not prove reduced accumulated yaw error.

TLIO demonstrates that lower window prediction MSE can coincide with increased temporal error correlation and unchanged trajectory error. It compensates overlapping measurement correlation in its filter and uses bias/gravity perturbation training. Therefore simply extending context or averaging many overlapping predictions is not independent new information. [Authors' paper](https://arxiv.org/html/2007.01867).

Use perturbations consistent with raw-to-feature conversion and training-derived uncertainty. Arbitrarily rotating each wheel/chassis channel without transforming its sensor geometry creates inconsistent observations; unknown raw encoding prevents importing SI noise ranges literally.

## 3. Wheelchair slip correction: faithful but gated baseline

Van der Slikke et al. compare wheel-derived and chassis acceleration to detect concurrent skid; in turns they combine two estimates of frame-center motion from individual wheel motion and measured frame yaw. Wheel speed/deceleration informs adaptive weighting. Corrections sometimes worsen normal-speed/collision trials. The reported kinematic measures are not proof of whole-path millimeter RMSE. [Authors' institution-hosted paper](https://repository.tudelft.nl/file/File_a9e38cd0-ca20-48ae-ab3a-f8056b64a4ee).

**Executable empirical version:** derive per-wheel midpoint speed using trained geometry/yaw conversion, compute left/right implied midpoint disagreement and acceleration consistency, and fit a bounded residual correction/gate on training-fold motion or endpoint targets. Preserve independent observed headings and the ridge lateral channel. Compare single-wheel and concurrent-skid variants separately. Include braking-window displacement diagnostics, not only average speed RMSE. Do not label wheel/body disagreement as skid truth: mounting errors, scale error, tilt, lever-arm acceleration and sensor timing can generate the same signal. Concurrent skid removes the wheel no-slip velocity constraint, so integrating chassis acceleration needs calibrated gravity/bias and cannot preserve absolute speed indefinitely.

The paper's2.5 m/s² threshold requires verified conversion. Its full physics version must wait for confirmed encoding, mounting rotations and rotating wheel offset vectors; fitting empirical units is allowed if labeled honestly. The negative v11 result argues against another unconstrained acceleration smoother.

## 4. Uncertainty gate and offline fusion only after a useful estimator exists

Obtain out-of-fold residuals on known training participants; fit an IMU-feature-based prediction-risk model. Calibration must be assessed for yaw increments and displacement, including long optical-gap intervals, rather than inferred from a small training rate loss. Compare bounded gate toward unchanged ridge against always-on correction. Shared raw sensors and overlapping contexts mean estimator errors are correlated; do not use independent inverse-variance averaging without measured cross-covariance or conservative inflation. A gate can suppress damaging corrections but cannot restore information absent from all estimators.

Wheel-INS2 models wheel/body states, calibration and lever-arm relationships and assumes mounting calibration in its experiments. It is the physical foundation after acquisition evidence is complete; the v9 empirical comparator was not its reproduction. [Authors' paper](https://arxiv.org/html/2012.10593).

## Acceptance and identifiability

Use all71 fixed accepted validation trajectories only after training-fold selection; preserve the same observed masks/initial pose. Report each participant, maneuver, heading drift, local1/5/10 m displacement and final-observed error. Selection folds should refit all calibration/normalization; inherited full-training base models make a conditional fold, not independent end-to-end validation. Report that limitation if preserving the inherited base is intentional.

Known AR marker-side ambiguity requires acquisition evidence; a model must not be rewarded for arbitrary heading flips selected by its error. Gravity determines roll/pitch but supplies no absolute yaw reference. Wheel/chassis consistency can restrict relative motion under its assumptions, not prove uniquely identifiable tire slip or absolute position. Longer fitting, RL and factor-graph optimization do not remove those limitations. The current strongest executable direction is **yaw-only integrated correction with conservative gain**, followed by empirically calibrated uncertainty gating; stable gains must be measured rather than assumed.
