# Frozen v121 validation comparison — decision ready, not executed

Prepared 13 October 2026 from source and existing research reports only. This
document does not authorize validation access and is not a new model search.

## Decision requested

Authorize one matched comparison of the already frozen full-TRAIN v121 model
against frozen v34 on the 71 previously exposed validation recordings. No
refitting, alternative penalties, clock selection, reserved-test evaluation,
deployment promotion, commit or push is included.

## Frozen candidate and control

- Candidate: `models/reservoir_path_v121_completed/model.json`, SHA256
  `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`.
  Use `reservoir_inference_v121.load_reservoir_model`; penalty 10, saved
  normalization and coefficients, unchanged 16-state reservoir and correction caps.
- Control: `dynamic_blend_inference_v34.load_dynamic_blend`, frozen weight 0.75.
  Both loaders retain their manifest/dependency checks and reviewed exact legacy
  hash transitions; do not weaken these checks to run the comparison.
- Run CPU inference with `CUDA_VISIBLE_DEVICES=-1` before importing torch.
  Preserve source/dependency hashes in a fresh output directory.

## Matched evaluation contract

Reuse v34's observed-reference validation preparation, original startup IMU
initialization, timestamps, clock mappings, crop boundaries, reference arrays,
initial pose and support masks. The existing source route is
`observed_training_experiment.observed_rows` with the v7 saved settings and
validation partition, as used in `dynamic_tilt_blend_v34.py`. Do not run that
script's `main`: it fits models and searches blend weights.

Before candidate scoring, reproduce all 71 saved v34 motions/trajectories and
trial metrics, IDs and per-frame support, plus historical equal-person ATE
100.702119399 mm. Use the established reproduction tolerances from the existing
inference audit; record them in the runner before execution, never loosen them
after seeing validation values. A mismatch stops execution for provenance or
implementation diagnosis. Equal frame counts alone do not prove matched masks.

Pass only sensor/setup/IMU initialization to prediction. Supply one observed
initial pose separately to integration; no optical resets, post-hoc alignment,
scale fit, participant/maneuver inputs or newly chosen exclusions. Require finite
candidate outputs on every baseline-supported frame. Unsupported candidate data
is a failure, not a reason to shrink the common evaluation mask.

Report both models on all 71 identical records, with participant and maneuver
tables. Preserve historical metrics through `pipeline.metrics`/`summarize` and
the supplementary `metric_contract_v74.metrics` fields, including coverage,
position tail, heading, route, RTE and last-supported endpoint. Do not rename
last-supported endpoint error as genuine acquisition endpoint error.

## Predeclared decision rule and stopping boundary

Lower equal-person mean XY ATE is necessary. Every participant and maneuver
ATE ratio must be at most 1.05, and equal-person position P95, last-supported
endpoint and heading ratios must each be at most 1.05. Require exact recording
and frame support with no omitted failures. Preserve the v121 aggregation and
guard implementation; a zero baseline requires no increase instead of division.
All guards must pass. No alternative candidate is evaluated if v121 fails.

Save per-record predictions, all metric tables, frozen input/source hashes and
the decision, then obtain independent review. Report any failure openly. Passing
this comparison would be conditional evidence on exposed development validation,
not a blind test or proof of superiority to published methods. Independent clock,
firmware provenance and new final-data requirements remain unresolved.

The next implementation step after authorization is a separate evaluation-only
runner using these existing loaders and evaluators, with synthetic support and
guard checks before accessing validation. No runner or validation result is
claimed by this decision document.
