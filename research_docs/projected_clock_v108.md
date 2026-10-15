# Existing projected-yaw clock diagnostic v108

Preregistered 9 October 2026 before results. Hypothesis: projecting full-record
center gyro onto the existing 0.3 Hz dynamic-gravity proxy reduces pitch/roll
contamination and yields additional supported clocks with the unchanged gates.
This tests an existing feature, not a new predictor architecture or event rule.

One configuration only: reuse projected_yaw_folds_v52.proxy on v80 full raw/t/
validity, using v84 fresh-seed, other-participant fold calibration. Replace only
the selected center column in a private copy given to synchronize_observed.
Keep v84 sync terms, wheel speed, mode priority, normalization, peaks, motion,
correlation, ambiguity, lag limit, matching tolerance and refinement unchanged.
No projected-yaw scalar refit, cutoff/sign search, blend, or alternate fallback.
All six center fits must be gx/positive scale and gravity-x positive; otherwise
stop, rather than adapting the protocol after seeing outcomes.

Baseline is the sealed v84 199/207 acceptance. Retain all207 TRAIN/12people/
15No20. Read optical time/yaw/speed/derivative-validity only for clock diagnostics;
never XY values or ATE. Check exact source hashes and fit/held-person disjointness.
Save projected features, diagnostics, per-trial acceptance transitions and offset
differences. Use v81 frozen time/validity masks only to count lost scored support.

Acceptance for a possible future clock path requires all207 accepted, no lost
frozen scored support and independent alias/distributed review; this job cannot
certify timing truth or promote clocks. Any missing clock fails closed. No fit
on an accepted subset, held-out validation/test access or predictor execution.

The gravity direction is an acceleration-derived proxy and uses future samples;
v84 bias/gravity derives from other people's optical-supervised seed labels.
Projection does not prove independent physical mounting or acquisition timing.
Inherited timestamp reconstruction/reference/QC/acceptance remain conditional.

Self-checks: constant-gravity projection agrees with analytic biased gyro;
short valid runs use the existing fallback; input arrays are unchanged.
Completed output directories and scripts used by sealed results remain immutable.
Command: python research_run_guard.py projected_clock_v108.py
