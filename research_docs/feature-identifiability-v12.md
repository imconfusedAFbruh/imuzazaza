# Feature and identifiability audit, v12

## Scope and evidence

CPU-only diagnostics inspect all 473 observed-reference training caches. No validation/test signals are read, and no selected model changes. Sources: `learning.features`, `planar_experiment.planar_features`, `chassis_acceleration_v11.features/prepare/correct`; images read: `outputs_acceleration_diagnosis_v10/acceleration_signals.png` and `outputs_chassis_acceleration_v11_rejected_comparator/braking_comparator.png`. New diagnostics: `outputs_feature_diagnosis_v12/` and `outputs_stationary_mount_diagnosis_v12/`.

## 1. The center gravity frame varies substantially within a date

The current feature extractor subtracts one training-fitted `center_gravity_direction` for every recording from the same acquisition date. It supplies center accelerations/gyros in raw mounting coordinates and does not estimate a per-recording gravity rotation. That assumes mounting/attitude consistency which is not established by the acquisition documentation.

A conservative IMU stationary-candidate audit requires both calibrated wheel speeds below 0.05 m/s, empirically scaled three-axis center gyro norm below 0.1 rad/s, each center accelerometer axis's 1.01-second rolling SD below 0.02 empirical g, valid IMU, and at least one contiguous second. These fixed diagnostic gates were not selected by trajectory error. **117 of 207 Sept24/25 training recordings** contain such candidates. The candidates remain unverified physical stationarity; stationary sensor bias and low-speed creep can pass them.

Among qualifying recordings, participant-median center gravity direction differs from the shared date vector by **1.4–21.6°**, with norm near **0.998–1.003 empirical g**. Examples: No4≈17.4°, No6≈18.0°, No8≈14.7°, No16≈14.0°, No17/20≈21.6°. This is too large to ignore as a feature consistency issue. It does not prove that the mount moved: chair roll/pitch, different chairs, sensor attitude or acquisition handling could contribute. The records lack independent attitude/mount metadata to decide among them.

One static gravity subtraction can therefore leave a participant-dependent apparent horizontal acceleration even during a quiet period. Directly interpreting those channels as linear acceleration or pooling their orientation across a date is unsupported. Accelerometers measure specific force; linear acceleration requires an attitude estimate to remove gravity. [VectorNav, INS operation](https://www.vectornav.com/resources/detail/what-is-an-ins), [IMU measurements](https://www.vectornav.com/resources/detail/what-is-an-inertial-measurement-unit).

## 2. Wheel/chassis yaw disagreement is already large on training data

Mean trial yaw-rate RMSE on observed labels:

| Training condition/date | Wheel-derived yaw | Chassis yaw |
|---|---:|---:|
| Sept24 SL | 0.377 rad/s | 0.052 rad/s |
| Sept25 SL | 0.453 rad/s | 0.034 rad/s |
| Sept24 PS | 0.308 rad/s | 0.050 rad/s |
| Sept25 PS | 0.455 rad/s | 0.045 rad/s |

The wheel-derived yaw uses the difference of two empirically calibrated wheel speeds divided by configured hub spacing. Its wheel-speed intercept asymmetry creates an additional yaw bias. Wheel/chassis disagreement therefore does not uniquely identify slip or a new participant's mount. Track width, wheel speed scales, intercepts, mounting projection, and slip all affect it. It should be an uncertainty feature or a review diagnostic, not an independent measurement to fuse with equal trust. The existing 20 features already include wheel yaw and its disagreement with chassis yaw; merely adding the same proxy cannot create new information.

## 3. Why v11 braking acceleration did not repair the image

The plotted No18 PS2 comparator predicts a short early negative acceleration, then returns close to zero while observed speed still decelerates. The corrected path is almost unchanged. This matches the train-fold rejection of all 24 nonzero smoothers and the tiny rejected-comparator global difference, 116.898→116.918 mm.

The empirical model regresses `d(gt_forward_speed)/dt`, which is a second derivative of filtered optical position, inside derivative-supported segments with additional 150 ms boundaries removed. This target is noisier and less available than pose endpoints. Features include wheel acceleration and a model's wheel-conditioned speed; the smoother's velocity prior is that same model. The putative new measurement is therefore strongly tied to the wheel prior it is supposed to correct. A discrepancy gate cannot detect a missing chassis signal if the learned acceleration has reproduced wheel braking.

A separate conditional training-fold experiment fits per-date participant-weighted ridge acceleration regressors with fixed alpha=0.1. Four existing training participants form the held-out fold, with preprocessing newly fitted on the remaining training participants. It uses the physical base instead of v11's ridge input, so it is a diagnostic approximation, not a reproduction. No neural model or GPU is used.

| Features | All-condition acceleration RMSE | PS acceleration RMSE | PS mean braking bias |
|---|---:|---:|---:|
| Center accel/gyro only | 0.730 m/s² | 0.949 m/s² | +1.241 m/s² |
| Wheel acceleration only | 0.673 | 1.000 | +0.992 |
| Full physical features | 0.612 | 0.915 | +0.901 |
| Center features at −0.3/0/+0.3 s | 0.604 | 0.925 | +1.180 |

PS comprises six qualifying fold trials/three people. Braking is evaluation-only observed acceleration<−0.5 m/s². Positive braking bias means predicted acceleration is insufficiently negative on those frames. Modest center context improves pooled error but does **not** remove the PS braking bias. This does not support turning up v11 smoothing gain.

## Recommended finite CPU experiment

Use the existing four-person training fold and declare all candidates before evaluation:

1. Keep current ridge outputs as the zero-correction control; cache them once outside this CPU diagnostic.
2. Build per-recording IMU-only stationary candidates with the conservative fixed gates above. Estimate center gravity and three-axis gyro bias only from supported candidates; record coverage. If absent, retain shared training calibration and expose a missing-calibration flag. Do not assume the initial five seconds are stationary.
3. Compare shared-date features against per-recording centered center channels, then optionally a minimal gravity-aligned representation. Gravity alone cannot determine forward yaw; do not invent a full mounting rotation from its vector. A train-fitted forward projection or documented mount is required.
4. Fit a small temporal ridge residual directly to forward velocity and yaw, rather than acceleration. Fixed context offsets −0.5/−0.25/0/+0.25/+0.5 seconds, ridge penalties 0.1/1/10, gains 0/0.25/0.5. Cap residuals with fit-participant quantiles. Keep lateral unchanged for this controlled comparison.
5. Select by equal-participant integrated path RMSE with <=5% worst-person regression, report PS and heading separately, and preserve every candidate. Add observed endpoint heading/displacement equations only after the centered-feature comparison succeeds. No optical pose enters inference beyond the initial pose.

This targets the measured mounting/gravity inconsistency and removes a noisy acceleration objective. It is a hypothesis, not a promise of improvement. Verify the empirical raw encoding and physical mount independently before presenting it as a calibrated INS. Repeated validation remains exploratory; no per-date switch or high-error exclusion is justified by this diagnosis.
