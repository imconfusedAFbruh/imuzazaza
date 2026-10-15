# Full-record IMU preprocessing: v80-v82, 8 October 2026

## Completed and decision

Three bounded cycles completed: v80 proves evaluator-crop invariance; v81 refits the fixed simple yaw model in TRAIN participant folds; v82 reproduces predictions and reviews support, metrics and plots. This is a correctness improvement to experimental preprocessing, **not a promoted trajectory estimator**. Retained historical v34 remains **100.702119399 mm synchronized XY ATE** and **49.726226563 mm route RMSE**, on its separate 71 previously exposed validation trials. No validation or reserved-test signals were read in this run. No commit/push qualifies; HEAD remains `87b85e6`.

The falsifiable hypothesis was that filtering center acceleration on the complete sensor-only timeline removes the optical-crop dependency found in v79 and improves held-person localization. The first part is supported; the accuracy benefit is small and the main clock regressions remain.

## How the result was obtained

`native_projection_v80.py` reuses `imu_streams`, `sample_streams`, the existing device/packet clock reconstruction and the exact v52 0.3 Hz, second-order, offline gravity projection. It applies projection to the full common L/R/C sensor record before optical cropping. The C3D evaluator maps this already-computed sensor motion using frozen offsets. No optical motion, future optical reset, route constraint, fitted alignment or new acquisition is introduced.

All 207 original TRAIN recordings were checked against hash-verified old/new caches and raw source hashes. Raw samples agree exactly; projected sensor yaw agrees exactly at shared physical sensor times under both crops. The synthetic regression failed on the legacy crop-first filter, then passed on full-record filtering. Sensor gaps and unsupported extrapolation remain unavailable. `masked_interp` conservatively requires both neighboring sensor samples valid, even at an exact-grid query immediately after a gap; accepted real-data assertions passed, so no scoring support changed here.

`native_refit_v81.py` preserves both frozen clocks, v52 yaw weight 1, all participant folds, identical legacy label masks and stride-five label sampling. The unchanged physical calibration is reused from hash-verified v72 fold models, whose fitting participants exclude held participants; recalculating an identical calibration would add no evidence. Projected yaw scale/intercept are refitted inside the same folds. No hyperparameter search or new architecture family. This remains conditional on inherited clock bootstrap, geometry and QC; it is not full pipeline nesting.

Saved v73 native C3D times, observed positions/headings, reference masks, IMU support and the single permitted initial optical pose are unchanged. Original observed C3D is primary. No processed-assisted score is calculated in this intervention; its distinct lower-confidence v76 results remain unchanged. The v74 full metric contract is reused, including bias/LoA, R²/Pearson and unavailable-value reasons. Genuine acquisition endpoints remain unavailable on all 207 crops; last-supported error is reported separately.

## Verified results

Participant-balanced mean trial metrics, TRAIN207 / 12 participants; these cannot be ranked against historical v34's validation scope.

| Metric | Cropped/new clock | Native/new clock |
|---|---:|---:|
| Synchronized XY ATE RMSE, mm | 147.697253 | 147.565311 |
| Position MAE, mm | 127.546708 | 127.412139 |
| RMSE X / Y, mm | 113.001247 / 80.208977 | 112.996136 / 80.159856 |
| Last-supported endpoint error, mm | 193.837472 | 193.689244 |
| RTE 1 / 5 / 10 s, mm | 75.071171 / 99.641703 / 77.032171 | 75.050488 / 99.193773 / 77.031340 |
| Yaw RMSE, degrees | 1.834858 | 1.830730 |
| Speed RMSE, m/s | 0.087030 | 0.087030 |
| Angular velocity RMSE, degrees/s | 1.950000 | 1.949598 |
| Synchronized position P95, mm | 241.922918 | 241.739485 |
| Geometric route RMSE, mm | 60.292338 | 60.195813 |
| Supported path-length error, mm | 337.009541 | 337.009541 |
| Observed reference coverage, % | 87.310343 | 87.310343 |

RTE eligibility is 207 / 106 / 12 trials at 1 / 5 / 10 s. Genuine endpoint error and genuine endpoint drift/path length are unavailable, not zero. All 207 availability-flagged trials include partial endpoints; those flags are not catastrophic failures. Before scoring, this run additionally declared diagnostic gates: no >5% participant/maneuver or aggregate P95/route/last-supported endpoint/RTE10 regression and no new trial crossing 1 m ATE or 1 m last-supported endpoint. The new 1 m gate is a prospective diagnostic safeguard, not an established historical criterion. New-clock ATE has zero >1 m trials; last-supported endpoint has two, unchanged. Old-clock ATE has one, unchanged. No trials or frames disappear.

