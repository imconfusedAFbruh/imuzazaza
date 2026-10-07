# Trajectory residual loop audit: v16, v19, v21

Audit date: 2026-10-03. This is an independent source and numerical audit of the sealed exploratory models. No models, original manifests, reference masks, or acquisition files were changed. No test recordings were loaded.

## Numerical results

The new CPU audit reproduced every one of the 71 validation recording position RMSE values for v16 and v21 exactly, including the four-participant aggregate. The predictor received only setup, IMU timestamps, IMU samples, IMU validity, and the previously frozen IMU startup initialization. Adding reference objects that raise an exception if converted to an array changed neither predictor output: maximum motion difference was zero.

| Check | Result |
|---|---:|
| v16 equal-participant mean trajectory RMSE | 104.451672 mm |
| v21 equal-participant mean trajectory RMSE | 102.585179 mm |
| Largest difference from sealed per-recording RMSE, both models | 0 m |
| Largest change from poisoned reference fields, both models | 0 |
| Recomputed v21 full-training nonlinear bounds difference | 0 |
| Training/fold participant overlap | None |
| Selected v21 endpoint Jacobian numerical derivative error | <=2.35e-8 |
| v19 stored endpoint Jacobian derivative error | <=2.77e-8 |

Artifacts: `outputs_trajectory_loop_audit/audit.json`, `reproduced_trials.csv`, and `training_endpoint_support.csv`. The independent audit uses the sealed reference cache through its provenance-checking loader. Its numerical Jacobian checks four representative columns, including both intercepts, on one training recording with a 1e-6 perturbation. This checks the local analytic derivative away from clipping and angle branch boundaries; it does not prove every parameter or boundary case.

## Fold separation and nonlinear preprocessing

The correction holdout consists of No.3, No.8, No.15, and No.20. The correction fit excludes every recording of those participants across dates. The 473-recording training cache contains no validation records. v21 computes the additional 40 product-feature clipping bounds from eligible labels in the correction fit subset before inner-fold evaluation; its mean, standard deviation, weights, and output residual caps are then fit on that same subset. After selecting the candidate, it recomputes these quantities using all 473 training recordings and evaluates validation once for that experiment.

This ordering is numerically material: the maximum absolute difference between fit-subset and full-training product bounds was 8.601665 in feature units. Recomputing the full-training bounds reproduced the saved model exactly. Bounds are separate for each acquisition setup, while the selected basis, regularization, endpoint weight, and gain are global. Reference label availability selects valid training samples for fitting preprocessing; reference values and masks do not enter the deployed predictor.

v19 initializes its total applied coefficients and caps at half the v16 raw values, reproducing v16's gain 0.5. Its nonlinear derivative zeros saturated-output sensitivities. Training objective line search is training-only, and checkpoint selection uses the fixed inner fold. Selected iteration 1 is the original v16 candidate; later training-objective improvement did not establish a trajectory improvement on the fold. There is no evidence from this experiment that iterative refinement is a better model.

**Whole-pipeline independence is not established by this inner fold.** The inherited calibration/base model was previously fit using these training people. The fixed fold assesses a correction conditional on that inherited model, not a newly trained whole pipeline that has never seen those people. Repeated use of the four validation people for the broader research loop also makes the reported numbers exploratory. These are not untouched final-test results.

## Endpoint geometry and optical gaps

v16 uses first-order SE(2) endpoint residuals at 1, 3, 5, and 10 seconds. Each endpoint pair requires observed reference endpoints and uninterrupted IMUs. The endpoint is expressed relative to the starting body frame. The analytic derivative includes the starting-frame heading term, cancelling sensitivity to accumulated yaw before that local interval. The finite-difference audit confirms that cancellation locally. Training uses the reference pose at each interval start to define labels; inference integrates continuously from the single permitted initial reference pose and never resets to later reference poses.

The observed training cache supplies 30,640 endpoint pairs. Of these, 10,543 bridge one or more optical gaps. This creates a real difference in label support: endpoint positions can constrain net displacement over an unobserved interior, but do not establish what happened at every missing frame. No interpolated optical path is treated as a measured interior path for this loss.

Initially, 4,807 pairs appeared to have raw heading residuals larger than pi before circular wrapping. A second train-only decomposition found **all 4,807 occurred across optical gaps**, and **zero occurred among the 20,097 continuously observed pairs**. This is consistent with the reference heading's separately unwrapped observed segments having different 2pi branches. It is not evidence that the estimator missed complete turns. The circular endpoint heading residual is therefore appropriate for endpoint orientation, but orientation at two endpoints alone cannot identify a hidden full rotation count during an optical gap. Dense observed derivative labels and shorter endpoints provide additional constraints where available.

Additional artifacts: `outputs_endpoint_alias_diagnosis/summary.json` and `trials.csv`. This audit did not choose a mask or correction from these counts.

## Remaining structural limits

No numerical or reference-input leakage defect was found in the audited selected v16/v21 predictors. The audit supports their implementation integrity for this saved benchmark, not absolute millimeter accuracy or sensor calibration correctness.

- v16/v21 endpoint fitting remains a first-order approximation around the inherited ridge motion. Gain and clipping make the final integrated path different from the linear training approximation. v19's unsuccessful generalization illustrates that reducing the training objective is insufficient.
- Product features are empirical nonlinear motion terms. Their fitted weights cannot be interpreted as physical skid coefficients or verified SI sensor scales.
- Initial reference pose and optical/IMU synchronization are external inputs permitted in this benchmark. The numerical reproduction is conditional on those frozen inputs; it is not an IMU-only global-pose system.
- Gravity startup initialization only establishes tilt, with the explicit frozen fallback when no usable startup stationary interval exists. It does not establish mounting forward azimuth. The known sensor encoding and reference-geometry uncertainties remain unresolved.
- Offline temporal context is retained. These scores cannot be presented as zero-latency online performance without a separate causal experiment.

## Source hashes

Full SHA256 provenance is in `outputs_trajectory_loop_audit/audit.json`.

| Source | SHA256 |
|---|---|
| motion_endpoint_experiment_v16.py | 48ff7ea7b16cd598641bbdd88482438a7c1e70c91ba558461386de3b5e8f2098 |
| motion_endpoint_iterative_v19.py | 2411e4fdc8414458706668a370136abffc7febb324d0303d74db8f069e8ae96b |
| nonlinear_endpoint_experiment_v21.py | 2c8e8a038374eb5ba587635bb278035887dcbf71c708dd86ed03cfb119a21813 |
| trajectory_loop_audit.py | 5cc3dffdf71efea7af757bb97f95cd1d4608c224581c01ec8761e6a3e050fe82 |

The saved audit also hashes all three inference loaders and the v16/v21 artifact manifests. All findings above are based on local source and numerical evidence; no external method claim was needed for this integrity audit.
