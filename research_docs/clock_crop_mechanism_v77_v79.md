# v77-v79: historical metrics and clock/crop mechanism

## Protocol, outcome and scope

Three prespecified deterministic research cycles completed; no new parameter fits/search or promoted estimator. v77 adds the tested v74 metric contract to sealed v34/v42/v32 artifacts. v78 tests first-order clock phase under fixed coefficients and identical initial optical pose on TRAIN207. v79 transports old-cache predictions to the new clock and compares raw/wheel controls with projected yaw on identical physical sensor support. No reserved test read. v77 reads already-exposed validation predictions for metric audit only, not tuning; v78/v79 access TRAIN only.

v77: 781 rows, 11 source-model combinations, 71 previously exposed validation trials each. Per-trial ATE/count checks pass; independent direct sum-of-squares maximum difference 5.551115123125783e-17 m. Eleven participant-balanced means independently reconstructed without the shared aggregation helper. Retained v34 remains 100.702119399 mm. Common-native v42 old blend100.592598441 versus refit94.661739566 mm remains rejected by the existing training-person guard; own-clock and native-common scopes stay separate. Stored-supervision v32 remains rejected102.585179403 ->105.172052325 /110.932464656 mm. No new model ranking or winner claim.

## Retained v34 expanded metrics

| Metric | Value |
|---|---:|
| ATE_RMSE_mm | 100.702119399 |
| Position_MAE_mm | 87.224011739 |
| RMSE_X_mm | 66.189063006 |
| RMSE_Y_mm | 67.610611093 |
| Last_Supported_Endpoint_Error_mm | 127.772313328 |
| RTE_1s_mm | 45.514455339 |
| RTE_5s_mm | 99.371467131 |
| RTE_10s_mm | 75.608373996 |
| Yaw_RMSE_deg | 1.260899061 |
| Speed_RMSE_mps | 0.052206064 |
| Angular_Velocity_RMSE_degps | 2.489607159 |
| Position_P95_mm | 159.335254909 |
| Route_RMSE_mm | 49.726226563 |

Genuine acquisition endpoint inclusion is not established by these saved artifacts; genuine endpoint/drift remain unavailable. Listed endpoints are last-supported. RTE and derivative/filter definitions are v74 diagnostics, separately versioned from legacy metrics. Full machine-readable metrics, eligibility, participant/maneuver distributions and null reasons are saved. Speed/omega LoA are descriptive per-trial correlated-frame summaries, not independent-sample confidence intervals. All accepted trials remain present.

## v78 falsifiable phase hypothesis

For the same fitted model and shared initial pose, first-order clock shift predicts delta-position = delta-offset times [world velocity(t)-world velocity(0)-initial omega times J times displacement(t)]. This uses prediction motion, not C3D motion. The relative heading counterpart is delta-offset times [omega(t)-omega(0)]. No post-hoc trajectory alignment or correction is performed; this is a mechanism diagnostic, not an estimator candidate.

All207 initial XY/heading equality checks passed.154 clocks change. Median changed-clock position difference7.955476182mm; median first-order remainder0.083154734mm. Median explained squared-difference fraction0.999815206. This is a per-trial median descriptive approximation, NOT percentage IMU-C3D accuracy, NOT squared correlation, and NOT evidence a selected clock is physically correct. Moving initialization magnifies phase sensitivity: No.13 10x5 Trial1 first-second speed0.923316m/s;65.3ms clock change yields138.375337mm fixed-model position difference, remainder4.045372mm. No.17 10x5 Trial1 gives63.048707mm difference/remainder2.502094mm.

The first-order model is incomplete for slopes. No.13 ST2 has96.228628mm actual prediction difference and47.749679mm first-order remainder (explained fraction0.753775); No.17 ST2 fraction0.106390. Do not hide these exceptions or infer all prediction differences are pure time shifts.

## v79 crop-dependent filter hypothesis

Old and new cached samples were transported by the recorded clock offset, without choosing a lag from ATE. All207 recordings retained. Matched raw RMS maximum1.9566267704581804e-10 counts, wheel-speed RMS maximum7.0817083631456436e-15m/s: raw acquisitions and linear motion controls agree on shared sensor support. Yet gravity-projected yaw-rate RMS reaches0.863376361deg/s. No.20 ST2 crop boundaries move70ms, yaw difference0.863376deg/s overall,1.701207deg/s within1s edges versus0.025304deg/s interior. No.13 ST2 initial crop moves-40ms, yaw difference0.608054deg/s overall,1.126730deg/s edge versus0.055485deg/s interior.

Code root cause: pipeline.prepare clips and starts raw arrays according to optical overlap/support before projected_yaw_folds_v52.proxy applies its offline0.3Hz lowpass independently on that cropped array. Different optical clocks change physical IMU crop boundaries and hence filter boundary conditions. Existing optical-input poisoning changes optical fields after cropping, so it does not detect this upstream dependence. The earlier v73 comparison must be interpreted as clock-plus-crop-preprocessing, not a pure clock-only intervention.

Conclusion: supported filter-boundary confound, with slope outliers. Sensor units, mounting signs and physical yaw agreement are still not certified. This is not proof that the entire100mm error comes from filtering, nor that a full-timeline filter will improve held-person ATE. Native full-record sensor preprocessing is the next justified controlled fix. No smoothing reset, post-hoc heading fit or optical motion input is allowed.

## Visual review and adversarial review

Viewed actual No.13 ST2 trajectory_yaw.png: red IMU accumulates yaw error early and remains roughly1.5-2degrees from black observed reference; XY lateral deviation persists along the slope. The plot supports an early heading problem but cannot assign it exclusively to crop-filter differences. Diagnostic transport has its own eligible support and is not used to change official C3D masks or exclude trials. Saved original old/new controls remain156.001639 ->147.386863mm for identical old coefficients on TRAIN207; the earlier refitted new/new147.697253mm still fails No.13/17 guard. No new original-reference score is claimed.

Adversarial review performed in the same context; numerical verification uses independent direct formulas and aggregation, not an independent reviewer agent. Fold models and prediction/cache hashes were checked. Optical-dependent clock/QC/bootstrap and geometry remain inherited. Historical validation exposure and uncertainty limits are explicit. Diagnostic explanation success is not estimator promotion, and no Git commit/push qualifies.

## Reproduction, next step and budget

Executed: python historical_metrics_v77.py; python clock_phase_v78.py; python crop_filter_v79.py. Outputs are immutable completed directories; do not rerun these commands into existing paths. Synthetic v74 checks plus source/aggregate checks are in tests.log. Full CSVs, participant/maneuver tables, dashboards and manifests are under outputs_historical_metrics_v77, outputs_clock_phase_v78, outputs_crop_filter_v79. Metrics for unchanged controls are explicitly identified; transport diagnostics are separate.

Three-cycle session budget exhausted. Next experiment: compute gravity/projected yaw on the full native IMU timeline using pipeline.imu_streams/sample_streams before optical cropping; assert its motion is invariant under evaluator clock/crop changes; then perform a frozen matched-support TRAIN-fold refit with no more than the prescribed configurations. First establish preprocessing correctness, then compare ATE/route/endpoint/RTE/yaw/tails and the5%person guard. Remaining older failed v58-v64 full-suite availability/backfill remains unfinished.
