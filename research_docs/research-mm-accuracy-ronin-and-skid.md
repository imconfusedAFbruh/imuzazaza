# Millimeter accuracy, RoNIN and skidding correction

Research date: 2026-10-03. Primary sources and a training/validation-only experiment. No fresh test result or global-best guarantee is claimed.

## Decision

Continue the IMU reconstruction project, but change the next priority from larger networks to **measurement validity, timing, lateral motion and observability**. Millimeter full-recording trajectory RMSE has not been demonstrated with these sensors. A faster GPU increases experimental throughput; it does not supply missing position information or correct reference and timestamp errors.

For an application that actually requires approximately 1–10 mm absolute trajectory accuracy, evaluate an external position observation system under the actual camera geometry, working volume, occlusion and marker mounting conditions. Optical tracking is a plausible laboratory option; calibrated vision/fiducials are a candidate for a different deployment setting. Neither purchase nor sensor fusion guarantees 1 mm. The external system's measured uncertainty, time alignment and hub-marker offset must fit the error budget. Feeding Qualisys to the estimator continuously changes the experiment from IMU-only reconstruction to externally aided reconstruction; the same Qualisys trajectory cannot then serve as an independent accuracy reference without accounting for shared measurements.

## RoNIN is relevant, but not a millimeter result

RoNIN includes ResNet, LSTM and TCN variants and a pedestrian inertial dataset collected from 100 subjects. The authors' unseen-subject RoNIN benchmark reports ATE of 5.14 m for ResNet, 5.32 m for LSTM and 5.70 m for TCN. These task-specific values are not directly comparable to this project's shorter wheelchair trajectories, and they do not support a millimeter claim. [Authors' project and result tables](https://ronin.cs.sfu.ca/), [paper](https://arxiv.org/abs/1905.12853).

The official implementation rotates calibrated accelerometer and gyroscope streams using orientation quaternions into a shared frame, then predicts two horizontal velocity components. Its ResNet/LSTM/TCN options are documented in the repository. Wheelchair adaptation requires a sensor orientation estimate available at inference, participant separation and no continuous MoCap rotation of inputs. A ResNet trained on the current physical features is RoNIN-inspired, not an exact reproduction or a valid use of pedestrian pretrained weights. [Official implementation and usage](https://github.com/Sachini/ronin), [global-speed preprocessing](https://github.com/Sachini/ronin/blob/master/source/data_glob_speed.py).

## Physical limits and lateral skidding

Wheel-INS uses wheel-mounted gyro rotation to aid INS and reports maximum horizontal position drift below 1.8% of traveled distance in its experiments. This is relative drift over its routes, not 1.8% RMSE or universal accuracy. Its benefit from rotation modulation does not establish millimeter reconstruction for these wheelchair sensors. [Wheel-INS paper](https://arxiv.org/abs/1912.07805).

Wheel-SLAM explicitly identifies continuing drift without external correction and uses repeatable terrain roll features for loop closure. Such constraints are additional information; an ordinary wheel trajectory may lack them. [Wheel-SLAM paper](https://arxiv.org/abs/2211.03174).

Slip-compensated navigation is a legitimate direction. Earlier work learns wheel-slip behavior alongside a delayed-state pose estimator using relative pose information; learned correction must have information that distinguishes slip from other systematic errors. [CMU authors' publication](https://publications.ri.cmu.edu/aiding-off-road-inertial-navigation-with-high-performance-models-of-wheel-slip).

**Inference for this experiment:** wheel-center yaw disagreement can reveal inconsistent measurements, but does not uniquely identify slip. Wheel radius/scale, hub track assumptions, sensor bias, frame errors and timing can produce the same discrepancy. Equal wheel slip during approximately constant-speed straight travel can be consistent with little acceleration and no yaw discrepancy; those channels alone cannot reliably establish absolute speed. Lateral skidding also violates the current integrator's zero body-side velocity assumption. Correcting forward speed and yaw cannot represent arbitrary sideways translation. Ground-truth sideways velocity should be audited in training and validation before introducing a three-component motion model.

## Why RL is not the first estimator here

RL formalizes actions, resulting transitions and reward. The current recordings supply measurements and reference trajectories; they do not establish a wheel-control action space or measured counterfactual transitions for alternative controls. A policy for preventing physical skidding would require suitable interaction data or a validated simulator and a controlled evaluation. [OpenAI RL concepts](https://spinningup.openai.com/en/latest/spinningup/rl_intro.html).

Offline RL can fail when it assigns value to actions absent from the fixed dataset; the TD3+BC authors specifically address out-of-distribution action value error. Relabeling a supervised speed correction as an RL action does not add missing observability. [Fujimoto and Gu, primary paper](https://arxiv.org/abs/2106.06860).

**Recommendation:** supervised motion/slip residual estimation is the direct experiment available now. Revisit RL if the objective becomes physical skid prevention or sequential estimator decisions with a validated reward and environment; compare it against supervised trajectory loss under identical leakage controls.

## First-order error budget: derived examples, not measured floors

For a straight route at speed v over duration T, approximate endpoint contributions are:

- Clock error: e approximately v times delta-t. At 1 m/s, 1 ms corresponds to 1 mm of temporal displacement. Initial anchoring can cancel a constant lag in perfectly uniform straight motion, so this is a local sensitivity, not an inevitable whole-trial floor.
- Constant velocity error: endpoint e approximately delta-v times T; continuous-time trajectory RMSE approximately absolute(delta-v) times T divided by square-root(3). For 1 mm RMSE over 30 s, constant velocity error would need to be below about 0.058 mm/s.
- Initial heading error: RMSE approximately v times T times absolute(delta-theta) divided by square-root(3). At 1 m/s over 30 s, 1 mm requires approximately 0.0033 degrees under these idealized assumptions.
- Constant yaw-rate bias b: small-angle lateral endpoint e approximately v times b times T squared divided by 2; position RMSE approximately absolute(v times b) times T squared divided by square-root(20). At 1 m/s over 30 s, 1 mm RMSE requires approximately 0.000285 degrees/s.

The terms are correlated in real trials, so they are not a sum of guaranteed independent error bounds. Turning and varying motion change the expressions. They show why sensor conversion, clock stability and orientation matter before adding parameters.

The current offline peak synchronizer uses a 25 ms candidate offset grid. That is not a demonstrated millisecond timing uncertainty. Residual timing, affine clock drift and packet timestamp semantics need measurement, preferably a hardware event captured in both systems. Finer numerical search alone cannot make noisy or ambiguous peaks precise.

Qualisys provides camera calibration residual checks; its documented default warning threshold is 3 mm. That threshold is not a claim that each point is accurate within 3 mm or a bound on this dataset. Calibration residual, marker placement and hub offset, camera geometry, occlusion, frame validity and independent reference uncertainty must be recorded before a 1 mm accuracy claim. [Qualisys calibration-quality documentation](https://docs.qualisys.com/qtm/content/project_options/calibration_quality.htm), [manufacturer calibration tutorial](https://cdn-content.qualisys.com/2018/02/8-How-to-calibrate.pdf).

## Executed supervised skid-proxy experiment

Code: `skid_experiment.py`. Checks: `python test_skid_experiment.py`. Results: `outputs_skid_v4/report.md` and `selection.json`.

Frozen v2 calibration, features, synchronization and accepted recordings are reused. Training only fits setup-specific wheel-derived yaw coefficients, participant/date-balanced residual regression, normalization, clipping caps and the disagreement gate scale. Validation evaluates a predeclared finite grid: three disagreement-gated wheel-yaw blends plus nine supervised nonlinear ridge corrections with three regularization strengths and three correction gains. No test cache is opened. Inference features are instantaneous or inherited causal physical features and TCN outputs; no reference trajectory is an input.

The fixed TCN remains validation-selected. The best added ridge correction scores 0.375118 m; the best wheel-yaw fusion scores 0.391987 m. The exact frozen TCN score and all candidate results are recorded in the output report. The corrections show no validation improvement and should not replace it. These results do not rule out genuine supervised lateral slip estimation or a properly observed INS, and they do not prove the recordings contain physical skidding.

## Next evidence needed

1. Confirm CSV count/scaled units and actual sensor settings from firmware or a controlled static/rate experiment. Record saturation and clipping during maneuvers.
2. Establish sensor acquisition timestamps and both-system clock uncertainty with a shared event; quantify across the entire trial rather than only one alignment offset.
3. Measure the hub-marker geometry and sensor orientations; report whether C3D XY is the floor plane and whether markers remain rigid on the frame.
4. Audit lateral velocity and an ideal zero-side-velocity reconstruction on development participants. If the ideal model itself misses by centimeters, change the motion representation before choosing architectures.
5. If millimeter absolute accuracy is mandatory, measure an external correction system's uncertainty in the intended volume and use an independently justified reference.
6. Freeze the selected method and evaluate new participants. The existing test cohort has already informed development history; it cannot become blind again.
