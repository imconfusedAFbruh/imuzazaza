# Frozen v124 validation decision

Prepared15October2026 after the completed, independently reviewed TRAIN screen,
full207 selected fit, exact public inference reproduction and artifact freeze.
This is a concrete proposed evaluation; it does not authorize validation access.

## Frozen models

- Candidate: `models/trial_rmse_v124/model.json`, SHA256
  `ac46f8b82096214da181624f7be0362ddc8494f1b44fa4827c68f01d41421ce7`.
  Load with `reservoir_inference_v121.load_reservoir_model('models/trial_rmse_v124')`.
- Primary control: frozen full-TRAIN v121 at
  `models/reservoir_path_v121_completed/model.json`, SHA256
  `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`.
- Historical control: frozen v34 weight .75, unchanged public loader and seals.

The v124 screen improved matched TRAIN ATE129.739810994->128.872854348mm.
Every original guard passes against both controls. All207 records/12people/
15No20 remain. No.8's ratio1.049560359 versus v34 is close to the1.05limit.
The descriptive improvement interval[-.126796,1.940807]mm includes zero.
Those observations motivate a frozen comparison; they do not establish its result.

## Proposed single evaluation

After explicit authorization, use a separate evaluation-only runner to compare
v124 once against both controls on all71 previously exposed validation records.
Before any candidate inference, reproduce BOTH controls against the sealed
`outputs_frozen_validation_v123_exact` arrays: v34 ATE100.702119399mm and v121
ATE99.303735166mm, all71/fourpeople/105821scoredframes. Require exact IDs,
references, timestamps, clock mappings, crop boundaries and support masks.
Keep the frozen v123 tolerances in `frozen_validation_v123.TOL`; do not loosen
them after a mismatch. Set CUDA_VISIBLE_DEVICES=-1 before torch import and use
four Torch threads to match the producing CPU calculation.

Reuse original startup IMU initialization and the same sensor-only input contract.
Supply a single original observed initial pose only for integration. Preserve
all historical and v74 metrics, all participant/maneuver tables, explicit metric
availability denominators and last-supported endpoint terminology. Require
finite outputs on every control-supported frame, including exact finite masks
on unscored portions; no mask intersection, exclusion, replacement or fallback.

Select no hyperparameters during this evaluation. Require lower equal-participant
mean XY ATE than v121, and all original guards against BOTH v121 and v34: every
person/maneuver ATE and overall P95position/last-supportedendpoint/heading ratios
at most1.05. A zero control permits no increase. All71 records and all105821
scored frames remain mandatory. Save complete paired outputs, input/source/output
seals and the decision; obtain independent support/arithmetic/provenance review.

## Boundary

The current v124 protocol permits TRAIN fitting, verification, packaging and
reporting only. This decision requires separate explicit validation authority;
a generic continuation does not consume this new evaluation. No refit, alternative
penalty, retuning from validation, reserved-test use, promotion, commit or push.
Failure retains v121's completed validation result. Passing would support only
previously exposed development validation. Independent clocks, firmware/runtime
identity, physical geometry and independent final data remain unresolved.

Evidence: `trial_rmse_results_v124.md`,
`research_state/v124_independent_review.json`,
`research_state/v124_package_report_review.json` and
`models/trial_rmse_v124/verification.json`. Completed fitting, scoring, inference
reproduction and report arithmetic should not be repeated to prepare this decision.
