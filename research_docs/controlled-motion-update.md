# Controlled motion experiments: 4 October 2026

| Comparator | RMSE mm | Interpretation |
|---|---:|---|
| Original v21 | 102.585 | Existing exploratory minimum |
| v24 / v25 control | 108.950 | Conservative current control |
| v25 braking only | 106.309 | Selected on three training folds |
| v25 quiet yaw only | 108.880 | Quiet-state eligible 1/71 |
| v27 matched combined | 106.228 | Same braking gain; heuristic smoother |
| v26 independently refitted | 219.749 | New simpler motion model; rejected |
| v28 braking_0.5 | 102.297 | Braking extension of stronger base |

v28 selection: {"candidates": [{"name": "braking_0.0", "slip_gain": 0.0, "yaw_gain": 0.0, "smooth": 0.0, "score": 0.14003032176779487, "worst_person_ratio": 1.06470267238425}, {"name": "braking_0.25", "slip_gain": 0.25, "yaw_gain": 0.0, "smooth": 0.0, "score": 0.13925425332083533, "worst_person_ratio": 1.059731166167014}, {"name": "braking_0.5", "slip_gain": 0.5, "yaw_gain": 0.0, "smooth": 0.0, "score": 0.13883489449259598, "worst_person_ratio": 1.0619626397557642}], "selected": null, "passes_original_ridge_guard": false, "preferred_over_v24_on_training_folds": false, "fallback": {"name": "conservative", "basis": "physical_products", "alpha": 0.3, "endpoint_weight": 1.0, "gain": 0.25, "score": 0.14219886070633056, "worst_person_ratio": 1.0065374035424897}, "selected_before_validation": true}

Quiet yaw-state support: 1/71 validation recordings. All 71 accepted records retained. No test data read.

Conditional v25 refits the v24 correction and new components within folds; inherited calibration/neural stack remain conditional. Independent v26 refits empirical calibration and every parameter of its new simpler learned motion model, rather than refitting the original neural stack. All branches retain benchmark clocks, optical geometry, QC and reference masks. This is not full independent preprocessing validation.

v25 braking uses 60 empirical temporal features: center acceleration/gyro, wheel speed/derivative, yaw disagreement, continuous braking/stopped gates and interactions at -0.5/0/+0.5 seconds. Constrained forward-only normal equations combine rate labels and 1/3/5/10-second endpoints; alpha .3, training-only scales/caps. Gain .25/.5 selected by pooled twelve-person folds and <=5% regression vs its control.

Yaw correction is a bounded zero-rate model-output state estimated during conservative IMU-only quiet intervals, not a verified 3D attitude or sensor calibration. Min1.5s quiet, .5s edges, max .02rad/s state, decay10s. Future quiet intervals make it offline.

Combined smoothing minimizes velocity measurement disagreement plus acceleration-increment disagreement with confidence inferred from in-fit residuals, per braking regime. Variances are heuristic and not independently calibrated; correlated samples are not modeled as independent sensor measurements. This implements a controlled empirical mechanism comparator, not a complete TLIO/Wheel-INS2 system.

User mounting update: both wheel IMUs are off-axis and face outward; center IMU faces backward. Exact rotations, lever-arm vectors and raw/library/CSV packing remain unknown. Actual acquisition remains +/-2g and +/-2000degrees/s.

The original 102.585mm result is exploratory. New validation comparisons were repeatedly inspected. No lower observed score establishes blind generalization or millimeter accuracy. Negative branches and all candidate tables are preserved.
