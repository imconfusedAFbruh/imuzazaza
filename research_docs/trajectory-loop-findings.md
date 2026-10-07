# Trajectory improvement loop — findings and current candidate

## Update: 4 October 2026

Controlled components and a new independent empirical-motion branch are complete. See `research_docs/controlled-motion-update.md` and `outputs_controlled_motion_review/` for the newer evidence. The prior findings below describe the preserved 3 October state.

The conservative v24 control improves from 108.950 to **106.309 mm** with v25 forward/braking correction. All four validation participant means improve; worst training-person regression is 1.91% versus v24 and 2.25% versus original ridge. Use v25 as the conservative candidate for the next separately frozen evaluation. Quiet-yaw and matched confidence-weighted smoothing give no clear further gain. Only one of 71 validation recordings meets the new quiet-state gate.

The v28 extension of v21 reaches 102.297 mm but fails the original-ridge training guard (6.20% worst participant regression). It is an exploratory comparator, not promoted. Original v21 remains the prior minimum-error comparator at 102.585 mm. The newly refitted simpler empirical model reaches 219.749 mm and is rejected. Its calibration and every motion-model parameter exclude held people within folds; it does not refit the inherited neural stack, and benchmark clocks/reference/QC remain fixed. A fully independent refit of that existing stack remains outstanding.

Reference-free replay matches all 71 conditional motion arrays exactly and the independent branch within 1.8e-18. All versioned artifact hashes match. These checks establish reproducibility, not independent generalization. No test acquisitions were accessed. CSV encoding/full rotations remain unknown; the user confirms off-axis outward wheel mounts and a backward-facing center sensor. Updated PDF: `output/pdf/trajectory_methodology_and_results_updated.pdf` (109 pages, original 71-page atlas preserved).

Date: 2026-10-03. This is an exploratory development report, not final test performance. The loop repeatedly fits training-only corrections, evaluates the same validation cohort, plots predictions, reads failures, and changes the next experiment. The original frozen pipeline and test lock remain preserved. No test acquisitions were reopened in this loop.

## Measured improvement

The lowest completed overall score is v21: **102.585 mm**, compared with paired CPU ridge **116.899 mm** (14.314 mm / **12.24%** reduction). The score is the equal-participant mean of trial 2D position RMSE. Each trial uses square-root mean squared Euclidean XY error on camera-observed reference frames, followed by equal weighting of participants. It is not a coordinate-wise or pooled-frame RMSE.

All four participant and all seven maneuver means improve versus ridge. This does not establish uniform trial improvement. Slalom No.14 trials1/2/3 worsen approximately137→166,176→184,105→114 mm; No.18 SL1 worsens164→216 mm. The new gallery displays these failures. v16 has a lower SL average119.725 mm than v21's122.943 mm, while v21 has the lower overall error. No participant/date/maneuver-specific winner is deployed.

| Method | Overall RMSE(mm) | Mechanism / outcome |
|---|---:|---|
| Original ridge |116.899|Paired CPU control|
| v12 yaw TCN |115.918|Yaw-only rate plus observed heading intervals; mixed generalization|
| v13 nonlinear temporal ridge |118.172|Nonlinear point-loss comparator rejected|
| v14 gravity/temporal features |112.622|Forward/yaw temporal correction; all participant means improve|
| v15 three-seed yaw ensemble |114.744|Reduces seed variation; September25 SL still regresses|
| v16 observed endpoint correction |104.452|Coupled forward/yaw rate and relative SE2 interval constraints|
| v17 forward context |111.077|Some braking improvement; major deficit remains|
| v19 iterative endpoint refinement |104.452|Training objective improves, fold worsens; retains v16|
| v20 channel blend |104.452|No complementarity gain; retains v16|
| v21 nonlinear endpoint correction |102.585|Adds eight kinematic products over five temporal contexts|
| v22 stronger endpoint weighting |116.879|Lower training-fold error fails to generalize; rejected|
| v23 offline gravity-direction state |103.445|Slightly improves SL, worsens overall; retain v21|
| v24 three-fold conservative selection |108.950|More guarded selection over twelve training participants|

The experiment journal is `outputs_trajectory_loop/progress.md`.

## Final development choice versus minimum validation score

The minimum measured validation error remains **v21,102.585mm**. The more conservative **v24,108.950mm** candidate is selected over three disjoint four-person training folds covering all twelve target training participants. Each fold independently refits correction normalization, nonlinear clipping bounds, weights and caps; inherited base/calibration remain frozen, so whole-pipeline independence is not claimed. Earlier unmapped training sessions remain in each fit. A shared maximum5% participant regression guard is applied to all twelve participants.

The conservative alpha0.3/endpointweight1/gain0.25 candidate passes with worst training participant regression0.65%. The v21 setting fails the broader guard at6.47%; the aggressive v22 setting fails at33.46%. This explains why a favorable single fold can select a correction that regresses other people. **Use v24 as the conservative candidate for the next separately frozen evaluation; keep v21 as the exploratory minimum-error comparator.** Do not report the minimum inspected validation score as a new blind test result.

