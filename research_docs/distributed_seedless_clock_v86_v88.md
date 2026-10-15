# Preregistered distributed fresh-fold clock diagnostics, v86-v88

Registered 9 October 2026 before execution. Three-cycle budget: v86 candidate
discovery, v87 pairwise distributed evidence, v88 independent reproduction and
separate reviewer. TRAIN only; original observed C3D derivatives; no trajectory
error, historical fitted clock fallback, predictive refit or gate relaxation.

Falsifiable hypothesis: signed yaw and wheel-midpoint speed fitted only on other
participants can expose the repeated-cycle alias through independently generated
event basins and distributed identical-support correlation. Short peak-poor
recordings may remain unidentifiable; absence is evidence against full coverage.

Use sealed v80 full sensor records, v83 references and v84 fold fits. Hash all
consumed parent artifacts; assert fit/held participant and ID disjointness.
Select the eight v84 rejects and two v85 discrepancies over 250 ms. The saved
clock comparison chooses cases only, never candidate lag values. Generate lags
from fresh channel peak-time differences within the existing +/-5 s bound,
25 ms bins, top three basins per channel separated by >500 ms. Coarse scores
have candidate-dependent support and ONLY propose basins; retain their support
counts and peak matches. Refine each within +/-25 ms at 1 ms resolution on
identical local support. Neither historical offsets nor position arrays enter
candidate generation. Retain insufficient-motion/peak diagnoses without relaxing
the existing motion and two-peak gates.

v87 compares every candidate pair on exactly the same observed derivative and
valid sensor brackets. Report signed yaw and speed, global correlations and
non-overlapping 8 s windows (>=60 frames and standardized spread >0.04), plus
chronological one-to-one peak matches within the existing 200 ms tolerance.
No ordinal first/last event claims across unmatched acquisition boundaries.
An evidence contrast needs >=0.025 global gain, no informative channel loss
>0.025, and at least two windows with >=0.025 gain and no contrary windows.
This is a diagnostic contrast, not an accepted clock or a new promotion gate;
shared periodic yaw/speed are not independent timing ground truth. Single-window
and peak-poor evidence stays inconclusive. Frozen v81 scoring support loss is
reported separately; common diagnostic masks NEVER replace scoring masks.

All 207 identities and all No.20 records remain unchanged. All-207 supported
clocks, alias review and unchanged support/pose remain mandatory before any
predictive refit. New trajectory metrics are unavailable because no predictions
are produced. Existing v34 result and v81 TRAIN scores remain unchanged.

Scope: new diagnostic scripts, small assert-based synthetic checks, sealed local
outputs, state files and README. No production callers, fixtures, exports or
configuration change. No raw datasets altered. Run using research_run_guard.py
(exclusive PID identity/run ID/15 s heartbeat); completed outputs immutable.

Commands:
`python research_run_guard.py distributed_clock_candidates_v86.py distributed_clock_evidence_v87.py`
Then independently reproduce saved evidence with v88; never rerun completed
directories. No commit/push unless a qualifying estimator is actually promoted.
