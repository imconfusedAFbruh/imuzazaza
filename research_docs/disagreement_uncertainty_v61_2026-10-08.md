# v61: TRAIN-only wheel/body disagreement uncertainty — rejected

Hypothesis: center-only acceleration increments, compared with wheel-derived
speed increments and adjusted for slow bias/sample-age uncertainty, predict
forward-speed error variance better than speed and braking magnitude alone.

**Result: the confidence model fails. Do not build a smoother from it.** Ranking
of high-error blocks improves, but calibrated variance prediction and worst
participant robustness worsen. No trajectories, yaw or clocks were changed.

## Exact scope and fitting

- 207 identified target TRAIN recordings; 12 participants in the three frozen
  v24 participant folds; 11,851 nonoverlapping 0.2 s held-participant blocks.
- Frozen v42 TRAIN clock/QC/reference support; hashes checked by `load_cache`.
- Outer calibration reuses v56, with exact fitting-ID set equality asserted.
- Within each outer fitting set, the two remaining participant groups supply
  inner OOF examples. For each, calibration and center-only acceleration mapping
  are refitted excluding its inner held participants. The variance models fit
  these OOF baseline speed errors, not in-fit baseline/acceleration estimates.
- Center acceleration mapping: three fold-normalized acceleration components,
  fitting calibration gravity subtraction; ridge alpha 1, equal-person weights;
  target 0.2 s observed forward-speed increment per second.
- Causal smoothing tau 0.05 s; mismatch bias memory 2 s; conservative sensor-age
  envelope 1/104 s times endpoint acceleration/center integrated jerk.
- Variance regression: log block-mean squared speed error plus fixed 1e-6
  (m/s)^2 epsilon; ridge alpha 1; equal-person fitting weights; fitting-only
  variance scale calibration. No hyperparameter search.
- Control inputs: absolute speed and wheel braking magnitude. Candidate adds
  raw discrepancy, bias-centered discrepancy or timing-excess discrepancy.
- All features are constructed from full IMU support before optical label masks
  select blocks for scoring. Reference speed enters fitting targets and held
  diagnostic errors only; it never enters confidence prediction.
- Validation and historical test data were not accessed. Reference preparation
  and clocks remain inherited, so this is not a new prospective evaluation.

## Overall held-participant results

Equal mean across the 12 participant means; NLL omits the common Gaussian constant.
Lower NLL and variance MAE are better; higher Spearman is better.

| Variant | NLL | Variance MAE (m/s)^2 | Spearman |
|---|---:|---:|---:|
| Speed/braking control | -1.645223 | 0.019546 | 0.487458 |
| + raw discrepancy | -1.601393 | 0.033417 | 0.634296 |
| + slow-bias centered discrepancy | -1.596691 | 0.031144 | 0.632620 |
| + timing-excess discrepancy | -1.600231 | 0.028851 | 0.615956 |

Center-only acceleration MSE is 0.538366 (m/s²)^2 versus 0.582043 for zero
acceleration: a modest 7.50% average reduction. It is worse than zero for No.4,
No.16 and No.17. These are empirical acceleration maps, not verified mounting or
gravity compensation.

## Timing-excess participant regressions

10/12 participants improve NLL, but only No.4 and No.19 pass the frozen <=1.05
variance-MAE ratio guard. No.19 has the largest NLL regression despite its MAE
guard passing; one metric alone would hide failure.

| Participant | NLL delta versus control | Variance MAE ratio |
|---|---:|---:|
| No.1 | -0.054520 | 1.057373 |
| No.13 | -0.014132 | 1.481961 |
| No.15 | -0.041090 | 1.235126 |
| No.16 | -0.047951 | **2.271266** |
| No.17 | -0.164890 | 1.508558 |
| No.19 | **+0.965358** | 1.028854 |
| No.20 | -0.006399 | 1.156598 |
| No.3 | -0.095695 | 1.966334 |
| No.4 | -0.040239 | 1.044493 |
| No.6 | -0.032952 | 1.140604 |
| No.7 | +0.080850 | 1.059484 |
| No.8 | -0.008433 | **2.078452** |

## Maneuver evidence

These means pool blocks within each maneuver and therefore do not replace the
equal-person aggregate above. Full maneuver tables preserve all seven classes.

| Maneuver | Control NLL | Timing-excess NLL | Control variance MAE | Timing-excess variance MAE |
|---|---:|---:|---:|---:|
| 10x5 | -1.797627 | -1.796541 | 0.017345 | 0.020802 |
| AR | -0.367022 | +0.096336 | 0.034179 | 0.033324 |
| CR | -2.306804 | -2.360291 | 0.006584 | 0.005815 |
| OS | -1.478381 | -1.267737 | 0.017582 | 0.015741 |
| PS | -0.892498 | -1.133621 | 0.069303 | **0.210995** |
| SL | -1.975874 | -2.005001 | 0.013133 | 0.015084 |
| ST | -1.907688 | -1.944215 | 0.013781 | **0.030273** |

PS and ST variance estimates regress substantially. Timing-excess Spearman
improves within PS 0.6372→0.6556 and ST 0.6099→0.7270, but better ranking does not
establish useful confidence calibration or safer sensor fusion.

## Decision and limitations

Reject this fitted confidence model. The predefined diagnostic requires lower
equal-person NLL, higher rank association, <=1.05 worst-person MAE ratio, and a
center acceleration map better than zero. It fails NLL and the worst-person
guard. No observer/smoother is built and no trajectory accuracy gain is claimed.

The result does not disprove every uncertainty model. It falsifies this small
log-variance ridge and conservative sensor-age adjustment as a robust fusion
confidence model. In particular, new participant dynamics produce variance
miscalibration. Accelerometer pitch/lever-arm errors and shared wheel/body
information remain uncontrolled. Actual sensor phase and device clock covariance
are unobserved; the 1/104 envelope is a conservative bound rather than measured
Gaussian noise. Future nonlinear or monotonic calibration needs a new nested
protocol and cannot be selected from validation.

Synchronized trajectory RMSE, route RMSE, Fréchet, P95 route distance, endpoint,
heading and path length are unchanged because this diagnostic produces no
trajectory correction. Their measurement is not evidence of this model working.

## Reproduction and verification

Run `python disagreement_uncertainty_v61.py` only in a fresh artifact location;
the script refuses to overwrite the completed `outputs_disagreement_uncertainty_v61`.
Script SHA256: `ad02713df078e58f7e2ff3c3cb7beafd4283d7f965f0e0e9018b889b26ed78c7`.

`python test_disagreement_uncertainty_v61.py` passed synthetic truth-feature
invariance and no-IMU-gap-bridge checks. Replacing optical speed by speed+999
changes diagnostic targets while leaving every confidence feature identical.

Evidence: [run](../outputs_disagreement_uncertainty_v61/run.json),
[protocol](../outputs_disagreement_uncertainty_v61/protocol.json),
[all participant pass/fail rows](../outputs_disagreement_uncertainty_v61/participant_pass_fail.csv),
[held block predictions](../outputs_disagreement_uncertainty_v61/held_blocks.csv),
[fold models and fit IDs](../outputs_disagreement_uncertainty_v61/fold_models.json).

Mechanism/proposal sources and prior v11 rejection are documented in
[uncertainty_slip_options_2026-10-08.md](uncertainty_slip_options_2026-10-08.md).
