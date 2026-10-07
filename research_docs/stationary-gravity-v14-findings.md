# Initial gravity feature experiment, v14

The training-only feature diagnosis led to a CPU temporal residual comparator. All original caches, optical masks, timestamps, base calibration, and selected ridge artifacts are unchanged. Initial gravity and gyro bias are estimated only from the first five seconds of the original IMU acquisition, before optical-overlap cropping, using the declared stationary-candidate gate. Missing candidates fall back to the shared training-date gravity and bias.

## Initialization finding

| Partition/date | Accepted recordings | Eligible initial stationary candidates |
|---|---:|---:|
| Train Sept9 | 95 | 87 |
| Train Sept11 | 27 | 25 |
| Train Sept19 | 144 | 84 |
| Train Sept24 | 105 | **1** |
| Train Sept25 | 102 | **0** |
| Validation Sept24 | 36 | **0** |
| Validation Sept25 | 35 | **1** |

The earlier 117/207 target-training stationary coverage used **any** time in a recording. The original acquisition first five seconds provide almost no usable initialization periods for the paper-target recordings. The first-five-second assumption is therefore unsupported here. A quiet period later in an offline recording could supply IMU-only attitude information under a separately declared algorithm, but was not used by v14.

## Measured comparison

| Model | Overall position RMSE | SL position RMSE |
|---|---:|---:|
| Paired CPU ridge | 116.899 mm | approximately 145.5 mm |
| Fixed-fold-selected temporal residual | **112.622 mm** | **136.853 mm** |

Position means improve for all four validation participants: No10≈83.45 mm, No14≈105.48 mm, No18≈144.54 mm, No5≈117.01 mm. Overall heading RMSE improves 1.484→1.423°. No18 heading RMSE increases slightly; the position gain is not a uniform heading improvement.

Selection used the existing four-person training fold before validation, retaining the zero-correction candidate. Selected minimal gravity rotation, penalty0.1, gain0.25; inner participant-mean RMSE162.362→154.970mm, worst-person regression2.42%. The inherited ridge and calibration saw those fold people previously, so selection is conditional. All 18 nonzero matched candidates and the zero control are preserved.

Features contain center accelerations/gyros, wheel speeds, ridge forward/yaw, wheel/chassis yaw disagreement, wheel acceleration, explicit vertical-gyro yaw projection and its ridge difference, and initialization eligibility, sampled at ±0.5/±0.25/0 seconds. Gravity defines a vertical axis but does not determine the chair's forward yaw. Translation and yaw residuals are fitted; lateral prediction remains the ridge output. Norms, coefficients, caps are fitted using the fit partition, then refitted on all training data after selection. The algorithm consumes no later reference at inference.

**Interpretation:** this is a promising temporal residual gain, not proof that per-recording initial mounting calibration solved the target cohort. Almost every target recording used the fallback. Older training acquisitions had substantially greater initial eligibility, so gravity handling can alter the fitted model even when target inference largely falls back. A shared-feature versus initialization-aware fold ablation and independent repeats are needed to attribute the gain.

## Preserved failure and inference

The first attempt prepared all training inputs and scored the control, then failed before its first nonzero fit because two-channel target weighting had a NumPy broadcasting error. No validation was opened. The attempt's executed source/log are preserved in `outputs_stationary_gravity_v14_initial_attempt/`; the fresh runner fixes the weighting and declares explicit vertical projection before any nonzero fitting.

`stationary_gravity_inference_v14.load_stationary_gravity()` reproduces CPU inference and accepts a supplied `initialization` dictionary obtained by the IMU-only startup algorithm, or `startup_imu` with original acquisition t/raw/imu_valid sampled at100Hz. Missing history explicitly falls back to the shared training-date gravity/bias; reproduce the sealed benchmark by supplying its actual initialization, including the one eligible validation recording. It never reads reference fields. `outputs_stationary_gravity_v14/initialization.json` and `training_initialization.json` preserve the actual initialization audits for reproduction. Data for another recording must use that recording's sensor startup, not a dictionary inferred from its reference.

The report is exploratory development evidence on repeatedly inspected validation participants, not a millimeter-accuracy claim or an untouched paper test. No test recordings were opened.

## Image inspection after inference reproduction

I read the paired trajectory, position-error, heading-error and speed figures in `outputs_stationary_gravity_diagnostic_plots_v14_readable/`; all candidate metrics reproduce the sealed trial table within1e-8m. No18 PS2 improves only447.95→433.19mm; its braking displacement deficit remains about531mm at the end. No14 SL1 worsens136.86→145.57mm and No18 SL1 worsens164.02→175.13mm; both retain a late negative heading bend. Thus all participant-average gains do not mean every path is repaired. The first diagnostic straight-path figure had crowded Y ticks; a separate readable figure set adds empty Y extent while retaining equal geometric aspect and unchanged data.
