# Current same-data evidence and publication limits

## 14 October 2026 — frozen v121 matched validation update

The authorized v123 comparison and independent review are complete: v121 improves
equal-person ATE100.702119399->99.303735166mm on the same71 exposed validation
records/fourpeople, with every guard passing and105821 matched scoredframes.
Baseline motion/trajectories/headings/reference/support reproduce exactly.
Route RMSE49.726226563->48.715699mm. No.5/PS/SL worsen slightly within5% limits.
No refit, retuning, reserved-test evaluation, deployment promotion, commit or push.
See frozen_validation_results_v123.md and ../research_state/v123_independent_review.json.
This supersedes earlier pending-validation and best-candidate status below,
without changing historical results or establishing an external-comparator victory.


9 October2026, v114 reporting checkpoint. This is a living evidence report.
The campaign's requested fair victory over the strongest relevant reproduced
external comparator is **not established**. No external method in the primary
source matrix has a faithful same-data reproduction yet. Published numbers
with different reference points, alignment, datasets or metrics are not a ranking.

## Retained historical comparison

Frozen v21 and training-selected v34 use the same71already-exposed validation
recordings/fourpeople in outputs_dynamic_blend_v34. Equal-person mean trial
synchronized XY ATE is102.585179403 versus100.702119399mm. Retained geometric
route RMSE49.726226563mm is a different measure. v36inference andv77historical
metric audit reproduce the retained result. No new fitting in this checkpoint.

The exact route is v14static/dynamic gravity features, v16integrated endpoint
correction, v21bounded nonlinear products, v33dynamic-gravity model, then v34
motion blend. Three participant-held TRAIN folds select.75from{0,.25,.5,.75}
with worst training-person ratio.993947477. Inference uses IMUs and one permitted
initial optical pose; no later optical reset/alignment/scale fit. Offline future
IMU context and inherited calibration/base/clock/geometry dependencies remain.

v114 reads only sealed participant aggregate CSVs andrun.json. New statistical
analysis is retrospective, not fresh validation. Paired equal-person benefit
is1.883060004mm (1.835606288%). Exactly256paired participant resamples yield
an empirical95%percentile sensitivity interval[-.104118611,4.379743550]mm;
16signflips give two-sidedp=.375 under a symmetric independent-person null.
Fourpeople and prior model/data exposure prevent a prospective confidence or
significance guarantee. The interval includeszero; no significance claim.

| Person | Old minus retained ATE (mm) | Benefit with this person omitted (mm) |
| --- | ---: | ---: |
| No.10 |-.390564072|2.640934696|
| No.14 |5.778882449|.584452522|
| No.18 |1.961594788|1.856881743|
| No.5 |.182326851|2.449971055|

No.10 worsens; most benefit depends onNo.14. These limitations accompany the
headline, rather than being removed by pooling thousands of correlated frames.
See retained_uncertainty_v114.md and sealed outputs_retained_uncertainty_v114.

## Strict TRAIN path and failed hypotheses

All207identifiedTRAIN/12people/all15No20 remain frozen. v80full-record IMU
filtering fixes optical-crop dependence; v81paired refits still fail the original
5%participant guard. v83/v84fresh seed fitting excludes held people locally but
produces199supported clocks and8rejections; inherited reference/QC/selection
remain. v108existing projected feature gives identical acceptance and21newly
unsupported frozen scored frames; no refit/promotion. v109reconstruction is exact.

v113logical reference bound uses sealedmetadata without recomputing events:
sixrejectedIDs lack any reference channel satisfying frozenmotion andtwopeak
requirements. Any IMU-only feature change has a permissive upper bound201/207.
This is a constraint of the chosen algorithm/reference contract, not a proof
that physical timing is unobservable. No further IMU-only feature search can
clearall207whilethese reference/gates remain fixed. No gate was relaxed, no
record removed and no199subset fit. Independent timing evidence or a separately
authorized clock-contract revision is required for this refit branch.

Genuine acquisition endpoints remain unavailable on the comparison crops.
Report last-supported errors separately. Existing full metrics, maneuver/tail/
route/heading/speed and contiguous1/5/10s diagnostics are retained in v74–v77/
v81/v95, with missing motion arrays and processed-reference provenance explicit.
Do not regenerate missing failed-candidate arrays or change the primary reference.

## External comparisons and remaining requirements

The primary matrix now includes2015skid/WISDOM/2022sensor-reduction/
2023wheelrotation andmobility/2025MASSWU/2026threeIMU/Wheel-INS2 sources.
Published angular-rate errors, wheel-distance errors, GPS summaries and long-route
drift percentages do not equal this benchmark's midpoint XY ATE. Single-wheel
Wheel-INS code is not multiIMUWheel-INS2. Source equations, units, full-axis mounts,
sensor lever radius/camber/geometry, clock/pose/support and implementation
availability must be locked before claiming a faithful local comparator.

Exact flashed firmware/runtime range, physical-front geometry, independent
optical uncertainty and legacy identities remain unresolved. Current data's
historical test exposure is disclosed; no new blind result is available.
Within the existing-data-only contract these facts constrain the claim, and
must not be replaced by invented calibration, new acquisition promises or SOTA.
The native campaign goal is usageLimited and unachieved at the06:52Bangkok
scheduled wake-up; the scheduler cannot reset/resume native allowance. No commit/push or new
promotion occurred. Next useful work: consolidate requirement-level evidence
and source-to-local implementation prerequisites; do not rerun failed gates.
