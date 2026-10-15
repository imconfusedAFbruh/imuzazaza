# v123: frozen v121 passes the matched validation comparison

14 October 2026. Equal-person XY ATE improves **100.702119399 -> 99.303735166 mm**
(1.398384 mm / 1.389% lower), on all71 identical exposed validation
recordings/four participants. Every predeclared guard passes. This is conditional
development validation, not a new blind test or proof of published-method superiority.
No deployment promotion, refit, retuning, alternative candidate, reserved-test
evaluation, commit or push. Independent review status is recorded separately in
`research_state/v123_independent_review.json`; the sealed run retains its at-execution status.

## How this result was obtained

The earlier v121 TRAIN search reproduced frozen v34, added a fixed 16-state
temporal reservoir over gravity-rotation IMU features, and optimized bounded
forward/yaw residuals through exact integrated trajectory loss. Three fixed
penalties were screened in participant folds; penalty10 passed every guard.
Penalty1 had lower TRAIN error but failed participant guards. The selected
readout was fitted on all207 identified TRAIN records and frozen before this
comparison. v122 stability analysis was descriptive, not another selection step.

After explicit user authorization, the evaluation-only v123 runner reconstructed
native IMU startup initialization and reproduced every saved v34 motion, trajectory,
heading, identity, metric and reference/support array before any v121 prediction.
It then evaluated the frozen v121 package once with the same time grid, clock maps,
crop, reference masks and one original optical initial pose. Prediction inputs
contained only sensor/setup/IMU initialization. No optical feedback or alignment.

Two implementation failures were preserved: virtual PyTorch `_ops.py` has no
source file; then a baseline-only check exposed the historical two-thread floating
point residual. Restoring the original v33 producer four-thread configuration
gave exact reproduction without changing any tolerance. Both failed attempts
evaluated zero candidate recordings. The final guarded run completed exit0.

## Matched participant results

| Participant | v34 ATE mm | v121 ATE mm | Change |
| --- | ---: | ---: | ---: |
| No.10 | 67.570596 | 67.108134 | -0.684% |
| No.14 | 96.405508 | 95.408632 | -1.034% |
| No.18 | 134.341813 | 129.754021 | -3.415% |
| No.5 | 104.490560 | 104.944154 | +0.434% |

## Matched maneuver results

| Maneuver | v34 ATE mm | v121 ATE mm | Change |
| --- | ---: | ---: | ---: |
| 10x5 | 143.900042 | 139.173194 | -3.285% |
| AR | 87.942655 | 86.725221 | -1.384% |
| CR | 55.128844 | 53.784685 | -2.438% |
| OS | 95.004803 | 92.981967 | -2.129% |
| PS | 188.816248 | 189.749257 | +0.494% |
| SL | 118.068214 | 119.570739 | +1.273% |
| ST | 58.404170 | 57.276235 | -1.931% |

## Additional outcomes

| Metric (equal-person mean) | v34 | v121 |
| --- | ---: | ---: |
| Position_P95_mm | 159.335255 | 156.125865 |
| Last_Supported_Endpoint_Error_mm | 127.772313 | 124.258881 |
| heading_rmse_deg | 1.260899 | 1.203765 |
| Route_RMSE_mm | 49.726227 | 48.715699 |
| Route_P95_mm | 96.768605 | 93.789526 |
| RTE_1s_mm | 45.514455 | 43.920490 |
| RTE_5s_mm | 99.371467 | 98.437431 |
| RTE_10s_mm | 75.608374 | 71.561472 |
| Scored_Coverage_pct | 87.365367 | 87.365367 |
| C3D_Coverage_pct | 87.365367 | 87.365367 |

P95 position, last-supported endpoint and heading guard ratios are respectively
0.979857630, 0.972502395, 0.954687802.
All are below1.05; every participant and maneuver ATE ratio is also below1.05.
No.5, PS and SL worsen slightly; the favorable mean is not uniform improvement.

`outputs_frozen_validation_v123_report/grouped_metrics.csv` contains all numeric
legacy/v74 metrics at overall, participant and maneuver level. Means exclude
missing values, and every row reports available/total trial and participant
counts. Maneuvers average participant means, not pooled trials. Frame/window
count fields are explicitly mean counts in this table; per-record counts remain
in the sealed trial tables. Unsupported genuine endpoint metrics remain missing.
RTE at different durations can have different eligible records; use denominators.

## Artifacts and limitations

- `outputs_frozen_validation_v123_exact`: all71 paired predictions, baseline audit,
  full per-record metrics, participant/maneuver tables, input/source/output hashes.
- `models/reservoir_path_v121_completed/model.json`: unchanged frozen candidate;
  SHA256 `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`.
- `research_docs/frozen_validation_v123.md`: authorization, fixed tolerances,
  support/guard contract and preserved implementation-failure history.

The full pipeline still inherits calibration and266 parent training records,
offline future context, optical-dependent crop and unresolved independent-clock
and firmware provenance assumptions. These71 validation records have prior
development exposure. Historical test is not blind. Independent final data and
a faithful external comparator remain needed; no further candidate tuning is
authorized by this comparison. The next authorized work is independent review
and evidence consolidation; numerical evaluation is complete.
