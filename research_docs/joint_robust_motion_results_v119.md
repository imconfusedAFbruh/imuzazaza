# Authorized TRAIN-only robust motion screen v119

User authorized one additional family/max3 configurations. Guarded run completed
all207 TRAIN recordings/12participants/all15 No20, three participant folds.
All207 frozen v52 baseline scores/counts reproduced before candidate scoring.
No new validation/test evaluation, promotion, commit or push.

| Delta | Equal-person XY ATE (mm) | Heading RMSE (deg) | Worst person ratio | Worst maneuver ratio | Eligible |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 147.746508 | 1.836665 | 1.000000 | 1.000000 | True |
| 1.5 | 144.230173 | 1.822717 | 1.001187 | 1.126090 | False |
| 3 | 143.926074 | 1.822725 | 1.003298 | 1.148412 | False |
| 6 | 144.063281 | 1.826479 | 1.004674 | 1.180894 | False |

TRAIN guard-selected delta: 0. This is not promotion.

Method: unchanged causal v56 hysteresis features; residual relative to frozen
v52 speed/projected-yaw baseline; TRAIN-fitting group-balanced normalization;
fixed centered target MAD scales, ridge1, eight shared two-component Huber IRLS
updates, delta1.5/3/6 only; correction caps0.1m/s and0.05rad/s, fixed gain0.25.
Held participants excluded from every residual fit and normalization. All four
motions/positions/headings saved per recording for exact support review.

Acceptance requires lower overall ATE and <=1.05 for every person/maneuver,
overall trial P95position, last-supported endpoint and heading. All207 must
remain represented. Missing support is never dropped or assigned a score.

## Guard details

Delta1.5: Position_P95_mm ratio=0.970796; Last_Supported_Endpoint_Error_mm ratio=0.969024; heading_rmse_deg ratio=0.992406
Person/maneuver violations: ST=1.126090
Delta3: Position_P95_mm ratio=0.968402; Last_Supported_Endpoint_Error_mm ratio=0.967943; heading_rmse_deg ratio=0.992410
Person/maneuver violations: ST=1.148412
Delta6: Position_P95_mm ratio=0.968665; Last_Supported_Endpoint_Error_mm ratio=0.968166; heading_rmse_deg ratio=0.994454
Person/maneuver violations: ST=1.180894

## Every maneuver on identical TRAIN support

| Maneuver | Baseline (mm) | Delta1.5 (mm) | Delta3 (mm) | Delta6 (mm) |
| --- | ---: | ---: | ---: | ---: |
| 10x5 | 289.927042 | 282.529849 | 282.358034 | 282.838366 |
| AR | 85.954470 | 81.708057 | 81.334544 | 81.116221 |
| CR | 47.178747 | 44.455737 | 44.297664 | 44.252243 |
| OS | 123.811474 | 106.498545 | 103.924458 | 101.304157 |
| PS | 204.147641 | 200.700965 | 199.978210 | 198.955438 |
| SL | 206.667073 | 196.068346 | 194.408784 | 193.844205 |
| ST | 81.831921 | 92.150138 | 93.976789 | 96.634818 |

Inherited optical crop/initial pose/clocks and offline projected gravity
proxy remain; this does not resolve the strict all207 timing gate or demonstrate
true attitude, genuine acquisition endpoints or deployment generalization.
Retained historical v34 best remains100.702119399mmATE/49.726226563mmroute on
its separate already-exposed validation evaluation. Do not compare that number
directly with this207 TRAIN-fold mean or treat TRAIN selection as validation.

Independent final review passed: all hashes,207 prediction files/828 unique rows,
exact masks/primary guards and eligibility independently reproduced; see
research_state/v119_review.json. Supplementary diagnostics were not all
independently reconstructed. Numeric budget exhausted: no fourth config,
new family, validation scoring or promotion authorized. Next numerical step
requires separate user authorization; strict timing work requires new linked
independent evidence. Completed unsuccessful timing searches should not repeat.
