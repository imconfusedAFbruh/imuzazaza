# Best trajectory method for this wheelchair dataset

Research date: 2026-10-03. Scope: three IMUs, 2D hub-midpoint trajectory, one allowed optical initial pose, no later optical correction. Existing training/validation reports were read; no test signals or new models were opened. This is a recommendation for investigation, not a claim of a universally best estimator.

## What the actual experiments establish

The observed-reference ridge is the current robust control: 116.898 mm equal-participant mean trial position RMSE. The endpoint-loss ensemble reaches 114.057 mm overall but worsens SL from 145.482 to 147.682 mm and two participants. The empirical bias-state comparator is much worse at 230.680 mm. These are exploratory results on repeatedly inspected validation participants, not blind paper estimates. See `outputs_build_v9/report.md` and `docs/build-v9.md`.

The current ridge maneuver means are PS 195.817 mm, 10x5 166.591 mm, SL 145.482 mm, OS 109.398 mm, AR 98.225 mm, ST 73.634 mm and CR 68.286 mm. Participant No.18 averages 147.954 mm versus No.10 90.250 mm. This distribution argues for calibration robustness and accumulated speed/yaw error diagnosis across maneuvers rather than optimizing SL pictures alone. These figures come from `outputs_build_trajectories_v9/model_0_maneuvers.csv` and `model_0_participants.csv`.

`pipeline.calibrate` currently selects one gyro axis per sensor and date; wheel midpoint speed is subsequently jointly fitted from the two selected axes. Center gravity is a single training median, not a full time-varying attitude estimate. Later planar networks already receive signed three-axis chassis gyro features, so the proposal is a constrained calibrated projection/robustness comparison, not the first use of those channels. Thus a small mounting tilt or changed gravity direction is a concrete plausible source of cross-participant errors. This is an inference from implementation, not a measured causal attribution.

## Primary research and applicability

### Wheel-INS2: best-matched physical starting point

