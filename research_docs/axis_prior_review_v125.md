# v125 independent review closure

15 October 2026. Source preflight, guarded TRAIN screen, selected full-TRAIN
package, public inference reproduction, reporting and both independent reviews
are complete. Older model/source artifacts and existing dirty work are preserved.

## Accepted result and rejections

Selected speed prior1/yaw prior10: equal-person participant-fold TRAIN XY ATE
127.53162704843507mm versus v124128.87285434811182mm, a1.341227300mm /1.040737%
improvement. All207 recordings/12 people/15No20/314498 scored frames remain.
Every original participant/maneuver/P95/last-supportedendpoint/heading guard
passes against all three controls v34/v121/v124. Speed10/yaw1 is rejected for
No6/No8; speed3/yaw3 is rejected for No8 versus v34. No criteria were relaxed.

The runner reuses the exact v124 loss and v121 motion/Jacobian/frozen prior.
Three synthetic tests pass:136 central finite-difference derivatives including
saturation, exact scalar(3,3) objective/fit equivalence, exact prior, monotone
and deterministic fitting. Independent source preflight found no screen blocker.

## Independent screen checks

`research_state/v125_independent_review.json`: PASS.
Standalone checker `research_state/review_axis_prior_v125.py`, guarded exit0.
Verified224 output/642 input/20 source hashes plus all224 frozen v124 outputs.
All inherited source hashes unchanged; exact original IDs, fold exclusions,
normalizations,621 pre-fit reproduction records and permitted fit histories.
Independently reconstructed1242 paired predictions' supports, saved-motion
integration, caps, unchanged lateral and64584 metric values;1863 exact control
array comparisons. All core selection metrics, original guards, participant/
maneuver tables and winner were reconstructed. Direct RTE, distance-relative,
path and coverage diagnostics were also checked. New-candidate route/Frechet
and filtered derivative values were retained but not independently recomputed.

## Frozen package and report checks

`models/axis_prior_v125/model.json` SHA256:
`7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2`.
Selected once-only full207 fit uses frozen full-TRAIN v121 prior/normalization.
All207 predictions from the actual unchanged public loader match expected motion
exactly, with maximum difference0; all207 optical/identity poisoning checks pass.
This is full-TRAIN inference reproduction, distinct from held-person accuracy.

`research_state/v125_package_report_review.json`: PASS, guarded exit0.
Verified6 bundle outputs/451 inputs/36 dependencies,3 report outputs/12 inputs,
all207 saved inference/poisoning records and all8520 grouped rows/denominators.
96 groups lack values;660 have partial availability. All three bundle files
supporting package claims are recorded report inputs. Reviewed package source
pins the accepted screen source hashes before fitting and checks input/dependency
maps separately afterward. This provenance improvement was made before fitting;
the frozen v124 sources and reports were not changed.

The reviewer independently reconstructed11/12 participant benefits, mean
1.341227300mm, leave-one-person-out range1.036014..1.514637mm, seed1224096-draw
bootstrap95[.476606539,2.312106231]mm and exact26/4096 sign flips. The reviewer
inspected the saved PASS outputs and source hashes and reported no blockers.
The package/report reviewer did not repeat fitting or public inference.

## Wording clarification and evidence boundary

The sealed report says "twelve" GN/IRLS iterations. Interpret this as the
preregistered maximum: the unchanged fitting-only zero-step rule stops one
selected fold/setup after10; remaining selected fold/setup fits and both full-
TRAIN setup fits run12. README/state use "up to twelve". Preserve the sealed
report and source hashes; no scoring rerun is justified by this clarification.

No4 worsens.545% versus v124, PS2.039%, ST.147%; all remain within5%.
No8 versus v34+4.929492% remains close to the guard. Conditional post-selection
TRAIN statistics do not certify independent significance or generalization.
No validation/test scoring, deployment, commit or push occurred. Frozen v121's
99.303735166mm remains the best completed exposed validation result. Original
independent timing, firmware/runtime identity, geometry/final-data requirements,
offline context, optical crops and266 inherited training records remain.

Next: `research_docs/frozen_validation_decision_v125.md` is a concrete single-
candidate evaluation proposal requiring the separate validation authorization.
