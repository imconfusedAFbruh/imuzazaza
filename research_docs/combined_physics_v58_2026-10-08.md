# v58: projected yaw plus continuous travel correction

Decision: **reject both nonzero travel gains**. The overall synchronized and
geometric means improve, but slope/ST errors worsen substantially. The
predeclared participant-and-maneuver 1.05 guard correctly retains projected
yaw alone. No validation or protected-test data were opened.

## Hypothesis and protocol

Dynamic gravity projection addresses yaw contamination, while the bounded
causal braking-memory residual addresses forward-travel errors. Their
combination could improve held-participant trajectory accuracy.

- Data: the same 207 identified target TRAIN recordings, 12 participants,
  inherited participant folds and frozen v42 clock/reference preparation.
- Reuse: sealed v56 fold calibration and residual models; sealed v52
  projected-yaw mappings, weight 1.0. Artifact hashes, identical calibration,
  fitting membership and held membership were checked.
- Predeclared travel gains: 0, 0.25, 0.5. Ridge alpha 1, causal EMA states at
  0.10/0.25/0.50/1.00 seconds, fitting-only 99.5% residual clipping.
- Prediction inputs: IMU and fitting-only parameters. C3D supplies fitting
  labels, evaluation and the previously authorized initial pose. There are no
  subsequent reference resets, spatial alignment, reflection or scale fits.
- Selection: minimum equal-participant synchronized XY RMSE subject to worst
  participant **and** maneuver XY ratio <=1.05 versus projected yaw alone.
- Gravity projection is an offline low-pass acceleration proxy, not verified
  attitude. Historical validation hypothesis exposure remains exploratory;
  inherited clocks/QC mean these are conditional estimator folds.

## Results

All lengths are mm; heading is degrees. Aggregation is equal trial mean within
participant, then equal participant mean.

| Travel gain | Synchronized XY | Symmetric route | Route P95 | Sampled Hausdorff | Max-run discrete Frechet | Last-supported endpoint | Absolute supported length error | Heading |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 147.746508 | 60.521354 | 119.404180 | 217.235166 | 257.007912 | 193.852803 | 330.121009 | 1.836665 |
| .25 | 143.447034 | 58.225938 | 114.396769 | 211.554548 | 247.600357 | 186.928767 | 311.953628 | 1.836665 |
| .5 | 144.147231 | 57.659957 | 111.383173 | 212.627450 | 246.334098 | 187.312372 | 310.951753 | 1.836665 |

| Gain | Worst participant XY ratio | Worst maneuver XY ratio | Regressing trials | Decision |
|---|---:|---:|---:|---|
| 0 | 1 | 1 | 0 | retain control |
| .25 | 1.018563 (No.6) | 1.384763 (ST) | 67/207 | reject |
| .5 | 1.047937 (No.6) | 1.825777 (ST) | 80/207 | reject |

The .25 gain improves all six other maneuvers: 10x5 ratio .944315, AR .938739,
CR .933300, OS .827990, PS .912628 and SL .919647. This does not justify
accepting the ST regression. ST synchronized error rises 81.831921 ->
113.317795 mm; Frechet 115.801256 ->153.240173 mm; endpoint 114.370275 ->
152.045746 mm; length error 76.430999 ->118.677046 mm. At .5, ST error reaches
149.406802 mm and length error 168.696284 mm.

Worst absolute .25 regressions include ST No.16 T2 169.064->241.184 mm,
No.16 T1 95.700->165.985 mm and No.20 T2 54.184->123.819 mm. A participant-only
guard would conceal these failures.

## Reproduction and geometry limitations

All 207 control trial synchronized and heading errors reproduce v52 weight1
**exactly**, maximum absolute difference zero. Overall route metrics reproduce
the independent v59 reconstruction. Route queries are 10mm apart against
exact supported polyline segments; 20mm refinement is recorded. Maximum route
RMSE refinement across all 621 records is 2.401671 mm. Frechet is discrete,
computed separately per same temporal support run, maximum over runs, with
25/50mm spatial resampling; maximum refinement difference is 12.564122 mm.
These are supported partial routes with disconnected reference gaps, not
continuous full-route guarantees. Endpoint means last supported point.

All 207 held trajectories and three gains are exported under
`outputs_combined_physics_v58/trajectories`; all207 two-panel trajectory/yaw
images are under `figures`. Visual inspection of No.3 10x5 T1 showed continued
route bending; No.8 PS2 shows travel correction with essentially unchanged
yaw; No.13 SL3 retains route displacement. Initial plot inspection caught
`unwrap` propagating optical NaNs and hiding later C3D yaw. Regenerated plots
use relative wrapped yaw, gaps and wrap discontinuity breaks for both signals.
This repair changes only images, not predictions or metrics.

The initial run completed all621 predictions/metrics but failed in final
summary because maneuver summaries use a different key than participant
summaries. `--finish` reaggregated saved metrics after correcting the key;
no models, predictions or grid values were rerun or changed. `--replot` then
rebuilt images from saved trajectories. Manifest records the final artifact
hashes and plot revision.

## Next falsifiable mechanism

v56 subtracts a fixed fold gravity direction from center acceleration. On
slopes, gravity rotation can masquerade as dynamic acceleration in its speed
features. The concentration of regressions in ST supports investigating this
mechanism but does not prove it. A cheap next experiment is to replace those
features with IMU-only dynamic-gravity-compensated or magnitude-invariant
acceleration, refit within the same TRAIN folds, and keep the frozen guards.
Do not select a condition-specific override from this result.

Commands:
```powershell
python combined_physics_folds_v58.py
# Existing completed output is preserved; do not rerun into it.
python combined_physics_folds_v58.py --finish
python combined_physics_folds_v58.py --replot
```
