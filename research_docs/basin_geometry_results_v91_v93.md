# Bounded clock basins and geometry roles, v91-v93

Completed 9 October 2026, three substantive cycles. Preregistered in
basin_geometry_v91_v93.md before execution; no post-result interval widening.

## Findings

The twelve already generated v86 proposals were each evaluated on a 1 ms
grid covering exactly +/-200 ms about its coarse event proposal, clipped to
+/-5 s. The radius comes from the frozen event tolerance. For each case/channel,
all grids share one common observed derivative and sensor-bracket mask.
Neither ATE nor inherited clocks set an interval or select an optimum.

Eleven basins have an interior gated optimum; one No.7 speed basin remains at
its upper bound -3.050 s with correlation -0.324485827. One pair of No.13
intervals overlaps. These are bounded local diagnostics, not proof of global
completeness or clock truth. Interior status does not override correlation,
distributed consistency, identity, or frozen-support requirements.

| Case/channel | Interior optimum | Correlation | Other channel | Frozen scored / IMU frames lost |
| --- | ---: | ---: | ---: | ---: |
| No.13 long T3, fresh speed basin | -0.859 s | .958315146 | yaw .913656297 | 0 / 0 |
| No.13 long T3, yaw alias basin | +4.152 s | .664751483 | speed .293524718 | 12 / 458 |
| No.7 CR1, best speed basin | -1.625 s | .693798177 | yaw .744716127 | 91 / 91 |
| No.19 OS1, best yaw basin | -.543 s | .626961824 | speed .998266006 | 0 / 0 |

No.13 retains 1,669 common derivative frames. Maximizing speed moves from
the old local boundary -.825 s to -.859 s; speed correlation increases while
yaw correlation falls relative to the earlier diagnostic. It remains an
objective tradeoff, not a certified exact lag. No.7's absolute speed gate now
passes in its best bounded basin, but unchanged scoring support still fails.
No.19 retains only the earlier single-window evidence, which remains insufficient
for distributed timing confirmation. Seven candidate-empty cases are not
revisited or rescued by this audit. Accepted clocks remain 199/207, eight reject.

Saved event identities are chronological one-to-one associations of existing
peak indices restricted to common support. They do not establish physical
event identity or independent hardware timing. Full grid scores/masks, all
twelve optima, overlap pairs and both support-loss counts are retained.

v92 binds all 207 frozen scoring identities, references, masks and initial poses
by parent artifact hashes, verifies exact v83-to-v81 native-time projection,
and records train-fitted geometry separately. All 318,034 scored frames and
all fifteen No.20 trials remain in the evaluator. The sealed v70 audit shows
that applying train geometry as an evaluator filter would remove 27,580 native
observed frames and fifteen No.20 trials. This native-frame loss is not a new
count on the cropped scoring grid and must not be subtracted from 318,034.

The v92 contract is diagnostic; production policy is unchanged. It does not
create a physically justified unseen marker-spacing band, remove inherited
instrument/QC/dataset-selection dependence, or establish a fully nested pipeline.
Train-fit IDs/audit IDs exclude held IDs and people, while evaluator instrument
provenance remains explicitly conditional.

## Verification and limits

v93 verifies 658 parent/output hashes, independently reproduces 9,122
grid/channel correlations using explicit interpolation brackets and centered
dot products, and checks all 9,122 event-match counts. Maximum correlation
difference is 1.110223025e-15. All twelve optimum/boundary/support/event-identity
checks pass; the overlap list matches. Independent exact-time dictionary
projection verifies all 207 reference roles and 318,034 scored frames.
Synthetic invalid-neighbor/out-of-range, known-lag identity, bounded-grid and
participant-overlap rejection checks pass. Same-context numerical verification;
no separate-agent review or independent clock ground truth is claimed.

No raw data, estimator, clock acceptance, reference pose or scoring mask changed.
No predictor fits or new trajectory metrics, validation/test reads, promotion,
commit or push. Best retained v34 stays 100.702119399 mm synchronized ATE and
49.726226563 mm route over 71 previously exposed validation recordings; TRAIN
v81 native/new 147.565311 mm is a different scope. Existing limitations include
offline future IMU filtering, reference/front ambiguity, exact acquisition
provenance and inherited preprocessing/acceptance.

## Reproduction and next step

Completed output directories are immutable. Inspect run.json and manifests in
outputs_basin_completeness_v91, outputs_geometry_roles_v92 and
outputs_basin_geometry_review_v93. Original guarded commands:

```powershell
python research_run_guard.py basin_completeness_v91.py
python research_run_guard.py geometry_roles_v92.py
python research_run_guard.py review_basin_geometry_v93.py
```

Do not rerun them into completed directories. Non-writing synthetic checks:
`python -c "from basin_completeness_v91 import check; check()"` and
`python -c "from review_basin_geometry_v93 import check; check()"`.

Next run: preregister a two-channel/distributed consistency audit restricted to
the existing v91 intervals, focusing on the No.13 yaw/speed tradeoff, rather than
another interval widening. Report whole lag profiles, per-window consistency,
event associations and uncertainty; no position scoring, historical fallback,
new peak definition or clock acceptance. The one unresolved No.7 boundary is
already correlation/support-ineligible; do not pursue it with a broader search.
If evidence cannot certify all-207 coverage, continue the pending historical
failed-candidate metric backfill and fair source/metric comparison audit, using
sealed predictions only and no new model family. v92 role separation is complete
as a diagnostic; full reference instrument provenance is still unresolved.
