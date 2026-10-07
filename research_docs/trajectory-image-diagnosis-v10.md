# Image-led trajectory diagnosis, v10

## Evidence inspected

I inspected `outputs_build_trajectories_v9/sl_comparison.png` at image resolution. Twelve SL panels show a consistent pattern: the endpoint ensemble removes the current model's downward transverse displacement for Sept24 participants No5/10, but introduces an upward final-loop bend for Sept25 No14/18. This is not simply a plotting alignment mistake: the plot uses the same observed scoring frames, initial pose, equal axes, and no later reference resets. Black-line breaks represent unavailable reference, and should remain visible.

I ran `trajectory_image_diagnosis_v10.py` on 35 Sept24/25 training SL recordings and 12 validation SL recordings. Predictors received only setup, timestamps, raw sensors, and IMU validity. No test recordings were opened. Optical data was used afterwards for diagnosis. Results are in `outputs_trajectory_image_diagnosis_extended_v10/diagnostics.csv`, `channel_variants.csv`, and `summary.json`. The earlier diagnostic output is also preserved.

## The channel causing the visible regression

Equal-participant mean SL position RMSE, mm:

| SL subset | Current ridge | Full endpoint | Endpoint forward only | Endpoint lateral only | Endpoint yaw only | Endpoint forward+yaw |
|---|---:|---:|---:|---:|---:|---:|
| Sept24 training | 219.5 | 138.9 | 212.7 | 209.6 | 151.7 | 142.4 |
| Sept25 training | 240.3 | 190.0 | 213.2 | 242.2 | 210.6 | 181.4 |
| Sept24 validation | 150.1 | 85.5 | 141.3 | 127.3 | 93.7 | 85.2 |
| Sept25 validation | 140.8 | 209.8 | 128.7 | 159.4 | 182.5 | 178.1 |

These substitutions use the named model's one channel with the other channels from the ridge. They are diagnostic comparisons, not independently selected models. The yaw change produces most of the Sept24 gain and Sept25 regression. Forward velocity alone improves both validation dates. The new lateral channel further harms Sept25.

Sept25 validation heading RMSE rises from **1.70° to 2.68°**. Its mean fitted heading-error trend changes from **−0.072°/s to −0.197°/s**. The first third of the path improves slightly, **68.6 to 59.0 mm**, while the last third deteriorates **164.5 to 327.3 mm**. That matches the late upward bend visible in the image. These trends are descriptive, not proof of a constant sensor bias.

## The unsupported intervals matter

Mean endpoint-minus-ridge integrated yaw change over complete SL recordings, degrees:

| Subset | Intervals with derivative support | Remaining intervals |
|---|---:|---:|
| Sept24 training | −0.261 | −0.086 |
| Sept25 training | −0.713 | −2.058 |
| Sept24 validation | −0.858 | −0.637 |
| Sept25 validation | −0.472 | −2.275 |

The support mask requires observed derivative/lateral labels at both neighboring frames. Remaining intervals include actual optical gaps and filtering boundary margins. It is incorrect to call every remaining interval missing optical position. Roughly **83% of the net yaw correction on Sept25 validation lies outside derivative-supported intervals**. This percentage decomposes the predictor difference; it does not establish the true yaw error there. Optical endpoint orientations are available to evaluate accumulated error without inventing intermediate labels.

Meanwhile, on supported Sept25 validation labels, mean yaw-rate error looks good: endpoint **−0.0009°/s**, versus ridge **+0.0319°/s**. A near-zero mean error on the available labels therefore does not establish accurate whole-recording heading. Dense point losses and global average-bias diagnostics can miss the intervals that dominate accumulated path error.

## Why a date-specific constant correction is not yet supported

The endpoint's training heading-error trend is positive on both dates, **+0.077°/s and +0.061°/s**. Validation Sept25 has the opposite sign, **−0.197°/s**. Subtracting a positive training-date mean yaw bias would push that validation trend further negative. A fixed date-selected bias or choosing one model per date after inspecting these participants would amount to development tuning. The data does not justify calling the date alone the cause; participant motion, IMU bias distribution, and support pattern are confounded.

## Actionable correction

1. Retain the ridge as the control. Do not promote the full endpoint ensemble or a validation-picked channel splice from these images.
2. Separate the yaw correction head from translation and lateral heads. Train local relative-heading endpoint targets explicitly across supported pose endpoints, including endpoints bracketing optical gaps. Add a conservative regularizer toward the calibrated chassis yaw on uncertain intervals. Any reliability gate must use IMU features at inference, never the optical support mask.
3. Select correction caps and gate strength on participant folds, with an explicit worst-participant heading/path objective and reporting by acquisition date. Refit all preprocessing inside folds for a genuinely independent comparison; inherited frozen calibration saw the old inner participants.
4. Add realistic train-only gyro-bias perturbations to the IMU channels and regenerate corresponding calibrated input features. Keep pose targets unchanged. Bias sensitivity should be checked before learning an unconstrained long-interval yaw residual. Select perturbation bounds from stationary training IMU measurements, not validation path error.
5. Use IMU-validated stationary periods for recording-specific zero-angular-rate bias observations where present. Do not assume the first five seconds are stationary, and do not set yaw to zero merely because forward speed is small: the chair can rotate in place.
6. Only consider uncertainty-aware offline fusion after the independent yaw correction passes these checks. A raw-IMU filter and a network using the same IMU have correlated errors.

The bias augmentation and correlation concern have primary-source support in [TLIO, system design and training](https://arxiv.org/html/2007.01867). TLIO jointly estimates pose, velocity, and IMU biases using learned relative displacement and uncertainty, and explicitly discusses reusing the same IMU signal in propagation and neural updates. Its headset/pedestrian results are not evidence that an uncalibrated wheelchair implementation will achieve the same accuracy. The recommendations above are an inference from that method and the measured wheelchair failure pattern.

## Plot improvements

Preserve the truthful trajectory overlay. Add start/end marks, direction arrows, time coloring, and a paired position/heading error timeline. For the Sept25 failure, annotate the late divergence rather than rotating or scaling the predicted path to match the reference. Show reference support separately from derivative support. State that these are 71 repeatedly inspected validation recordings; exclude test trajectories from development displays.

The current figure has enough image resolution and correct geometry to establish the failure. The fix belongs in yaw generalization and uncertainty handling, not cosmetic trajectory alignment.
