# Improvement plan based on corrected SL diagnostics

## Measured starting point

- Selected corrected model: 116.898 mm overall, 145.482 mm SL, 71 validation recordings/four participants. SL has 12 recordings.
- SL median recording duration: 29.41 s. Median supported 1 m relative displacement error: 24.38 mm. Median last-observed position error: 178.92 mm.
- Median absolute linear trend of heading error: 0.138 degrees/s. This describes the observed error trend; it does not prove a constant hardware gyro bias.
- Derivative/lateral labels are available for a median 54.29% of SL frames, although reference pose coverage is greater. Short optical segments and gaps reduce derivative-label availability.
- Partial-label diagnostic oracles: replacing forward speed on valid labels gives125.828 mm, lateral137.524 mm, yaw128.366 mm, all three99.959 mm versus145.482 mm. Predictions remain unchanged outside those labels. These are non-deployable sensitivities, not achievable predictors or error floors.

The evidence supports investigating both speed and heading, and training over longer motion intervals. A pure yaw fix or lateral-only model is insufficient. This plan does not assume that every discrepancy is tire skid.

## Order of work

### 1. Freeze observed-reference scoring; rebuild alignment on observed labels

The v7/v8 comparisons inherited clock offsets computed before the reference-validity fix. Recompute training bootstrap calibration and peak alignment using camera-observed reference only, then perform native-rate local correlation refinement. Do not choose offsets by position RMSE, alter masks to make scores look better, or fit reference trajectories. Report old/new peak support, ambiguity, residuals, accepted IDs and timing uncertainty. On common accepted IDs, preserve identical observed score frames for comparisons. Clock changes that alter overlap need a separate coverage report. Preserve the old reference/clock artifacts.

Inspect actual firmware encoding, sensor mounting axes and lever arms in parallel. The confirmed acquisition range is +/-2 g; the unexplained 8200-count rest norm still prevents claiming verified factory SI conversion. These facts gate physical INS interpretation, not an excuse to stop the supervised comparator.

### 2. First model experiment: multi-horizon relative-pose supervision

Keep a matched-size network and compute budget. Compare the current short velocity-residual loss with relative SE(2) motion losses at predeclared1/3/5/10-second horizons. Relative displacement and heading targets require two trustworthy observed endpoint poses and uninterrupted IMU samples; they do not require interpolated optical poses in between. Rotate displacement into the starting body frame for training. At inference, use only IMUs and the allowed initial pose. Never reset the reconstructed path at an optical gap or use later reference pose to correct it.

This specifically addresses two observed weaknesses: 30-second SL drift is not directly penalized by the current2.56-second complete-label local loss; and derivative-label gaps discard motion supervision that reliable endpoints can still provide. Compare integrated dense-motion loss versus a relative-displacement head. Add uncertainty only after verifying the motion target and its held-out residual calibration. Avoid treating overlapping predictions as independent measurements.

### 3. Physics comparator: estimate attitude and slow bias as state

Use the three-IMU placement studied in Wheel-INS2 as a methodological starting point. Include chassis attitude, gyro bias, wheel-derived speed and the wheel-IMU rotation/lever-arm effects. Our nominal4 cm off-center wheel mounts rotate and cannot be treated as fixed body-frame sensor offsets. Use measured or explicitly training-fitted transforms/scales with uncertainty; do not silently promote scalar YAML offsets to verified3D geometry.

Bias estimation during inference must use IMU evidence and trained state dynamics, never held-out MoCap. Validate stationary detection from sensors rather than assuming the first5 seconds are stationary. Lateral velocity constraints must be soft or gated; rigid zero-lateral constraints can suppress genuine lateral motion. Compare this state estimator against the current model before fusing them. A diagonal speed/yaw smoother tested earlier is not this navigation-state estimator.

### 4. Offline fusion only if independent gains justify it

Compare direct learned integration, physics-only estimation, and physics plus learned interval-motion measurements. Use meaningful bias, mounting, wheel and IMU-stationary constraints. Model uncertainty/correlation conservatively; raw IMU and predictions derived from the same IMUs are not independent. Do not add known cone positions, return-to-start, endpoint heading, or reference loop closures unless those are real deployment inputs. Smoothing with only an initial pose cannot create missing position information.

## Experiment and acceptance rules

- Make architecture/loss decisions in folds of the known training participants; keep their recordings across dates together. Earlier sessions remain training-only where participant identities cannot support a validation fold.
- Use three predeclared seeds and matched training budgets for shortlisted comparators. Preserve all runs and report median/spread, not only the best seed.
- Score every variant on the same accepted recordings, observation masks and frame conventions. Report whole-trajectory RMSE, SL, per-participant outcomes, turn/straight residuals, last-observed drift and valid relative-distance metrics.
- Prefer a clear, consistent gain over submillimeter changes in the aggregate. A first development milestone is below100 mm overall and below100 mm on SL; this is a target, not a promised result. Check that gains are not bought by a substantial regression on another participant or maneuver.
- The existing validation cohort has been repeatedly inspected and remains exploratory. Confirmatory paper performance needs a genuinely untouched cohort under a frozen corrected protocol. Do not open existing test signals during these experiments.

## Sources and evidence

- Local diagnostic: `outputs_sl_error_budget_v9/diagnostics.json`, `sl_error_budget.py`.
- [Wheel-INS2: simultaneous wheel/body IMUs and state estimation](https://arxiv.org/html/2012.10593).
- [TLIO: relative displacement, uncertainty and bias-aware fusion](https://arxiv.org/html/2007.01867). Its discussion of correlated errors cautions against assuming longer overlapping windows improve trajectory accuracy.
- Research review: `research_docs/research-observed-reference-improvement-plan.md`.

Global1–10 mm IMU-only performance remains unproven. The proposed sequence addresses identified10–20 cm errors first and separates genuine reconstruction improvements from reference/protocol changes.
