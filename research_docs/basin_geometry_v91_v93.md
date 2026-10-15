# Preregistered bounded basin and geometry-policy audit, v91-v93

Registered 9 October 2026 before execution. Three cycles: v91 basin audit,
v92 reference-scoring/training-geometry separation, v93 numerical verification.
Reuse sealed v86 candidates and v87 signals; no candidate regeneration or fits.

v91 expands each of the twelve existing coarse proposals by exactly the frozen
200 ms event tolerance on each side, clipped to the existing +/-5 s limit.
The 1 ms grid is fixed before scores. This radius follows the existing event
association tolerance, not ATE, historical clocks or observed boundary direction.
Use one common derivative/sensor mask per case/channel across the union of all
prescribed grids. Retain motion, >=60 frames, standardized spread >.04, two
chronological peaks and .6 correlation gates. Record all grid scores, boundary
or interior maxima, interval overlaps, both-channel scores, event identities,
and frozen IMU/scoring support losses. No widening after seeing scores. This
tests these bounded intervals only, not global completeness or absolute timing.
An event identity is a saved peak-index association, not physical ground truth.
No candidate clock is accepted; seven candidate-empty cases remain unresolved.

v92 creates a diagnostic contract separating immutable scoring references,
support and initial pose from existing train-only geometry fits. Verify sealed
v70 fold fit IDs/audit IDs and disjoint people; carry forward its support audit
without refitting or recounting raw geometry. Verify all 207 v83 references
against v81 frozen scoring arrays on exact native times. Keep all fifteen No.20
trials in scoring even where fold-only geometry is inapplicable. Report loss
if training geometry were incorrectly used as an evaluator filter. This role
separation does not erase inherited reference/QC/dataset selection, infer an
unseen marker band, or certify fully nested estimation. No production changes.

v93 verifies parent/output hashes, independently reconstructs every v91 grid
correlation using explicit brackets and centered dot products, and checks
maxima, boundaries, support losses and v92 accounting. Synthetic missing-bracket,
known-lag, closed-limit and event-identity checks must pass. Same-context review,
no separate agent or independent clock ground truth.

Scope: three small scripts, local immutable outputs, research state and README;
no production callers, tests/fixtures/config/exports changed, raw data untouched.
All-207 supported clocks/alias review/unchanged support and pose remain required
before predictive refit. No validation/test access, trajectory scoring, promotion
or commit/push. Run each cycle using research_run_guard.py.
