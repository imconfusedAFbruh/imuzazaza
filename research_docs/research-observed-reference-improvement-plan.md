# Improvement plan after correcting reference validity

Research date: 2026-10-03. Development participants only. No model training or test-signal access in this research task.

## Starting point

The corrected benchmark is 71 validation recordings, four participants, equal-participant mean trajectory RMSE 116.898 mm. SL has 12 validation recordings and mean trial RMSE approximately 145.5 mm. The large previous reduction principally corrected unsupported C3D initialization; it does not demonstrate a comparable learning gain. Current candidates use 1.28 s future IMU context. [Local recovery report](../outputs_reference_recovery_v8/report.md), [SL provenance](../outputs_sl_v8/provenance.json).

**Recommendation:** diagnose persistent motion errors, build a calibrated three-IMU state estimator, then compare learned relative displacement with uncertainty. A larger window or network is not the next evidence-led step.

## Primary-source findings

### Wheel-INS2 is a closer physical precedent than pedestrian RoNIN

Wheel-INS2 explicitly studies two wheel IMUs plus one body IMU, the same sensor placement family. It estimates position, velocity, attitude, sensor biases and scales; wheel rotation provides speed, body attitude removes the horizontal-surface assumption, and spatial constraints couple the sensors. Its reported 0.73% drift for the triple configuration is route drift, not wheelchair RMSE or a promised result here. The experiments assume mounting angles and lever arms calibrated in advance. [Authors' paper](https://arxiv.org/html/2012.10593).

Wheel-INS uses wheel rotation modulation to mitigate some constant bias effects; this does not eliminate all bias, fix scale, or provide absolute position observations. Its official implementation and example datasets support a reproducible comparator. [Authors' code](https://github.com/i2Nav-WHU/Wheel-INS).

**Project-specific inference:** do not copy wheel-center equations unchanged. Our stated 4 cm radial mounting offset rotates relative to the chair. Compensation requires wheel phase, full mounting rotation and lever-arm vectors. Sensor acceleration contains tangential and centripetal terms. The wheel IMU positions are not fixed offsets in the chair frame, although wheel hubs are. A nominal scalar offset is insufficient for a strict rigid-body model.

### Relative displacement and uncertainty address a different weakness

TLIO predicts relative displacement and uncertainty, then fuses these into a stochastic-cloning EKF that estimates pose, velocity and biases. It defines displacement in a local gravity-aligned frame to avoid falsely observing global heading. Longer overlapping input windows can reduce individual displacement MSE while increasing temporally correlated errors, leaving trajectory accuracy unimproved. Bias and gravity-direction perturbations improve robustness in its experiments. These are methodological precedents, not portable pedestrian weights or wheelchair performance guarantees. [Primary paper](https://arxiv.org/html/2007.01867), [authors' implementation](https://github.com/CathIAS/TLIO).

**Project-specific proposal:** predict relative planar motion `(delta_forward, delta_lateral, delta_heading)` over short intervals, plus uncertainty. This targets accumulated motion and allows lateral movement. Compare direct integration against uncertainty-weighted fusion; do not assume learned variance is calibrated. Gravity/body frames at inference must come from IMUs and measured calibration, never continuous reference orientation.

### Offline smoothing can revise biases, but cannot create information

GTSAM's IMU preintegration connects pose, velocity and bias between keyframes. Standard `ImuFactor` requires separate bias-evolution factors; `CombinedImuFactor` includes bias evolution and related covariance. These mechanisms support a physically defined offline estimator rather than simply smoothing predicted speed/yaw traces. [Official ImuFactor documentation](https://borglab.github.io/gtsam/imufactor/), [CombinedImuFactor](https://borglab.github.io/gtsam/combinedimufactor/).

**Project-specific limitation:** a factor chain with one initial pose and no new independent constraints still drifts. Overlapping learned measurements share inputs and can have correlated errors; treating every overlapping factor as independent creates overconfidence. Start with nonoverlapping measurement intervals, then quantify residual autocorrelation before dense overlap. Raw IMU and learned measurements from those same IMUs also share information; fusion needs conservative weighting and consistency checks.

## Ordered experiments and decision gates

| Order | Experiment | What it resolves | Keep it only if |
|---|---|---|---|
| 1 | Corrected-reference development error decomposition: reference yaw oracle, forward-speed oracle, lateral-speed oracle, reference-derived full motion integration | Whether SL failures are yaw drift, scale/speed error, lateral dynamics, or derivative/reference artifacts | Results use identical camera-supported intervals and are labeled diagnostic oracles, never estimator scores |
| 2 | Calibrated physics comparator: body attitude and gyro-bias state; wheel speed updates; rotating lever-arm correction; IMU-derived stationary updates | Whether modeling frames, attitude and slow drift beats empirical corrections | Same recordings/initial pose, no reference updates; no systematic per-participant or maneuver regression |
| 3 | Relative SE(2) displacement head with uncertainty, compared with the current velocity head under matched architecture/compute | Whether supervising interval motion improves trajectory drift | Improvement survives multiple seeds and development participant folds; interval uncertainty matches measured errors |
| 4 | Offline smoothing of physical and learned relative-motion constraints | Whether whole-recording consistency improves state/bias estimation | It beats direct integration and a physics-only smoother, with no false endpoint or loop-closure constraints |

All rows are proposed experiments, not already measured improvements. Compare against the frozen corrected 116.898 mm model. Keep equal-participant whole-trajectory RMSE primary; report SL, turn apex, straight segments, endpoint, fixed-distance relative pose and uncertainty coverage. A fast 5% development gain can justify further investigation, but should not be called a reliable population improvement with only four validation participants.

## Constraints that matter particularly for SL

- Wheel-INS2's nonholonomic constraint assumes no lateral/vertical vehicle velocity. Use a soft measurement with uncertainty, or disable it when IMU-derived consistency checks fail. A hard zero-sideways constraint would prevent genuine lateral-skid recovery. This recommendation follows from the constraint's mathematical meaning, not proof that these trials contain skidding.
- Wheel/chassis yaw disagreement is evidence of inconsistency, not a unique slip label: timing, radius, camber, mounting and scale errors can also cause it.
- If all wheel speed signals have an equal scale error or constant shared slip during nearly uniform travel, zero translational acceleration cannot independently recover absolute speed. A learned prior can guess typical behavior but does not guarantee identification.
- Do not impose known slalom cone positions, expected lane width, return-to-start, final heading or endpoint location unless those are explicitly available deployment inputs. GT-fitted constraints would produce attractive plots without answering the agreed IMU reconstruction task.

## Generalization and measurement gates

Confirm actual CSV encoding before physically interpreting acceleration or doing INS preintegration; user-confirmed acquisition range is ±2 g, but reported resting norm near 8200 remains unexplained. Obtain sensor-frame rotations and lever-arm vectors, examine saturation, and measure acquisition clock behavior. Training-derived empirical scaling can remain an explicit comparator, not a verified SI-unit conversion.

Use training-participant cross-validation for architectural decisions, holding dates together by participant. Reserve the repeatedly inspected validation cohort for development reporting, not a new blind claim. Preserve reference support masks and score coverage; mask reference gaps but never reset the trajectory when the reference returns. A final paper generalization claim needs fresh participants or another genuinely untouched cohort under a frozen protocol.

Full-trial 1–10 mm IMU-only reconstruction remains unproven. The first useful outcome is identifying and reducing the remaining 10–20 cm drift without adding reference feedback. If a measured external observation is later introduced, name that as a separate aided-reconstruction task and use an independently justified reference.