v23 estimates gravity unit-direction states from quiet IMU observations within continuous IMU runs using frozen calibration and fixed gates. It does not refit held-out bias, scale or gravity magnitude. Its103.445mm score does not beat staticv21; no additional gain is claimed. The estimator uses future retained IMU samples and is explicitly offline. Preparation and diagnostic serialization failures were preserved; finalization did not refit or reevaluate the selected model.

## What worked

The strongest gain came from **changing supervision**, not increasing network size: train with observed interval displacement and heading targets at1/3/5/10seconds, jointly correcting forward velocity and yaw. Intermediate optical gaps remain masked; no invented optical path is used. Interval Jacobians account for the effect of yaw on XY displacement. Inference only predicts IMU corrections; it does not optimize against held-out optical coordinates.

v21 adds predeclared nonlinear kinematic products to v14's75 temporal features: forward*yaw, squared forward/yaw, wheel mean/difference products, acceleration/gyro norm squares, and vertical-yaw interaction. Product clipping bounds, normalization, weights and residual caps are fitted using training data. These remain empirical features; they do not prove physical slip or verified SI conversion. The residual's lateral channel remains exactly ridge.

Each correction uses a training participant fold (No.3/8/15/20) for the finite candidate selection and then refits all473 training recordings before its71-recording validation comparison. New normalization and product bounds exclude the fold during selection. The inherited calibration and pretrained predictors previously saw those training participants, so this is conditional correction selection, not independent whole-pipeline cross-validation.

## More epochs and more fitting

More epochs did not consistently help. At fixed yaw gain0.5, training-fold trajectory RMSE at epochs3/6/12/24/36 is approximately147.0/146.6/145.5/154.6/149.7 mm. Training loss keeps falling after12 while trajectory error worsens. Epoch12 was selected before validation. Chart: `outputs_trajectory_loop/epochs_vs_trajectory.png`.

v19 reaches the same conclusion for repeated nonlinear endpoint fitting: decreasing the actual clipped training objective does not improve the participant fold. v22 also shows that much stronger endpoint weighting can improve the training fold and severely worsen No.14/18 validation. These are preserved negative comparisons, not hidden unsuccessful runs.

## Image diagnosis and remaining limits

- Late SL bending is accumulated heading error. Average derivative-label error can conceal integration drift and unsupported optical intervals.
- No.18 PS2 loses roughly0.5m during braking because wheel-derived speed falls before observed body motion. The new forward model reduces error, but does not resolve this interval. Timing evidence does not establish a global0.8s chassis latency: training clock residuals are milliseconds, and a longer±1s context did not win.
- Most target acquisitions already start active. Only one validation recording passed the initial-five-second stationary gate, so v14/v21 gains cannot be attributed chiefly to per-record mount initialization. Quiet intervals found later cannot be substituted silently for initialization-only history.
- No.5 AR2/AR3 retain a possible180° physical-left/right or initial-heading ambiguity. Two optical markers cannot resolve physical front independently. No automatic flip or reference-based exclusion was applied.
- No.5 CR3 is genuine near-in-place rotation; its small irregular midpoint path is not repaired into a circular template.
- Sensor CSV encoding, full mounting/lever-arm vectors, absolute reference uncertainty and global coordinate convention remain unverified. Preserve the user's±2g acquisition statement. Rest norm≈8200 does not prove a different acquisition range. Actual firmware/receiver/library identity and simultaneous raw/float/CSV values are needed to establish encoding.

There are71 accepted validation recordings from four participants, versus84 planned repetitions:12 each10x5/AR/CR/SL/ST,8PS and3OS from two people. Thirteen missing repetitions remain visible in the overview sheets; their existing QC reasons are preserved. No final test result or millimeter accuracy is claimed.

## Evidence and recommended direction

The independent audit exactly reproduced all71v16/v21 scores and confirmed that poisoned reference fields do not change predictions. Training-fold exclusion and nonlinear bounds were checked. Sampled endpoint Jacobians agree numerically to about2.4e-8. All raw heading residuals exceedingπ occurred across optical gaps, consistent with separately unwrapped reference segments; none occurred in continuously observed pairs. Circular endpoint orientation is appropriate, but hidden full-turn counts across gaps remain undetermined. See `research_docs/trajectory-loop-audit.md`.

The practical direction is **calibrated wheel/body motion plus domain-trained interval corrections**, with robust attitude/bias state handling and uncertainty. [Wheel-INS2](https://arxiv.org/abs/2012.10593) provides the physical foundation including mounting and rotating lever arms; its drift metrics do not establish path RMSE or millimeters here. [Gyroscope denoising](https://arxiv.org/html/2002.10718) motivates integrated orientation supervision and cautions against overly long trajectory objectives. [TLIO](https://cathias.github.io/TLIO/) supports interval displacement uncertainty and bias estimation, while demonstrating failures outside pedestrian training distribution. None establishes an RL advantage for this dataset.

Current measured candidate: `nonlinear_endpoint_inference_v21.load_nonlinear_endpoint()` (CPU, IMU-only optional startup state, inherited1.28s future context). Full71-case gallery and PDF: `outputs_trajectory_best_v21/`. The complete previous comparisons and negative experiment artifacts remain in their versioned folders. A separate final test is needed after the development choice is frozen; this reused validation cannot serve as a blind final evaluation.
