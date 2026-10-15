# v124: trial-RMSE readout results

Matched TRAIN XY ATE: v121 **129.739810994 mm** -> selected **128.872854348 mm**
(0.668227% lower). Selected `lambda_10`. All207 recordings,
12 participants and all15 No20 retained on the same original clocks/crops/support.

| Readout | ATE mm | Heading RMSE degrees | Eligible |
| --- | ---: | ---: | --- |
| v121 | 129.739811 | 2.044960 | True |
| lambda_0.1 | 129.250415 | 2.207057 | False |
| lambda_1 | 126.775358 | 1.989820 | False |
| lambda_10 | 128.872854 | 2.031726 | True |

## How the model was obtained

Reviewed v121 code and previous rejected models. Kept the fixed16-state temporal
reservoir, TRAIN-fold normalization, .05m/s/.02rad/s correction caps and frozen
v34 motion. Reproduced all207 v34 and v121 motions, trajectories, support and
primary metrics before any candidate fit. Changed the training objective from
mean squared path error to smoothed mean trial XY RMSE plus heading RMSE,
with a quadratic prior at the frozen v121 weights. Three predeclared prior
penalties .1/1/10; twelve GN/IRLS steps and fitting-only line search. Each
held participant stays outside its fit, normalization and prior fitting.
Every original participant/maneuver/tail/endpoint/heading guard must pass
against both v121 and v34. No clock, mask or gate changes.

## Selected result on identical support

| Maneuver | v34 mm | v121 mm | Selected mm |
| --- | ---: | ---: | ---: |
| 10x5 | 213.012753 | 200.952444 | 199.044546 |
| AR | 82.337381 | 81.279294 | 80.693283 |
| CR | 48.908680 | 47.861096 | 47.187084 |
| OS | 172.261638 | 165.829649 | 163.765664 |
| PS | 212.642211 | 212.649340 | 213.828770 |
| SL | 183.757434 | 184.242203 | 182.593032 |
| ST | 81.643976 | 80.007338 | 79.684663 |

| Participant | v121 mm | Selected mm | Benefit mm |
| --- | ---: | ---: | ---: |
| No.1 | 98.135404 | 98.514266 | -0.378862 |
| No.13 | 131.873137 | 131.720048 | +0.153089 |
| No.15 | 204.276934 | 204.135825 | +0.141109 |
| No.16 | 163.747891 | 161.283671 | +2.464220 |
| No.17 | 115.411038 | 114.337619 | +1.073419 |
| No.19 | 138.273231 | 137.238375 | +1.034855 |
| No.20 | 130.129023 | 125.828980 | +4.300043 |
| No.3 | 133.523974 | 134.910579 | -1.386605 |
| No.4 | 105.069849 | 103.957556 | +1.112293 |
| No.6 | 107.818577 | 108.310998 | -0.492421 |
| No.7 | 149.250176 | 145.154513 | +4.095664 |
| No.8 | 79.368496 | 81.081821 | -1.713325 |

All candidate guard ratios are preserved in `outputs_trial_rmse_v124/run.json`.
All historical and v74 supplementary metrics are in the sealed trial table;
`outputs_trial_rmse_v124_report/grouped_metrics.csv` includes equal-participant
overall/participant/maneuver means and explicit availability denominators.

## Uncertainty and evidence limits

8/12 participants improve. Leave-one-person-out mean benefit range
0.554858 to 1.101528mm.
Descriptive bootstrap95 interval [-0.1267963672546642, 1.9408074960778563]; exact paired sign-flip fraction 0.153320312.
These are conditional post-selection TRAIN summaries, without an independent
significance/generalization claim. Historical parent calibration and266 other
training-record dependence persist. Offline future context, optical-dependent
crops and unresolved independent clocks/firmware/acquisition provenance remain.
No v124 validation/test scoring, deployment, commit or push. The completed v121
exposed validation score99.303735166mm stays a separate result.

Independent review status: `research_state/v124_independent_review.json`.
Synthetic checks cover all34 objective derivatives including saturation,
monotone/deterministic fitting, exact-prior and original integration Jacobian.

## Frozen callable bundle

`models/trial_rmse_v124`: selected penalty fitted once on all207 TRAIN
using frozen full-TRAIN v121 prior/normalization and v34 parent.
All207 sensor-only inference reproductions pass; maximum motion difference 0.
Every optical/identity poisoning check passes. These are package reproduction
checks, not held-out scores.

```python
from reservoir_inference_v121 import load_reservoir_model
predict = load_reservoir_model('models/trial_rmse_v124')
motion = predict(sensor)
```

Model JSON SHA256: `ac46f8b82096214da181624f7be0362ddc8494f1b44fa4827c68f01d41421ce7`.
