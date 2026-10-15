# Preregistered clock-event observability audit, v89-v90

Registered 9 October 2026 before execution. Continue interrupted v86-v88:
v86/v87 completed artifacts are reused, v88 numerical reproduction completes
first. This run has three substantive cycles: v88, v89, v90. No new estimator
family, gate tuning, lag acceptance, historical fallback or trajectory scoring.

Hypothesis: the eight rejected fresh-fold clocks lack sufficient observable
event evidence under the frozen protocol, rather than failing merely because
the coarse search missed an admissible multiple-peak lag. Inspect all twenty
saved channels for ten difficult TRAIN cases, preserving every identity and
the original optical mask. Report observed-run lengths, discarded short-run
frames, existing peak counts, and event-spacing feasibility. Do not fill gaps,
count run boundaries as peaks, or lower motion/prominence/two-peak gates.

For each saved peak list, enumerate all breakpoints where a peak pair enters
or leaves the existing +/-200 ms tolerance inside +/-5 s, plus interval
midpoints. Compute the maximum chronological one-to-one matches over this
finite set. This proves feasibility for the saved events only; it does not
identify a clock or prove that alternative event definitions cannot work.
Report only maximum count, never choose a lag from position errors. Check
event-support feasibility separately from candidate correlation or full
reference scoring coverage. Even feasible events cannot authorize refitting.

v90 independently checks peak provenance against reference/full-sensor signals,
reconstructs run accounting and uses dynamic-programming event matching to
verify v89 maxima. Known shifted, incompatible spacing, empty events and
closed tolerance-boundary synthetic examples are checked. Use only sealed
v83 reference arrays and v87 channel signals after manifest verification.
No separate-agent review is claimed; numerical independence is same-context.

Scope: two diagnostic scripts, local immutable outputs, research state and
README. No production callers, fixtures, exports, config or raw-data writes.
All 207 records and fifteen No.20 records remain in the benchmark; all-207
supported clocks, alias review, unchanged scoring support and initial poses
are still prerequisites to predictive refitting. New trajectory metrics N/A.

Commands: `python research_run_guard.py clock_observability_v89.py`
then `python research_run_guard.py review_clock_observability_v90.py`.
Completed output directories must never be overwritten.
