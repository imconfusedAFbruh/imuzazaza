# Trajectory research, image review and correction experiment

Research date: 2026-10-03. All trajectory comparisons use the same 71 accepted validation recordings and one observed initial pose. No later optical pose feedback, fitted trajectory rotation, time warping selected by position error, or test acquisitions were used. The validation cohort has already guided development, so these are exploratory results.

## What is currently best

There is no demonstrated universally best method for this dataset. The existing ridge is the stable control. The endpoint ensemble has the lowest aggregate among these three candidates, but worse SL and two participant averages. A new training-fitted correction improves the ridge aggregate and SL slightly, but regresses PS, OS and one participant.

| Method | Overall RMSE (mm) | SL RMSE (mm) | Interpretation |
|---|---:|---:|---|
| Current ridge | 116.898 | 145.482 | Retained control |
| Endpoint ensemble | 114.057 | 147.682 | Lowest aggregate; mixed generalization |
| Training-fitted calibration/fusion | 116.255 | 140.446 | Small SL gain; other maneuvers regress |

The calibrated candidate has three improving participant averages: No.10 90.250→87.444 mm, No.5 122.588→122.138 mm, No.18 147.954→147.234 mm. No.14 worsens 106.799→108.203 mm. Its PS error increases 195.817→204.660 mm and OS 109.398→114.699 mm. These figures come from sealed trial tables, correcting an inaccurate intermediate agent statement that two participants worsened.

The correction fits nine coefficients per acquisition setup: channel scale, offset and endpoint-minus-ridge blend for forward/lateral/yaw. It uses training-only velocity and linearized 1/3/5/10-second endpoint constraints, regularized and damped. Alpha, endpoint weight and gain are chosen on No.3/8/15/20 before refitting all 473 training recordings. Inherited predictors already saw those inner participants; this is conditional selection, not a fully nested independent pipeline. See `outputs_trajectory_calibration_v10/report.md`.

## What reading the images revealed

### SL: the late bend is mainly accumulated yaw correction

All seven maneuver overviews were inspected, followed by individual trajectory/position-error/heading-error panels and native rotational marker diagnostics. The endpoint ensemble corrects the September 24 transverse displacement but adds a late bend on September 25. SL means by session are 150.1→85.5 mm and 140.8→209.8 mm respectively. These cohorts contain different people; date and participant are confounded, so this does not prove a date-specific hardware fault.

Channel substitution identifies the main mechanism: on September 25, replacing only yaw with the ensemble worsens 140.8→182.5 mm; replacing forward speed improves to128.7 mm, and lateral replacement worsens to159.4 mm. These are diagnostic model channel substitutions, not optical oracle predictors. About83% of the net yaw correction occurs outside derivative-supported intervals. Rate error averaged over the available labels therefore hides accumulated heading drift. Optical gaps stay masked and never reset the predicted path. Source: `research_docs/trajectory-image-diagnosis-v10.md`.

As an illustration, a0.1° heading error over a straight5 m segment creates approximately8.7 mm of transverse displacement. This is geometry, not a claim that the same formula equals the error on a turning sports trajectory. Heading accuracy must improve along with forward displacement if the study aims at millimeters.

### AR: two initial-heading/side identities remain unresolved

No.5 AR2/AR3 show tiny irregular reference midpoint paths on the opposite side of the predicted circles. Native data are almost completely observed and rigid: separation standard deviations0.735/0.751 mm, approximately739°/732° heading sweep, and yaw correlation about0.9998. Optical signed forward speed anti-correlates with the calibrated wheels, −0.833/−0.919. Initial headings differ approximately180° from AR1.

This supports a possible physical-left/right label or heading convention ambiguity; it does not prove a label swap. Both C3Ds contain only `L_FAL` and `R_FAL`, with no independent front/rear marker. A consistent side swap preserves midpoint and yaw derivative while reversing heading and signed forward velocity. Residual, rigidity and yaw-peak checks cannot resolve it. No automatic flip or error-based exclusion was applied. Acquisition/QTM/video evidence is needed for any separately versioned amendment. Source: `research_docs/rotation-reference-image-diagnosis-v10.md`.

No.5 CR3 is a genuine near-in-place turn: both markers make full circles while the midpoint remains within about231×120 mm. Its small irregular path must not be replaced by an ideal circular template.

### PS/ST: overlapping shapes can still have large displacement error

No.18 PS2 looks almost straight for every method, yet position error rises to roughly0.5 m during braking and persists. Native positions and supported derivative labels show about0.39 m/s underprediction over1.5–2.8 s, totaling about0.51 m. Wheel-derived velocity drops toward zero around1.9 s while the observed chassis decelerates until about2.8 s. This is compatible with wheel/body braking disagreement or slip; it does not uniquely establish skid or rule out remaining acquisition uncertainty. A pretty overlapping path is insufficient: along-path displacement error needs the time-series panel. The new calibration worsens that trial,448.0→465.2 mm. The full gallery includes position and heading error versus time for every accepted recording. See `outputs_acceleration_diagnosis_v10/report.md`.

