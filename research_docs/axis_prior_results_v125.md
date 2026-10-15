# v125: separate speed/yaw prior results

Matched TRAIN XY ATE: v124 **128.872854348 mm** -> selected **127.531627048 mm**.
Selected `speed1_yaw10`; 1.040737% lower.
All207 recordings/12 people/15 No20/314498 scored frames retained.

| Readout | ATE mm | Heading degrees | Eligible |
| --- | ---: | ---: | --- |
| v124 | 128.872854 | 2.031726 | True |
| speed1_yaw10 | 127.531627 | 2.030136 | True |
| speed10_yaw1 | 128.156224 | 1.990411 | False |
| speed3_yaw3 | 127.563048 | 2.005905 | False |

## Method

Kept v124 trial-RMSE/heading loss, v121 prior/normalization, fixed16-state
reservoir, frozen v34 motion, caps, original folds/clocks/crops/support.
Changed only the speed/yaw prior strengths: exactly (1,10), (10,1),
(3,3), specified before fitting. Reproduced all207 trajectories for
v34/v121/v124 first. Fit only on the other participants with twelve
GN/IRLS iterations and fitting-only line search. Selection requires
lower equal-person ATE than v124 and every original5% guard against
ALL THREE controls. No participant/maneuver identity enters inference.
Synthetic checks verify all34 gradients including saturation, exact
scalar equivalence, deterministic monotone fits and exact prior.

## Guard failures

- `v124`: none; all regression guards pass.
- `speed1_yaw10`: none; all regression guards pass.
- `speed10_yaw1`: v34/participant_ratios/No.6=1.072868653; v34/participant_ratios/No.8=1.058988709; v121/participant_ratios/No.6=1.079589249; v124/participant_ratios/No.6=1.074681047
- `speed3_yaw3`: v34/participant_ratios/No.8=1.054332801

## Matched maneuver results

| Maneuver | v34 mm | v121 mm | v124 mm | Selected mm |
| --- | ---: | ---: | ---: | ---: |
| 10x5 | 213.012753 | 200.952444 | 199.044546 | 197.905779 |
| AR | 82.337381 | 81.279294 | 80.693283 | 79.377908 |
| CR | 48.908680 | 47.861096 | 47.187084 | 45.527361 |
| OS | 172.261638 | 165.829649 | 163.765664 | 159.683933 |
| PS | 212.642211 | 212.649340 | 213.828770 | 218.188540 |
| SL | 183.757434 | 184.242203 | 182.593032 | 177.106518 |
| ST | 81.643976 | 80.007338 | 79.684663 | 79.801970 |

| Participant | v124 mm | Selected mm | Benefit mm |
| --- | ---: | ---: | ---: |
| No.1 | 98.514266 | 97.946232 | +0.568035 |
| No.13 | 131.720048 | 131.100203 | +0.619845 |
| No.15 | 204.135825 | 203.787155 | +0.348671 |
| No.16 | 161.283671 | 159.502866 | +1.780805 |
| No.17 | 114.337619 | 110.357225 | +3.980394 |
| No.19 | 137.238375 | 134.110697 | +3.127678 |
| No.20 | 125.828980 | 121.130408 | +4.698571 |
| No.3 | 134.910579 | 134.823419 | +0.087160 |
| No.4 | 103.957556 | 104.523841 | -0.566284 |
| No.6 | 108.310998 | 108.062998 | +0.248000 |
| No.7 | 145.154513 | 143.973166 | +1.181346 |
| No.8 | 81.081821 | 81.061315 | +0.020506 |

## Evidence limits

11/12 participants improve against v124.
Descriptive bootstrap95 benefit interval: [0.47660653872152386, 2.3121062306913256]mm.
Exact sign-flip fraction: 0.006347656.
These are conditional post-selection TRAIN summaries. Repeated development
exposure,266 inherited parent training records, offline future context,
optical crops and unresolved clocks/acquisition/runtime identity remain.
v12199.303735166mm remains the best completed exposed validation result.
No new validation/test scoring, deployment, commit or push.
All supplementary metrics/availability denominators are retained in
`outputs_axis_prior_v125_report/grouped_metrics.csv`.
Independent screen review: `research_state/v125_independent_review.json`.

## Frozen callable bundle

`models/axis_prior_v125`.
All207 public inference reproductions and optical/identity poisoning checks pass; maximum motion difference 0.
These full-TRAIN package checks are distinct from participant-fold scores.
Model JSON SHA256: `7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2`.
