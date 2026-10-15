# Clock tradeoffs and failed-candidate metrics — v94-v96

Completed9October2026, three bounded cycles. The complete goal contract is saved
in research_state/AUTONOMOUS_RESEARCH.md; actual numerical work remains in the
recovered research repository per the approved existing-data plan. Acquisition
application/firmware remains in WheelAthelse. No dataset was moved or duplicated.

## Clock result

v94 used only the twelve sealed v91 intervals,1ms grids/common masks, existing
peaks and nonoverlapping8s windows. The No13 longT3 local basin has a yaw maximum
at-.701s(.997862110yaw/.863357347speed) and a speed maximum at-.859s
(.958315146speed/.913656297yaw), a158ms objective separation. Yaw favors-.701s
in all six informative windows; speed favors-.859s in four, with two below the
existing.025 contrast threshold. Neither lag dominates across channels.

Independent v96 finite-only Pareto analysis gives159grid points from-.859 to
-.701s. Both raw maxima lose zero frozen IMU/scored frames. Each has only one
matched yaw event versus six speed events, so strong correlations do not provide
two-channel event certification. Across all12basins the simultaneous existing
two-channel motion/event/correlation gate has no passing range. That stricter
joint diagnostic is NOT a new historical acceptance policy. Clocks stay199/207;
no alternate clock is accepted and no predictor is fitted.

The initial event-gated-maxima implementation hid the raw tradeoff and is
preserved as outputs_clock_consistency_v94_gated_attempt. Corrected v94 reports
raw correlation maxima and eligibility separately,90window contrasts and whole
profiles. Its Pareto list remains explicitly event/motion-gated; v96 supplies
the raw frontier/support separately, preserving completed v94. Empty joint-gate
support lists are not evidence of support loss at raw maxima.

## Failed-candidate backfill

v95 scores2898sealed TRAIN prediction rows,14source/model cells,207recordings/
12people per cell. v58 has3cells, v62/v64 each5 and v60 has only its baseline.
All original trial ATE/counts reproduce, maximum difference1.110223025e-16m;
common position masks across each source's saved candidates agree exactly.
The unchanged v74 evaluator adds synchronized MAE/P95, yaw, local displacement,
route/tail, length and last-supported endpoint metrics with participant/maneuver
tables. Genuine acquisition endpoints stay unavailable. Only207v60baseline rows
save actual local motion, so velocity/rate metrics are absent for the other2691.
Motion is never reconstructed from predicted position.

| Historical TRAIN cell | ATE mm | Route mm | Contiguous5s RTE mm | Decision |
| --- | ---: | ---: | ---: | --- |
| Projected-yaw control |147.746508|60.521354|99.627313|Matched historical control |
| v58 gain.25 |143.447034|58.225938|102.563001|Still rejected: frozen slope guard |
| v62 dynamic-gravity gain.5 |142.487879|57.765063|108.048029|Still rejected |
| v64 wheel-products gain.5 |142.051218|57.760981|108.078745|Still rejected |

The table illustrates tradeoffs, not a new ranking/selection. Full14cell tables
are saved. Lower aggregate ATE/route coexists with worse5s local displacement
and historical slope regressions.1/5/10s eligibility is207/106/12for these cells;
ten-second numbers describe a smaller eligible subset, not the whole population.

Missing arrays are explicit in v96 availability_corrected.json:828nonzero v60
model-trials and1656v63diagnostic model-trials are unavailable. v61 has variance
diagnostics with unchanged trajectory, so trajectory backfill is not applicable.
v95's original availability undercounts v63; the verified v96 supplement corrects
it without editing completed output. No regeneration or favorable missing-data
exclusion is authorized. Thus the historical full metric backfill is complete
for available saved candidates, not for every prior prediction.

## Verification, provenance and review

v96 verifies1352parent/output hashes; independently reconstructs9122whole-grid
and40794window/channel scores using explicit interpolation brackets and centered
dot products, maximum difference1.332267630e-15; all90CSV contrasts agree.
Independent squared-error checks2898ATE/counts, maximum difference6.661338148e-16m;
all14participant-balanced aggregates agree. Sealed profile grids/masks are exact.
Synthetic Pareto dominance/ties/NaNs, discontinuous grid ranges and existing
interpolation/correlation/metric checks pass. Read-only separate-context reviewer
identified the Pareto/support and availability gaps; supplements address them.
No independent hardware timing or physical accuracy is claimed.

Post-review supplementary accounting in
research_state/consistency_backfill_v94_v96_verification.json verifies all280
overall/person/maneuver summary rows for four key metrics,828source-recording
candidate masks, and a complete unique90window CSV key set. Each cell retains
all15No20trials and314621scored frames (different historical source grid from
v81/v92's318034). Completed v94/v95/v96 manifests verify again. These checks
close the final review's table/mask/CSV completeness gaps.

v95 checkpoints atomically every10files and verifies its script hash on resume.
Dependency/inventory hashes are not pinned inside those checkpoints; a changed
dependency on a future interrupted run must fail a separate audit before resume.
This uninterrupted run's final manifest pins metric code, v96 seals current code/
inventory and verifies checkpoint rows against final rows. A run.json without a
valid final manifest is incomplete, never a successful immutable run. No future
resume capability stronger than this evidence is claimed.

The exact preregistration bytes used by v94/v95 are recovered and hash-verified
in consistency_backfill_v94_v95_sealed_preregistration.md. The live v94-v96
document includes explicit pre-finalization correction and reviewer supplements;
these did not widen intervals, select clocks, fit a model or change acceptance.
Raw inputs, all207identities/all15No20 references, scoring support and poses stay
unchanged. No validation/test reads, new estimator, promotion, commit or push.

## Reproduction and next justified task

Completed outputs are immutable; do not rerun these commands into them:

```powershell
python research_run_guard.py clock_consistency_v94.py
python research_run_guard.py failed_metrics_v95.py
python research_run_guard.py review_consistency_backfill_v96.py
python -m pytest test_consistency_v94.py -q
```

The retained best remains v34:100.702119399mm synchronized ATE and49.726226563mm
route on71already-exposed validation trials. README records its exact training
selection and reproduction; no new score replaces it.

The new primary-source competition_source_matrix.md separates literature metrics
from reproductions. The full wheelchair skid paper was recovered from TU Delft;
its20Hz acceleration comparison and2.5m/s2threshold are source evidence, not
newly tuned values. Render the PDF's equations1-3 next; text extraction omits them.
Audit wheel-radius/track/camber/axis evidence and sensor conventions using existing
artifacts before registering a faithful baseline or explicitly labelled adaptation.
No external same-data competitor has yet been reproduced. Do not pursue another
local lag widening, lower event gates or repeat known peak shortages. Reference
instrument/front/acquisition provenance and eight unsupported clocks remain open.
