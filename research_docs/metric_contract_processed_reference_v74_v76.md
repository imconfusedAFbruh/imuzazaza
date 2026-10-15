# Metric contract and stored-processed reference audit: v74-v76

## Scope and decision

Three substantive cycles completed on 8 October 2026: v74 metric correctness, v75 frozen prediction backfill, v76 secondary-reference audit. No estimator fitting or promotion. No validation or reserved-test signals read. Historical retained v34 remains 100.702119 mm on its previously exposed 71-trial validation scope; it is not comparable to the TRAIN207 scores here. No Git commit/push: the new authorization permits only promoted validated estimator improvements. Existing dirty changes remain local.

v75 covers four frozen v73 model/clock cells, 207 accepted TRAIN recordings, 12 participants, 828 trial-model rows. Every ATE and frame count reproduces the historical parent exactly (maximum ATE difference 0 m). v76 evaluates the same predictions against different secondary support: it is not a paired estimator improvement.

## Metric correctness and definitions

Official aggregation: mean of participant means of per-trial valid-frame Euclidean position RMSE. Secondary numeric aggregates use the same available-trial hierarchy; summaries explicitly give eligible trials/people, trial SD, median/IQR. X/Y are the existing world coordinate frame; signed longitudinal/lateral errors project onto valid C3D heading. Route metrics retain existing within-supported-run rules and no gap bridges. Position and route P95 remain separate.

RTE v74: every 1 s start; 1/5/10 s contiguous valid native C3D windows; both relative displacement vectors rotated by reference starting heading. These sampling counts differ from the legacy RPE diagnostics, which are preserved separately and must not be silently interchanged. Eligibility is 207/106/12 trials respectively, across all four cells. The 10x5 maneuver has zero eligible 5 s windows on primary observed support. It is N/A, not zero.

New velocity diagnostic: native-time gradient followed by offline Butterworth order 2 lowpass at 6 Hz (or 0.4 sampling rate if lower), independently per supported run, excluding 0.15 s edges. It differs explicitly from legacy position-filter-then-gradient targets. The initial synthetic constant-speed check exposed a 0.000101 m/s edge bias with the legacy order; the new diagnostic procedure passes constant speed exactly. Historical targets and ATE are untouched.

All 207 comparison arrays end before the original C3D acquisition endpoint. Genuine endpoint metrics and normalized genuine drift are null with reasons; prior values called endpoint are last-supported endpoint errors. Supported path length excludes gaps, with a 1 m denominator threshold. Last-supported normalized errors are separate diagnostics and flag fragmented denominators. Crop coverage is not full raw recording coverage.

Bias/LoA are descriptive correlated-frame summaries within trials; summary means of these trial statistics are not pooled LoA. Prediction R2 is 1-SSE/SST, not squared Pearson. Constant-signal R2/Pearson are null. No independent-frame confidence intervals or prospective-generalization claim is made. Trial distribution summaries and paired participant differences describe uncertainty; inferential uncertainty has not been certified for these reused folds.

## Original observed support: old/old versus new/new

| Metric | Old model / old clock | New model / new clock |
|---|---:|---:|
| ATE_RMSE_mm | 156.001639 | 147.697253 |
| Position_MAE_mm | 134.399212 | 127.546708 |
| RMSE_X_mm | 121.122498 | 113.001247 |
| RMSE_Y_mm | 80.590194 | 80.208977 |
| Endpoint_Error_mm | N/A | N/A |
| Endpoint_Drift_pct | N/A | N/A |
| Last_Supported_Endpoint_Error_mm | 201.238131 | 193.837472 |
| Last_Supported_Normalized_Endpoint_pct | 2.898942 | 2.638438 |
| RTE_1s_mm | 81.912117 | 75.071171 |
| RTE_5s_mm | 102.585095 | 99.641703 |
| RTE_10s_mm | 76.697682 | 77.032171 |
| Yaw_RMSE_deg | 1.861919 | 1.834858 |
| Speed_RMSE_mps | 0.093159 | 0.087030 |
| Angular_Velocity_RMSE_degps | 2.163027 | 1.950000 |
| Position_P95_mm | 255.912082 | 241.922918 |
| Route_RMSE_mm | 62.691260 | 60.292338 |
| Route_P95_mm | 125.990366 | 119.228108 |
| Sampled_Hausdorff_mm | 227.725899 | 216.893339 |
| Maximum_Run_Frechet_mm | 267.772167 | 256.951001 |
| Within_Run_Arc_Length_RMSE_mm | 140.541810 | 135.208068 |
| Path_Length_Error_mm | 356.447549 | 337.009541 |
| C3D_Coverage_pct | 87.310343 | 87.310343 |

