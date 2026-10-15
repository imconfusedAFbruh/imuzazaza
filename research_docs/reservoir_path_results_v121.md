# v121: nonlinear temporal model beats the strongest retained TRAIN baseline

Frozen v34 matched TRAIN ATE132.240200mm ->129.739811mm (1.89% lower).
All207 recordings/12people/all15No20 retained; every original guard passes.
This is a measured improvement, not a claim of groundbreaking performance or
universal superiority. No new validation/test evaluation has been performed.

| Penalty | Equal-person ATE mm | Heading RMSE deg | Worst person ratio | Eligible |
| --- | ---: | ---: | ---: | --- |
| 0 | 132.240200 | 2.083097 | 1.000000 | True |
| 0.1 | 131.913282 | 2.278375 | 1.573990 | False |
| 1 | 127.490837 | 2.019101 | 1.118657 | False |
| 10 | 129.739811 | 2.044960 | 1.033559 | True |

Penalty1 obtains127.490837mm but fails participant guards; it is rejected.
Selected penalty10 worstperson+3.356%, worstmaneuver+0.264%; P95position
ratio0.981494, last-supportedendpoint0.980206, heading0.981692.

| Maneuver | Matched v34 ATE mm | v121 ATE mm | Change |
| --- | ---: | ---: | ---: |
| 10x5 | 213.012753 | 200.952444 | -5.662% |
| AR | 82.337381 | 81.279294 | -1.285% |
| CR | 48.908680 | 47.861096 | -2.142% |
| OS | 172.261638 | 165.829649 | -3.734% |
| PS | 212.642211 | 212.649340 | +0.003% |
| SL | 183.757434 | 184.242203 | +0.264% |
| ST | 81.643976 | 80.007338 | -2.005% |

## Method and route to this result

v119/v120 improved a weaker physics baseline. The new comparison directly
reproduces the retained v34 weight0.75 model, all207 exact historical scores
and support counts before scoring candidates. Frozen parent models preserve
their inherited266 additional training-record dependence; new residual fitting
uses only identified TRAIN people, excluding each held participant fold.

A fixed16-state leaky tanh recurrent reservoir encodes central gravity-rotation
IMU features, with fit-only normalization and seeded fixed recurrent weights.
A joint forward/yaw readout is optimized against exact accumulated XY/heading
trajectory error. Eight analytic GaussNewton steps with fitting-only line search
replace short-interval/derivative-only objectives. Caps.05m/s and.02rad/s,
three preregistered ridge penalties.1/1/10; no maneuver labels or identity at
inference. Optical labels are used only for fitting and evaluation.

Independent reviewer checked all34 Jacobian columns (maxerror9.04e-10),
all207x4 trajectory support/core metrics, fitting exclusions and hashes. All
candidate predictions and perperson/maneuver results are preserved. See
research_state/v121_review.json and v121_preparation_notes.md for audit and
the two preserved pre-fit path/manifest lookup failures.

## Actual model artifact

models/reservoir_path_v121_completed contains the full-TRAIN readout fit at selected
penalty10 on all207 identified records, with the frozen full v34 parent.
Use reservoir_inference_v121.load_reservoir_model()(sensor). Startup IMU
initialization is supplied or computed from original startup history; an
optical initial pose is supplied separately only for integration.
Full TRAIN inference reproduction: 207 recordings; maximum motion difference0.
Optical/identity-field poisoning leaves inference unchanged. These package
reproduction checks are not held-out accuracy measurements.

## Package completion and provenance repair

The first package attempt saved the full-TRAIN coefficients, then stopped at
a strict legacy pipeline hash check. Only sensor metadata and report prose
had changed; numerical pipeline functions were unchanged. The incomplete
models/reservoir_path_v121 bundle and original source copies remain preserved.
Completion reused its coefficients and normalization without another fit.
Two exact reviewed provenance transitions allow the corrected pipeline and
the verification-only ridge loader edit. Other hashes still fail closed;
historical manifests were not rewritten. New dependencies are sealed.
All207 sensor-only predictions and per-record optical/identity poisoning
checks pass. See research_state/v121_package_review.json for package review.

## Comparison scope and next evaluation

Recorded inventory:125 complete207-ID historical candidate groups,116 with
v34 frame counts. New selected score is below their recorded means, including
rejected v33tilt0.3 at131.460088mm. Exact paired baseline support is verified
for v34; equal counts alone do not prove every historical mask/time mapping.
See research_state/v121_comparator_inventory.json for all paths/hashes/groups.

v34 historical validation remains100.702119399mm on71 exposed recordings.
Do not compare that directly to129.739811 TRAIN. Candidate is frozen and ready
for one explicitly authorized matched validation comparison, with no retuning
or reserved-test use. No promotion/commit/push occurred. Independent clocks
remain unresolved; offline/future-context/crop/calibration inheritance persists.
