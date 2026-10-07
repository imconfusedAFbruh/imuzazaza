# Three-participant-fold robustness comparison v24

Three folds were declared before computation: A=No.3/8/15/20, B=No.1/4/13/16, C=No.6/7/17/19. Earlier training recordings always stayed in the correction fit. For every fold, nonlinear clipping bounds, normalization, output caps, and correction coefficients were refit excluding every recording of held participants. The inherited base/calibration remains conditional rather than independently retrained.

Selection pooled the 12 target training participants with equal participant weights and required no participant mean to worsen by more than 5% against unchanged ridge. Zero remained eligible. Parameters were selected before the full 473-recording refit and 71-recording validation evaluation.

| Candidate | Pooled training RMSE mm | Worst participant change | Eligible |
|---|---:|---:|---|
| Zero/ridge | 149.168 | 0% | Yes |
| v16 linear, alpha .1 EW1 gain .5 | 140.526 | +7.61% | No |
| v21 nonlinear, alpha .1 EW1 gain .5 | 140.030 | +6.47% | No |
| Conservative nonlinear, alpha .3 EW1 gain .25 | 142.199 | +0.65% | Yes, selected |
| Nonlinear, alpha .1 EW3 gain .5 | 140.172 | +12.44% | No |
| Aggressive nonlinear, alpha .01 EW10 gain .75 | 146.911 | +33.46% | No |

The aggressive candidate achieved 129.220 mm on fold A but 167.022 mm on fold C. Higher endpoint weight does not generalize consistently across participant groups. The stricter multi-fold guard selects a smaller correction rather than the lowest pooled mean alone.

The selected model's final exploratory validation RMSE is **108.950 mm**, versus the paired CPU ridge's **116.899 mm**. Heading RMSE is 1.39835 degrees. SL is 131.316 mm and PS is 192.886 mm. The four participant means are 79.303, 102.189, 140.476, and 113.830 mm for No.10/14/18/5. This improves the baseline but does not replace v21's 102.585 mm as the smallest observed validation aggregate. It is a differently selected robustness alternative; choosing between them after viewing validation is another exploratory choice.

Artifacts are sealed under `outputs_participant_folds_v24/`, including the predeclared grid, per-recording fold scores, selected parameters, fitted model, validation scores and SHA256 manifest. Source is `participant_folds_experiment_v24.py`; inference is `participant_folds_inference_v24.load_participant_folds()`, which delegates to the audited IMU-only v21 loader and checks saved provenance. Loader construction succeeded after artifact sealing. No test recording was accessed, and no existing source or artifact was changed.

This closes the requested finite robustness comparison. It does not establish absolute reference accuracy, sensor units, mounting yaw, or an untouched final-test claim.