Citation identity is verified: original **Wheel-INS**, Xiaoji Niu / Yibin Wu / Jian Kuang, is [arXiv 1912.07805](https://arxiv.org/abs/1912.07805), DOI 10.1109/TVT.2021.3108008. **Wheel-INS2**, Yibin Wu / Jian Kuang / Xiaoji Niu, is [arXiv 2012.10593](https://arxiv.org/abs/2012.10593), DOI 10.1109/TITS.2022.3220508. The latter was accepted online in 2022 and appears in the 2023 journal volume. The [authors' official repository](https://github.com/i2Nav-WHU/Wheel-INS) explicitly distinguishes these methods and the third measurement-model paper. Existing notes labeling 2012.10593 as Wheel-INS2 are correct.

Wheel-INS2 studies dual wheel IMUs, a wheel/body pair and a triple arrangement. It estimates navigation, attitude, residual bias and scale errors, and uses relative IMU position constraints. It explicitly models wheel-to-center lever-arm vectors and mounting angles; therefore a 4 cm off-center wheel IMU is not intrinsically incompatible. Its experiments calibrated mounting and measured lever arms in advance. The triple arrangement's reported 0.73% traveled-distance drift is not trajectory RMSE or a millimeter guarantee. A wheel/body pair achieved 0.69%, showing that simply adding sensors does not ensure improvement. [Authors' paper](https://arxiv.org/html/2012.10593).

For this project, a validated full estimator requires actual CSV-to-SI encoding, three mounting rotations, complete lever-arm vectors and sensor noise/bias characterization. A scalar offset and empirical gyro scale are insufficient to claim reproduction. The failed v9 yaw-bias comparator did not implement this full model.

### TLIO: most useful learned-estimator lessons

TLIO predicts interval displacement and uncertainty, then estimates pose, velocity and bias jointly. It gravity-aligns inputs and trains with bias/gravity perturbations. Longer contexts reduced prediction MSE but increased temporal error correlation and did not necessarily reduce trajectory error; its filter inflates measurement covariance for overlapping outputs. It reports failures for motions absent from training, including rolling on a chair. This supports domain-specific retraining, correlated-measurement handling and robustness augmentation, not importing pedestrian checkpoints. [Authors' paper](https://arxiv.org/html/2007.01867), [authors' code](https://github.com/CathIAS/TLIO).

### RoNIN and newer pedestrian methods

RoNIN provides a large human-motion dataset and several neural architectures. That establishes a useful comparative family, not transfer accuracy for wheel-mounted spinning sensors. This project already tried a RoNIN-inspired residual network; its name does not establish better trajectories. [Authors' paper](https://arxiv.org/abs/1905.12853), [authors' code](https://github.com/Sachini/ronin).

The newer ReNiL uses a motion-aware orientation filter with accelerometer, gyro and magnetometer inputs, walking-cycle windows, and variable-interval displacement/uncertainty inference. Its pedestrian results cannot be directly applied to this six-axis wheelchair recording protocol. Its interval uncertainty ideas are research candidates; the orientation and walking priors require replacement. [Authors' paper](https://arxiv.org/html/2508.06053).

### Wheelchair-specific skid correction deserves a faithful baseline

Van der Slikke et al. use wheel/frame redundancy: compare wheel-derived acceleration with chassis acceleration for concurrent skid; during turns compare each wheel's frame-center estimate using measured chassis rotation and adapt wheel weights. Corrections sometimes worsened normal-speed/collision cases. This is closer to the device arrangement than generic RL. Its displacement/kinematic outcomes are not evidence of 8 mm whole-path RMSE on this dataset. The 2.5 m/s² acceleration threshold requires verified units; it cannot be copied into unknown raw counts. [Authors' institution-hosted paper](https://repository.tudelft.nl/file/File_a9e38cd0-ca20-48ae-ab3a-f8056b64a4ee).

### Offline factor graphs: useful implementation, conditional information

GTSAM CombinedImuFactor couples poses, velocities and bias evolution using preintegrated IMU data. This can implement a properly calibrated offline smoother. It is not a guarantee that weak wheel constraints and learned outputs create independent absolute position information. [Official documentation](https://borglab.github.io/gtsam/combinedimufactor/).

## Recommended next intervention

**First build a mounting/attitude/bias robustness comparator around the existing successful predictor.** Replace the center single-axis yaw feature with a training-fitted, regularized 3-axis gyro projection; estimate gravity direction from validated stationary intervals and an accelerometer-gated attitude filter; perturb empirical raw gyro bias, small mounting rotations and sensor scale during training. Perturbation ranges must come from training variation or documented acquisition uncertainty. Do not import TLIO SI ranges while CSV units remain unverified. Recompute consistent physical features instead of perturbing only already-derived channels. Preserve the original predictor as a control.

Choose the comparator using participant folds entirely inside training; refit every learned calibration/base/normalization within each fold. Use three fixed seeds. Report full trajectory, local relative displacement, heading drift, final-observed displacement, turn/straight error, every participant and every maneuver. Promote only a consistent improvement over the fixed control, not a favorable picture or best seed.

**Then implement a faithful wheelchair skid comparator and interval uncertainty calibration.** Wheel/chassis disagreement can indicate slip, geometry errors, tilt or scale error; it is not a unique slip label. Permit lateral motion during skids. Estimate uncertainty calibration on training folds before uncertainty-weighted fusion, with overlapping interval correlation explicitly handled. A stationary update requires sensor evidence and cannot assume a fixed first five seconds.

**Longer-term target:** calibrated wheel/body navigation plus domain-trained interval SE(2) motion/uncertainty in a conservative offline smoother. This is the strongest defensible methodological direction from the sources, not yet the measured best model. Do not use cone layouts, final positions, known closed paths or optical gap endpoints at inference. No RL priority is supported: logged IMU/reference data already provide supervised motion targets, whereas RL would additionally require a trustworthy dynamics/reward environment and leakage-safe validation.

For reliable global 1–10 mm accuracy, no cited IMU-only result establishes feasibility for these sports maneuvers and sensors. External localization would change the information available and the study protocol. Under the current initial-pose-only protocol, prioritize reducing the measured 10–20 cm drift while honestly reporting uncertainty.
