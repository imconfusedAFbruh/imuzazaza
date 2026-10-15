# Frozen v125 validation decision

Prepared15October2026 after the selected model and all207 public inference
checks were frozen and both independent reviews passed. This replaces the
unexecuted v124 proposal as the next candidate. It does not authorize access.

## Frozen candidate and completed controls

- Candidate `models/axis_prior_v125/model.json`, SHA256
  `7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2`.
  Existing `reservoir_inference_v121.load_reservoir_model('models/axis_prior_v125')`.
- Primary control `models/reservoir_path_v121_completed/model.json`, SHA256
  `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`.
- Historical v34 control: frozen .75 blend and unchanged public loader/seals.

The TRAIN screen improved v124128.872854348->127.531627048mm and all guards
against v34/v121/v124 pass.11/12 people improve; the descriptive post-selection
benefit interval[.476606539,2.312106231]mm is positive. This motivates independent
comparison without establishing its outcome. No8 versus v34 remains+4.929492%.

## Proposed one-time comparison

After separate authorization, use an evaluation-only runner for ONE frozen v125
candidate on all71 previously exposed validation records/four people/105821
scored frames. No new v124 alternative or hyperparameter selection is included.
Reproduce BOTH completed controls from `outputs_frozen_validation_v123_exact`
before any candidate inference: v34 ATE100.702119399mm and v12199.303735166mm.
Require original exact IDs/references/timestamps/clocks/crops/support and all
control motion/XY/heading arrays, using unchanged `frozen_validation_v123.TOL`.
Never loosen tolerances, intersect masks, drop records or substitute fallback.

Set CUDA_VISIBLE_DEVICES=-1 before Torch import; use four Torch threads to match
the producing CPU. Reuse original startup IMU initialization and sensor-only
prediction contract. A single original observed initial pose enters integration
separately. Require finite outputs on every control-supported frame and exact
finite masks on unscored portions. Reproduce startup/control checks and preserve
all historical/v74 metrics, availability denominators and last-supported endpoint
terminology. Record full paired predictions, input/source/output seals, guards
and an independent arithmetic/support/provenance review.

Acceptance requires lower equal-person mean trial XY ATE than v121 plus all
original5% guards against BOTH completed controls: every person/maneuver ATE,
overall equal-person P95 position, last-supported endpoint and heading. A zero
control permits no increase. Retain all71 and all105821 scored frames. Failed
guards retain v121 as the completed validation best, with no retuning.

## Boundary and next action

The current TRAIN protocol's fit, package, tests and independent reviews are
complete. The saved research contract requires separate validation authority;
the current direct request was executed as renewed TRAIN development. Approve
this concrete single-candidate comparison to enable its implementation/execution.
No new fit, alternative candidate, validation-guided tuning, reserved test,
deployment, commit or push is included. Previously exposed development validation
does not establish blind final generalization. Independent timing, exact runtime/
firmware identity, physical geometry and independent final data remain required.

Evidence: `axis_prior_results_v125.md`, `axis_prior_review_v125.md`,
`research_state/v125_independent_review.json`,
`research_state/v125_package_report_review.json`, and frozen bundle verification.
Do not repeat completed fitting/scoring/inference checks to prepare this decision.