Native/new improves by **0.131942 mm (0.0893%)**, with 7/12 participants improving; No.20 worsens 0.4909%, the largest matched-clock participant regression. Slope aggregate improves 0.8359%. Native/old slightly worsens **156.001639 -> 156.018832 mm**, failing the primary improvement gate. Both outcomes are retained, so a universal accuracy gain is rejected.

Against the original old-clock control, native/new still fails the frozen 5% participant guard: **No.13 +9.0216%, No.17 +7.9888%**. Correcting crop dependence does not resolve their timing/model interaction. Do not select a favorable clock from ATE or claim promotion because the matched new-clock mean decreased.

## Review and validation

v82 independently computes sum-of-squares ATE for 414 new predictions: maximum disagreement **4.547473509e-13 mm**. Reintegrating saved motion reproduces XY exactly. All 207 reference/support/timestamp arrays and initial poses agree with v73; all four participant-balanced means are independently reconstructed. Forward motion differs from its paired crop control by at most **3.441691376e-14 m/s**.

A separate read-only reviewer checked all 417 v80 and 216 v81 artifact hashes, independently reproduced ATE within 2.28e-13 mm, and confirmed identical support/counts/initial XY. This is separate-context review with inherited task history, not a blinded independent study. It agrees with diagnostic-only classification and identifies the conservative gap interpolation limitation.

Actual No.13 ST2 and 10x5 Trial1 red-IMU/black-C3D trajectory/yaw plots were inspected. ST2 improves ATE **165.641646 -> 135.982373 mm** and yaw **1.786306 -> 1.236749 degrees**, but an early heading discrepancy remains. Long 10x5 changes negligibly: **430.052729 -> 430.033396 mm**. The visuals support a slope boundary correction and reject the claim that crop filtering explains the long-route regression.

Two aborted attempts are preserved: `outputs_native_projection_v80_roundoff_attempt` caught a -2.08e-17 s cancellation at an exact sensor-grid boundary; reconstruction now snaps only differences below 1e-9 s to the existing grid, without changing offsets. `outputs_native_refit_v81_manifest_attempt` caught Windows manifest separator mismatch before any fit. The source/report preserve these errors; successful output directories were never overwritten.

## Reproduction, safety and next run

Executed sequentially under `research_run_guard.py`, which uses atomic exclusive lock creation, run ID, PID/creation-time/command evidence and a 15-second heartbeat. It refuses any existing lock and records completion/failure before releasing its own lock. No unrelated process was stopped. All jobs finished; no persistent experiment remains.

Successful commands (output directories are immutable; do not rerun into them):

```powershell
python test_native_projection_v80.py
python metric_contract_v74.py
python research_run_guard.py native_projection_v80.py native_refit_v81.py
python research_run_guard.py native_review_v82.py
```

The initial combined command completed v80 and stopped on the manifest error; after preserving that attempt, the actual successful refit was `python research_run_guard.py native_refit_v81.py`. Source compilation and regression checks passed. Full metrics, per-trial/participant/maneuver reports, fold checkpoints and manifests are in `outputs_native_refit_v81`; sensor invariance artifacts are in `outputs_native_projection_v80`; numerical review and figures are in `outputs_native_review_v82`.

Three substantive cycles exhausted this run's bounded budget. Next priority is fold-only clock bootstrap and signal/event evidence using invariant sensor features, eliminating inherited held-participant seed fits before any estimator search. Preserve fixed optical scoring support, including No.20 wide-marker recordings. Exact next inspection command:

```powershell
Get-Content research_docs/native_preprocessing_v80_v82.md; Get-Content fold_sync_sensitivity_v71.py; Get-Content observed_sync_experiment.py; Get-Content synchronization_experiment.py; Get-Content native_projection_v80.py
```

Preregister v83's fold-only bootstrap and provenance checks before execution; do not rerun v70/v71/v80-v82 or choose lags by localization error. Remaining historical failed-candidate metric backfill, strict geometry/reference-policy separation, competitor comparability, exact firmware provenance and legacy identities remain unresolved. No published-superiority claim is justified.
