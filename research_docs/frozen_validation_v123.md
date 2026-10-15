# v123 authorized frozen validation implementation

User authorization received 14 October 2026: "Authorize the frozen v121 validation comparison".
Implements research_docs/frozen_validation_decision_v121.md without a new fit or
search. One v121 penalty10 full-TRAIN candidate versus v34 weight0.75; 71 exposed
validation records, no reserved test, retuning, promotion, commit or push.

Before candidate predictions, reproduce every historical v34 motion, trajectory,
heading, trial metric, identity and exact reference/support array. Native startup
is reconstructed from original IMU streams as in audit_dynamic_loader_v36.py;
compare gravity/bias and eligibility to the saved v14 initialization. Inference
receives only setup/time/raw/IMU-valid/IMU initialization. Integration receives
one original optical initial pose separately. No new alignment or clock search.

Frozen tolerances: v36 XY maximum 1e-8 m and equal-person aggregate absolute
difference 1e-9 m against 0.1007021193993738 m. Additional pre-evaluation checks:
motion max1e-7 (v44/v121 precedent), startup gravity/bias max1e-10 (v44), heading
max1e-8 rad, and every numeric historical trial field atol1e-9/rtol1e-10. Exact
reference arrays, timestamps, NaN/finite masks, IDs and participant/maneuver labels.
Additional heading and per-trial limits are new implementation checks, not claimed
as thresholds enforced by the original v36 audit. No post-result relaxation.

Use the v121 aggregation: mean of participant mean trial ATE; maneuver ATE is
likewise participant balanced. Require lower mean, every person/maneuver ratio
<=1.05 and equal-person P95 position/last-supported endpoint/heading ratios<=1.05.
Zero baseline permits no increase; null ratio represents a failing increase.
Missing/nonfinite data or changed support fails closed; no dropped records.

Test synthetic lower-mean-with-worse-person/maneuver/tails, zero denominator,
duplicate/missing IDs, changed labels/counts, equal-count-different-mask and
nonfinite motion/heading before data access. Preserve all pipeline and v74 metrics,
predictions, hashes, baseline audit and independent review. The genuine endpoint
flag is not invented. Exposed validation does not establish independent generalization.

Commands: python -m unittest test_frozen_validation_v123 -v;
python research_run_guard.py frozen_validation_v123.py.
Fresh output: outputs_frozen_validation_v123. Failure artifacts are preserved.

Pre-evaluation provenance collection stopped on PyTorch virtual _ops.py, before baseline or candidate predictions. Failed directory outputs_frozen_validation_v123 and source/LAST_RUN copy in research_state/v123_preflight_failure remain preserved. Corrected real-file source collection uses fresh outputs_frozen_validation_v123_completed; model, metrics and tolerances unchanged.

Baseline reproduction stopped after24 records on SL_Trial1_No.10 heading-metric delta1.0225843727340589e-8 deg; candidate_count0. The original v36 two-thread audit has the identical historical residual. Baseline-only diagnosis restored the original v33 producer's four Torch threads and reproduced that recording's motion, XY, heading and heading metric exactly (zero differences). No tolerance changes. Preserved outputs_frozen_validation_v123_completed and second-attempt source/LAST_RUN; diagnosis research_state/v123_baseline_failure/diagnosis.json. Corrected execution uses outputs_frozen_validation_v123_exact with torch.set_num_threads(4).