## Stored processed / recovered reference

Original primary samples remain unchanged. Residual >0 plus camera support and frozen geometry defines observed; stored residual-zero coordinates are a lower-confidence processed category. Positive residuals without required populated camera support remain unverified, and invalid/geometry-rejected samples remain excluded. No new interpolation, filtering, C3D rewrite or deployed optical correction occurs.

207 source hashes and 207 classification sidecars verified. Primary frames: 318,034; additional stored-processed frames: 92,153. Crop participant-balanced reference coverage: 87.310343% primary versus 99.914087% secondary. No filename-tagged *processed*.c3d files were found under c3d; stored reconstructed coordinates exist in ordinary C3D files. Reconstruction algorithm, whether interpolation/filtering was used, and uncertainty remain unknown. Residual-zero does not establish an independently observed position.

| Frozen model/clock | Original ATE (mm) | Secondary ATE (mm) |
|---|---:|---:|
| new_model_new_clock | 147.697253 | 165.376107 |
| new_model_old_clock | 156.538460 | 174.993303 |
| old_model_new_clock | 147.386863 | 164.891413 |
| old_model_old_clock | 156.001639 | 174.189159 |

All four scores worsen with secondary support. This does not prove the stored reference is wrong or estimator accuracy decreased: prediction is identical and support changed. No benefit to original-observed evaluation has been established. Additional training supervision is withheld because processing provenance is insufficient; existing v32 processed-supervision fits were already rejected (102.585179 to 105.172052 / 110.932465 mm historical validation). Do not repeat without new evidence.

## Visual and adversarial self-review

The actual reference_comparison.png was viewed: No.13 10x5 trial 1 includes a conspicuous gray stored-processed spur below the observed route and a final processed yaw discrepancy. Red IMU loop geometry also departs from observed black curves. The tail discrepancy cannot be assigned solely to estimator or reconstruction without reliable optical provenance. Neither curve was aligned or fitted for display.

Self-review was performed in the same agent context, not independently. The historical new/new mean improves but No.13 +10.476104% and No.17 +8.037741% violate the frozen 5% guard. Maneuvers 10x5 (279.665306 to 290.086738 mm), AR, CR, SL and ST regress despite OS/PS improvement. New RTE10 rises slightly. No tail, participant, endpoint or coverage issue is hidden. All 207 trials stay visible. Failure_Flags describe reference/inference availability, not a preregistered catastrophic-error count; that count is unavailable until a frozen definition exists.

The all-null endpoint summary caused a reporting KeyError after saved trial metrics completed; fixed in shared summary collection, then resumed from saved JSON with exact ATE/count verification. A plot used the wrong date initially; corrected to the actual saved September 25 recording. Both failed attempts are retained in the session record; neither affected estimator outputs.

## Reproduction and artifacts

Run `python metric_contract_v74.py`; `python backfill_metric_contract_v75.py` resumes existing saved trial results and verifies against v73 before regenerating summaries. Run `python review_metric_contract_v76.py` to verify source hashes, sample classification, comparison tables and figure. Full v76 reference scoring is `python processed_reference_audit_v76.py` only in a fresh output path; never overwrite a completed directory.

Artifacts: outputs_metric_contract_v74/tests.log; outputs_metric_contract_v75/{trial_metrics.csv,maneuver_summary.csv,participant_summary.csv,dashboard.csv,paired_participant_differences.csv,run.json}; outputs_processed_reference_v76/{trial_metrics.csv,maneuver_summary.csv,participant_summary.csv,reference_audit.csv,reference_flags/,dashboard.csv,paired_participant_differences.csv,verification.json,reference_comparison.png}. Hash manifests preserve provenance.

Backfill coverage is currently v73/v72 frozen cells only. Older eligible v34/v42/v32 and rejected v58-v64 predictions remain to be checked for available saved motion and rescored; missing inputs must remain null with reasons. This is not a claim that the whole historical project has already received the full suite.

## Next task

Session budget of three substantive cycles is exhausted. Highest priority: complete metric backfill on older eligible saved predictions, then signal/event and moving-initial-pose sensitivity for No.13/No.17. Do not select clocks by localization RMSE or train a network before bootstrap/geometry leakage issues are settled.
