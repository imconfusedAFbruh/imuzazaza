# v126: frozen v125 validation results

V125 fails the predeclared dual-control comparison.
Matched equal-person XY ATE: v121 **99.303735166 mm** -> v125 **99.700352275 mm**
(-0.396617109mm benefit, -0.399398%).
Best completed guard-passing validation model: **v121**.
All71 previously exposed validation records/four people/105821 scored frames
retained. No refit, alternative candidate, tuning, test use or deployment.

## Method and frozen identity

The TRAIN-only v125 study fixed speed/yaw prior strengths(1,10), retaining
the v124 trial-RMSE loss, v121 prior/normalization and fixed16-state reservoir.
All207 public inference/poisoning checks and independent TRAIN reviews passed
before this comparison. The model was frozen before validation access.
Candidate model SHA256: `7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2`.
User renewed the model request after the concrete frozen-comparison proposal;
that contextual direction was recorded before execution in frozen_validation_v126.md.
Original IMU startup and both public controls were reconstructed for all71
before any v125 prediction. Frozen v123 tolerances and four-thread CPU were
retained. Identical clocks/crops/reference/support and original single initial
pose were used. Motion prediction received only sensor/setup/IMU initialization.
V125 was then evaluated once, with exact finite support against both controls.

## Equal-person metrics

| Metric | v34 | v121 | v125 |
| --- | ---: | ---: | ---: |
| ATE_RMSE_mm | 100.702119 | 99.303735 | 99.700352 |
| Position_P95_mm | 159.335255 | 156.125865 | 157.831375 |
| Last_Supported_Endpoint_Error_mm | 127.772313 | 124.258881 | 125.688166 |
| heading_rmse_deg | 1.260899 | 1.203765 | 1.214901 |
| Route_RMSE_mm | 49.726227 | 48.715699 | 48.612489 |
| Route_P95_mm | 96.768605 | 93.789526 | 94.084621 |
| RTE_1s_mm | 45.514455 | 43.920490 | 44.821873 |
| RTE_5s_mm | 99.371467 | 98.437431 | 100.689005 |
| RTE_10s_mm | 75.608374 | 71.561472 | 68.685769 |

## Participant results

| Participant | v34 mm | v121 mm | v125 mm |
| --- | ---: | ---: | ---: |
| No.10 | 67.570596 | 67.108134 | 67.326873 |
| No.14 | 96.405508 | 95.408632 | 95.761010 |
| No.18 | 134.341813 | 129.754021 | 130.461703 |
| No.5 | 104.490560 | 104.944154 | 105.251823 |

## Maneuver results

| Maneuver | v34 mm | v121 mm | v125 mm |
| --- | ---: | ---: | ---: |
| 10x5 | 143.900042 | 139.173194 | 138.453833 |
| AR | 87.942655 | 86.725221 | 84.895937 |
| CR | 55.128844 | 53.784685 | 51.097873 |
| OS | 95.004803 | 92.981967 | 97.888157 |
| PS | 188.816248 | 189.749257 | 195.696537 |
| SL | 118.068214 | 119.570739 | 120.775888 |
| ST | 58.404170 | 57.276235 | 59.188371 |

## Original guard decisions

### Against v34: PASS

Failed guards: none.

| Guard class | Group | Ratio |
| --- | --- | ---: |
| participant_ratios | No.10 | 0.996393065 |
| participant_ratios | No.14 | 0.993314720 |
| participant_ratios | No.18 | 0.971117629 |
| participant_ratios | No.5 | 1.007285463 |
| maneuver_ratios | 10x5 | 0.962152830 |
| maneuver_ratios | AR | 0.965355627 |
| maneuver_ratios | CR | 0.926880903 |
| maneuver_ratios | OS | 1.030349562 |
| maneuver_ratios | PS | 1.036439075 |
| maneuver_ratios | SL | 1.022933132 |
| maneuver_ratios | ST | 1.013427144 |
| guard_ratios | Position_P95_mm | 0.990561534 |
| guard_ratios | Last_Supported_Endpoint_Error_mm | 0.983688580 |
| guard_ratios | heading_rmse_deg | 0.963519939 |
### Against v121: FAIL

Failed guards: OS, mean_ATE_not_lower.

| Guard class | Group | Ratio |
| --- | --- | ---: |
| participant_ratios | No.10 | 1.003259509 |
| participant_ratios | No.14 | 1.003693350 |
| participant_ratios | No.18 | 1.005454030 |
| participant_ratios | No.5 | 1.002931741 |
| maneuver_ratios | 10x5 | 0.994831182 |
| maneuver_ratios | AR | 0.978907124 |
| maneuver_ratios | CR | 0.950045032 |
| maneuver_ratios | OS | 1.052764967 |
| maneuver_ratios | PS | 1.031342841 |
| maneuver_ratios | SL | 1.010078968 |
| maneuver_ratios | ST | 1.033384466 |
| guard_ratios | Position_P95_mm | 1.010923938 |
| guard_ratios | Last_Supported_Endpoint_Error_mm | 1.011502476 |
| guard_ratios | heading_rmse_deg | 1.009251335 |

## Availability and uncertainty

| Model/metric | Available records | Available people |
| --- | ---: | ---: |
| v34/RTE_1s_mm | 71/71 | 4/4 |
| v34/RTE_5s_mm | 39/71 | 4/4 |
| v34/RTE_10s_mm | 4/71 | 2/4 |
| v121/RTE_1s_mm | 71/71 | 4/4 |
| v121/RTE_5s_mm | 39/71 | 4/4 |
| v121/RTE_10s_mm | 4/71 | 2/4 |
| v125/RTE_1s_mm | 71/71 | 4/4 |
| v125/RTE_5s_mm | 39/71 | 4/4 |
| v125/RTE_10s_mm | 4/71 | 2/4 |

0/4 participants improve against v121.
Descriptive bootstrap95 benefit interval: [-0.6076789947463968, -0.25214904269567695]mm.
Exact sign-flip fraction: 0.125000000 over 16 signs.
These small-cohort, previously exposed development-validation summaries
do not establish independent significance or blind final generalization.
The TRAIN127.531627048mm result describes a different cohort and is not
directly compared to these validation scores. All diagnostic metrics and
availability denominators are preserved in the grouped CSV. Genuine
acquisition endpoints are unavailable; last-supported endpoint is distinct.
Inherited266 parent training records, offline context/optical crops, and
unresolved independent clocks/firmware/runtime/geometry/final data persist.
No model or prior artifact was changed by this evaluation. The bundle
validation_evaluated=false field records its earlier freeze-time status;
this separate sealed comparison records subsequent evaluation.

Independent review completion is recorded separately in
`research_state/v126_independent_review.json`; sealed run status is historical.
