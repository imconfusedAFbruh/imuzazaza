# Conservative robust motion v120: accepted TRAIN development model

New user request on11October2026 authorized renewed model development afterv119.
Selected fixed global gain0.075 of frozen delta3 robust corrections. No maneuver
labels or optical values enter motion inference. This is a verified improving
TRAIN development model in the frozen v52 family, not a demonstrated replacement
for retained v34 on its separate validation evaluation.

| Gain | Equal-person ATE mm | Heading RMSE deg | ST change | Eligible |
| --- | ---: | ---: | ---: | --- |
| 0 | 147.746508 | 1.836665 | +0.000% | True |
| 0.05 | 146.753294 | 1.831167 | +2.718% | True |
| 0.075 | 146.296429 | 1.829010 | +4.128% | True |
| 0.1 | 145.866966 | 1.827184 | +5.569% | False |

## Selected model by maneuver

| Maneuver | Baseline ATE mm | v120 ATE mm | Change |
| --- | ---: | ---: | ---: |
| 10x5 | 289.927042 | 287.160861 | -0.954% |
| AR | 85.954470 | 84.396641 | -1.812% |
| CR | 47.178747 | 46.170594 | -2.137% |
| OS | 123.811474 | 117.164081 | -5.369% |
| PS | 204.147641 | 202.749152 | -0.685% |
| SL | 206.667073 | 202.491672 | -2.020% |
| ST | 81.831921 | 85.209570 | +4.128% |

## How the model was obtained

1. Freeze v52 participant-fold wheel-speed calibration and offline projected-yaw
   baseline, original clocks, optical initialization and scoring support.
2. v119 fits existing causal hysteresis features to forward/yaw residuals using
   shared robust weights, ridge1, eight IRLS updates and TRAIN-only normalization.
   Delta3 had the lowest overall TRAIN score, but gain0.25 failed the ST guard.
3. v120 preregistered only gains0.05/0.075/0.10; retained coefficients/features
   and caps0.1m/s/0.05rad/s. Gain0.075 is the lowest-ATE eligible candidate.
   Gain0.10 fails ST; there is no maneuver-specific selector or retuning.
4. All207 recordings/12people/all15No20 remain present with exact same masks.
   Every person and maneuver stays within5%; overall P95position, last-supported
   endpoint and heading also pass. This is descriptive TRAIN development evidence.
5. Export models/conservative_robust_v120 with exact three research-fold replicas.
   Sensor-only inference reproduces all207 held motions; maximum difference8.88e-16.

Call conservative_robust_inference_v120.load_fold and predict_motion; bundle
README/model_card document inputs and scope. It is not a full-data deployment
refit, and selecting/averaging fold models for a new user has not been evaluated.

Independent review: passed; see research_state/v120_review.json.
No new validation/test scoring, deployment, commit or push. Retained historical
v34 remains100.702119399mmATE/49.726226563mmroute on71 exposed validation trials.
The all207 independent-clock gate remains unresolved; inherited calibration,
crop and offline filter dependencies remain. No significance/superiority claim.

Next: further development is authorized by the latest user request; do not
repeat completed v119/v120 grids. Preserve the selected model and exact guards.
A validation comparison or full-data deployment milestone requires an explicit
evaluation decision consistent with prior no-validation/no-promotion scope.
