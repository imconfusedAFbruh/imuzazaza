# Independent TRAIN fold and route audit v59

## Finding

The v56 selected braking residual fails the user's new maneuver robustness requirement. The original selection guarded only participant mean synchronized error. Gain0.25 reduces equal-participant XY RMSE219.002101→216.033080mm and has worst participant ratio1.010555, but ST rises89.333110→118.601066mm (+32.76%). ST endpoint worsens30.16%, supported-run discrete Fréchet28.91%, sampled Hausdorff31.98%, and path-length error55.27%. Reject promotion under the broader requirement. This is evidence of slope-related acceleration contamination or model mismatch, not proof of the specific physical cause.

## Reproduction and scope

`audit_fold_routes_v59.py` reconstructs predictions using saved v52 and v56 coefficients; it fits nothing. Each fold's calibration dictionaries and fitting memberships are exactly equal, and fit/held IDs are disjoint. Every record is TRAIN. All207 trial position/heading results match the sealed source CSVs within2.23e-16. Eight source artifacts passed SHA256 verification. The first audit process loaded the source before the explicit helper hash guard was added to the script; a separate subsequent hash verification covered all used fold models and source result files.

v56 recalibrates physics, acceleration normalization, ridge normalization/coefficient/cap excluding held participants. v52 reuses that same fold calibration, fits its yaw scalar/intercept excluding held participants, and selects gravity-projection weight using TRAIN folds. Both inherit frozen reference/QC/clock preparation and geometry; they are conditional participant development results. They do not establish an independently frozen final evaluation. Earlier validation informed the broader research history. v56 selection used only person error guard; no route, maneuver, or endpoint guard. New v58/v60 experiments must apply their predeclared broader guards.

Earlier identity-unlinked training rows are not used here: this audit covers exactly207 identified target-participant TRAIN recordings. Results cannot directly replace the100.702mm retained development headline computed on another partition/pipeline scope. No validation or test is read by the audit script. Existing historical exploratory images were visually reviewed without fitting or selecting from them.

## Same-support geometric results

All values below are equal trial means within participant, then equal participant means; heading is degrees, others millimeters.

| Model | XY RMSE | Symmetric route RMSE | P95 | Discrete Fréchet | Last supported endpoint | Heading | Absolute supported length error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fold physics |219.002|89.805|184.753|413.934|314.293|6.286|330.121|
| v52 projected yaw |147.747|60.521|119.404|257.008|193.853|1.837|330.121|
| v56 braking gain0.25 |216.033|87.891|180.998|406.791|308.141|6.286|311.954|

v52 improves all participants' synchronized XY means (worst ratio0.961159). OS maneuver XY worsens1.28% (122.251→123.811mm), geometric route3.91%, P955.12% (128.315→134.882mm), heading20.21% (0.719→0.864deg). No.13 participant heading worsens31.71% (1.416→1.865deg), despite improved XY. A strict multi-metric5% gate would therefore require explicit treatment of these regressions, rather than a universal promotion claim. The source proposal gate was XY-based. Absolute and participant/maneuver rows are saved in `outputs_fold_route_audit_v59/`.

Route distance uses10mm-spaced arc queries to the exact nearest point on the supported reference/prediction polyline, half weight per direction. Run endpoints/isolated vertices are included, so this is an arc-sampled approximation rather than an exact continuous length integral. No edges bridge reference gaps. P95 is a bidirectionally weighted quantile; Hausdorff is sampled-point-to-polyline maximum. Fréchet is25mm-resampled discrete Fréchet within matching temporal supported runs, taking the maximum run; it is not continuous or whole-recording Fréchet. Endpoint means last supported endpoint and can precede the true recording endpoint. The helper's vectorized anti-diagonal recurrence matches the existing scalar recurrence on five differently shaped random curves including one-point cases.

## Mechanism concerns

v56 `braking=max(-dv,0)` is a forward deceleration history feature. For reverse motion it marks increasing reverse speed as braking and omits slowing reverse travel. The regressor can still use the feature, but describing it as a general physical slip/braking detector is incorrect. A signed-speed-aware deceleration feature would be a new TRAIN-only hypothesis, not a reason to modify the sealed experiment.

v52 gravity projection uses offline0.3Hz forward/backward filtered center acceleration. It includes future IMU samples and dynamic acceleration; it is an empirical attitude proxy, not calibrated attitude. The comparison supports reducing yaw-axis contamination but does not prove mounting or lever-arm correctness. Integration uses permitted C3D initial pose only, with no subsequent resets. Local relative-distance metrics in the shared pipeline rotate intervals into the optical start heading; these diagnostics must not be confused with the unaligned route or synchronized scores reported here.

## Actual image inspection

- `outputs_clock_routes_v44/figures/2026-09-25__PS__PS_Trial2_No.18.png`: the straight route ends roughly0.5m short; error rises sharply around2–3s and persists. The optical-frame along-route component dominates, supporting existing v55 speed-counterfactual evidence. Timing/heading-only explanations are insufficient for this picture.
- `outputs_clock_routes_v44/figures/2026-09-24__AR__AR_Trial3_No.5.png`: the reconstructed loop stays on the opposite side of the initial pose from the optical loop, with all clock variants essentially overlapping. The image supports a stable initialization/mounting/reference convention problem but cannot establish which marker was physically left; no oracle reflection/rotation is allowed.
- `outputs_no8_clock_signals_v46/figures/2026-09-24__PS__PS_Trial2_No.8.png`: the corrected signed-yaw timing sits near the sharper correlation peak. Speed alignment is broad and affected by braking response. Selecting an old clock because its integrated position happens to score better would confound timing with velocity calibration. Existing boundary evidence explains why a55.5ms shift can change integrated travel by~0.126m when reference starts at~2m/s.

## Keep / reject

Keep v52 as a stronger conditional fold control and keep the route audit/helper. Reject v56 gain0.25 as a robust promotion. Continue predeclared combinations and interval travel residuals on the same TRAIN folds; inspect slope regressions before validation. Do not reduce errors through alignment, C3D resets, omitted difficult trials, or clock tuning from integrated position.