No repeated per-axis extreme plateaus were found in that recording. CSV encoding remains unknown, so a32000-count proxy cannot rule out saturation. Its empirical peak wheel speed gives only about0.468g centripetal acceleration at the configured4 cm offset; it does not support blaming this particular failure on high-speed2g centrifugal clipping. Empirical acceleration-norm peaks are not verified factory SI readings, and a vector norm above2g does not establish per-axis clipping.

### Coverage differs substantially by maneuver

Of84 planned validation repetitions,71 are accepted:12 each for10x5/AR/CR/SL/ST,8 PS, and only3 OS from two participants. Missing panels are labeled as unaccepted, not assigned invented exclusion causes. The earlier and corrected QC tables establish their actual synchronization/reference reasons. Do not treat the OS aggregate as a four-person estimate or silently omit the13 missing repetitions in a paper.

## Acceleration-assisted braking correction (v11)

An additional empirical chassis-acceleration velocity smoother was built after reading the braking plots. All 24 nonzero candidates worsened the fixed training participant fold: unchanged ridge 162.363 mm, best nonzero candidate 162.494 mm. The unchanged ridge was selected. A separately labeled rejected comparator was refitted on all 473 training recordings and evaluated once on the 71 validation recordings: overall 116.918 mm, SL 146.034 mm, PS 196.019 mm, versus ridge 116.898/145.482/195.817 mm. It changes forward velocity only; yaw and lateral predictions remain identical.

The new braking image was inspected. Its empirical chassis acceleration still finishes deceleration too early, and the velocity smoother leaves approximately 0.55 m of persistent displacement error. This is a concrete failed correction, not an established fix. Full-recording filtering/smoothing makes it offline; shared sensor/model inputs prevent interpreting its two terms as independent measurements. Selection and diagnostic artifacts are preserved in `outputs_chassis_acceleration_v11/` and `outputs_chassis_acceleration_v11_rejected_comparator/`, including coefficients, CSV results, manifests and `braking_comparator.png`. No test signals were opened.

## Strongest defensible method to develop

The best-matched physical foundation is [Wheel-INS2](https://arxiv.org/html/2012.10593): wheel/body attitude, bias/scale states, calibrated mounting and rotating lever-arm geometry. Its results do not prove millimeter accuracy here. The paper models off-center wheel IMUs; the configured4 cm offset is not intrinsically incompatible. Actual SI encoding, full mounting rotations and lever-arm vectors still need verification before a faithful physical INS can be claimed.

[TLIO](https://cathias.github.io/TLIO/) supplies the learned-estimation lessons: gravity-aligned inputs, bias/gravity perturbation during training, interval displacement with calibrated uncertainty, and jointly estimated bias states. The authors also show chair-rolling failures outside their pedestrian training distribution and warn that overlapping longer windows can reduce prediction loss without reducing path error. Importing a pedestrian checkpoint or adding a larger network is not established as the best solution.

For these data, the next useful model comparison is an independently regularized yaw estimator with relative-heading endpoint supervision, raw-signal-consistent bias/mounting/scale augmentation, and an IMU-only uncertainty gate. Use complete participant folds inside training, refitting calibration and normalization within each fold. Augmentation magnitudes must come from training/acquisition evidence. The existing three-axis empirical physics comparator already failed; merely refitting another gyro projection is insufficient evidence of a gain.

Then compare calibrated wheel/body navigation with domain-trained interval motion/uncertainty in a correlation-aware offline smoother. [GTSAM's CombinedImuFactor](https://borglab.github.io/gtsam/combinedimufactor/) is an implementation option after the physical model is validated, not a source of new absolute information. A faithful wheelchair wheel/chassis slip correction is a relevant comparator; disagreement is not a unique slip label. No RL advantage has been demonstrated here.

Retain the current ridge selection while the new candidates remain exploratory. Do not choose per-date/per-maneuver models from the displayed validation scores, force paths through cones, snap endpoints closed, or use later optical poses to make the plots look correct. The small correction does not resolve the observed generalization and initial-heading ambiguities.

## All trajectory artifacts

Final gallery: `outputs_trajectory_report_v10/gallery.html` (filter by participant/maneuver/trial).

All71 pages: `outputs_trajectory_report_v10/all_71_trajectories.pdf`.

Seven overview sheets: `10x5_all.png`, `AR_all.png`, `CR_all.png`, `OS_all.png`, `PS_all.png`, `SL_all.png`, `ST_all.png` in that folder. Each uses equal physical aspect ratio and identical limits within its maneuver. Black is observed reference, gray current ridge, teal endpoint ensemble, orange training-fitted correction. Reference gaps remain blank. Individual plots include trajectory, position error and heading error. Cached trajectories, CSV metrics and SHA256 manifests accompany them.

Full primary-source review: `research_docs/research-best-trajectory-v10.md`. Implementation: `trajectory_calibration_v10.py`, `trajectory_calibration_inference_v10.py`. Image artifacts are reproducible from `plot_all_trajectories_review_v10.py` and `finalize_trajectory_plots_v10.py`; original outputs were preserved.
