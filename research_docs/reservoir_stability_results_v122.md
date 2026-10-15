# v122: stability of the frozen v121 TRAIN improvement

Executed the preregistered descriptive audit using only sealed participant summaries. No new fit, model selection, trajectory evaluation, or validation/test access.

The selected v121 model improves matched equal-person TRAIN ATE from 132.240200 to 129.739811 mm: a 2.500389 mm (1.891%) reduction. Nine of twelve participants improve. All 207 recordings, including all 15 No.20 recordings, remain included.

Leaving out any one participant retains a positive mean benefit, ranging from 1.538987 to 3.111803 mm. Nevertheless, the 4,096-resample paired participant bootstrap interval is [-0.068061, 5.368020] mm and includes zero. The two-sided fraction among all 4,096 sign flips is 0.118652344.

| Participant | Baseline minus v121 ATE (mm) | Mean benefit omitting participant (mm) |
| --- | ---: | ---: |
| No.1 | 4.081876 | 2.356618 |
| No.13 | 0.953243 | 2.641039 |
| No.15 | 6.743332 | 2.114667 |
| No.16 | 9.017390 | 1.907934 |
| No.17 | 3.405946 | 2.418066 |
| No.19 | 0.785703 | 2.656270 |
| No.20 | -4.225165 | 3.111803 |
| No.3 | -2.395101 | 2.945434 |
| No.4 | 0.001615 | 2.727550 |
| No.6 | 0.675390 | 2.666298 |
| No.7 | 13.075808 | 1.538987 |
| No.8 | -2.115368 | 2.920003 |

## Interpretation and verification

Positive differences favor v121. No.20, No.3 and No.8 worsen; No.4 changes by only 0.001615 mm. The existing 5% participant guards pass, but a favorable mean is not uniform improvement.

This is conditional, post-selection TRAIN evidence. The selected penalty was chosen using these participants, and folds share fitting data. The resampling interval and sign-flip fraction do not establish independent generalization or statistical significance. They do not change selection or authorize promotion.

The script self-checks constant effects, zero effects and sign symmetry. The original root reconstruction is recorded in research_state/v122_verification.json. On 13 October an independent read-only reviewer verified all five input hashes, source manifest entries, output hash, unique participant pairing and trial counts. A separate calculation reproduced omission means, seeded bootstrap with manual quantile interpolation and all 4,096 sign flips (486 extreme). No material defect was found. The script does not explicitly assert unique IDs, but the actual 12 IDs were independently verified unique; the sealed source remains unchanged. See research_state/v122_independent_review.json. Previously completed v121 screen and package reviews remain in research_state/v121_review.json and research_state/v121_package_review.json.

## Next evaluation boundary

The full-TRAIN v121 inference model is already frozen at models/reservoir_path_v121_completed. The next accuracy milestone is one explicitly authorized matched validation comparison against v34 using frozen support, clocks, initialization, metrics and robustness guards. It has not been executed. Do not tune after inspecting that comparison or access the reserved retrospective test. Clock/provenance limitations and the need for new independent final data remain.

The concrete decision scope is recorded in research_docs/frozen_validation_decision_v121.md. It fixes the candidate hash, reproduction prerequisite, complete support requirement and all guards. The evaluation-only runner remains to be implemented after authorization; the document is not a validation result.
