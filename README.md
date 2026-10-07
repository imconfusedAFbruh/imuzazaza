# Wheelchair trajectory reconstruction

## Repository contents

Source code, configuration, research notes, and the latest trajectory PDF are included. Raw recordings (`c3d/`, `imu3/`, `samplerawdata/`), fitted experiment artifacts (`outputs*/`), and temporary files remain local. Existing inference/report scripts require those local experiment artifacts; cloning this repository alone does not provide a trained model or the dataset.

Research continuation instructions are in `research_state/NEXT_SESSION.md`. The latest report is `output/pdf/trajectory_research_accuracy_audit.pdf`.

Offline three-IMU reconstruction of the 2D wheel-hub midpoint, evaluated against Qualisys. Current code implements protocol amendment v2. The original evaluated artifacts remain immutable in `outputs/`; their source snapshot is in `experiments/v1_source/`. Current runs default to `outputs_amended_v2/`. The same participant assignments are preserved. Because the original test was inspected, amended test results are retrospective and cannot be described as a new blind evaluation.

## Run

Python 3.10+ with the packages in `requirements.txt` is required. The current workspace already has these packages.

```powershell
python pipeline.py inventory
python pipeline.py baseline
python pipeline.py learn --epochs 12
python pipeline.py report
python test_pipeline.py
```

`inventory` freezes a seeded participant split before loading signals. `baseline` calibrates on training data and evaluates validation data. `learn` compares the baseline, a regularized linear residual, and two small causal TCN residual models; checkpoints are chosen by equal-participant mean validation trajectory RMSE. This establishes the best of the tested candidates, not a globally optimal model.

After the estimator and evaluation protocol are frozen, run:

```powershell
python pipeline.py final-test
```

This runs the amended retrospective test and writes a lock preventing further development in that output directory. It reports the baseline and selected model. Do not use final test results to revise the estimator, filtering, calibration, split, or model selection. A new output directory does not make an already-inspected participant set unseen again.

Optional `--root PATH` and `--out PATH` select the dataset and output directories. Keep the frozen split and manifests with the paper materials.

## Outputs

- `outputs_amended_v2/split.json`: participant assignments and identity confirmations.
- `outputs_amended_v2/inventory.csv`: pairing inventory, including unpaired recordings.
- `outputs_amended_v2/qc_train.csv`, `qc_validation.csv`, and eventually `qc_test.csv`: accepted/excluded trials and reasons.
- `outputs_amended_v2/calibration.json`: empirical raw-to-motion scales, intercepts, axes, and training trial identities per acquisition date.
- `outputs_amended_v2/run.json`: settings, split and source hashes, versions, and calibration provenance.
- `outputs_amended_v2/baseline/validation_*`: trial metrics, participant means, maneuver means, and summary.
- `outputs_amended_v2/baseline/validation/trajectories/`: trajectory CSV exports and PNG plots.
- `outputs_amended_v2/selection.json`: candidate comparisons and validation checkpoint history.
- `outputs_amended_v2/validation_report.md` and `validation_comparison.png`: comparison report and figure. `report` refreshes validation exports without refitting models.
- `outputs_amended_v2/normalization.json`, `ridge.npy`, and `tcn*.pt`: training-only normalization and fitted corrections.
- `outputs_amended_v2/final_test_lock.json`: final evaluation freeze record, created only by `final-test`.
- `outputs_amended_v2/final_test_report.md` and `final_test_summary.json`: frozen held-out results and coverage limitations.
- `outputs_amended_v2/geometry_policy.json`: reference-separation bands and rigidity thresholds derived from training C3Ds only.
- `outputs_amended_v2/protocol_amendment.json`: parent experiment hashes, changes, and already-inspected-test disclosure.

## Evaluation protocol

Sept. 24 and Sept. 25 each contribute six training, two validation, and two test participants: 12/4/4 total. All maneuvers and repetitions follow their participant. Earlier sessions supply training data only, based on the researcher's confirmation that these participants do not overlap with the 20 target participants. Their trial-to-person mapping is incomplete and remains a provenance limitation.

The baseline converts left/right wheel gyro signals into wheel speeds and frame gyro into yaw rate using robust training-only regressions. Training fits midpoint speed jointly from the selected left/right gyro channels, avoiding a fixed hub-width assumption in forward-speed calibration. Their average supplies speed; center gyro supplies yaw. Configured track width is still used for the diagnostic wheel-yaw feature and is not claimed to be independently measured. Integration receives the initial reference position and heading. No later reference positions or headings correct the estimate.

Clock mapping uses per-device timestamps and packet arrival timestamps. A training-only bootstrap uses gyro magnitudes to fit axes and scales. A second training pass freezes projected signed center-yaw and calibrated wheel-speed channels for multiple-peak alignment; the same channels are used in validation and amended test. Peak support is chronological and one-to-one. Matches with insufficient correlation, insufficient peak support, or competing offsets are excluded. This is offline evaluation with external clock alignment, not an independent live navigation result. QC reports distinguish reference, clock, and synchronization rejection stages and retain correlation, runner-up, and peak-timing diagnostics.

The reference requires valid left/right markers, separation inside bands learned from training acquisitions, and within-trial rigidity. The wider band is supported by training participant No.20. These are optical-marker distances, not measurements of actual hub width. Derivatives are filtered independently within valid segments. Reference gaps are masked; missing reference never resets reconstruction. An IMU timing gap stops reconstruction rather than inventing motion, and reconstruction coverage is reported. Endpoint percentages are withheld when gaps prevent a complete reference path length.

Primary metric is position RMSE without fitting trajectory rotation, translation, or scale after initial-pose alignment. Supporting metrics include circular heading RMSE, valid endpoint drift, and 1/5/10 m segment displacement errors aligned at each segment's starting heading. Segment alignment is used only for the relative metrics; it never corrects the full reconstructed path. Participant and maneuver tables expose uneven trial coverage.

## Learned corrections

Twenty causal features contain calibrated wheel/center rates, wheel-versus-frame yaw disagreement, trailing rate derivatives, gravity-normalized acceleration magnitudes/projections, and off-axis gyro magnitudes. Gravity scales, biases, feature normalization, and residual bounds are fitted on training only. Gyro isotropy and configured radius remain assumptions. Windows and normalization balance known participant groups; older unidentified participants are grouped by date and must not be called individually balanced. The TCN combines pointwise residual loss with short integrated position/heading loss on complete training reference spans. Residual gains of 0.25/0.5/1 and checkpoints are selected on validation; final model choice includes the physics baseline.

## GRU and uncertainty-filter comparison

The separate `alternatives.py` comparison reads the frozen v2 calibration, normalization and fingerprinted accepted signals without changing that experiment. It trains a 32-unit causal GRU with the same residual targets, participant grouping, loss and epoch budget. A diagonal Kalman rate filter uses learned measurement variance fitted on training only; validation selects its process-variance multiplier. This is a speed/yaw filter, not a full pose-and-bias navigation estimator. It never receives reference motion during reconstruction.

```powershell
python test_alternatives.py
python alternatives.py train --epochs 12
python alternatives.py retrospective-test
```

Outputs are in `outputs_alternatives_v3/`: `selection.json`, `gru32.pt`, `uncertainty.json`, candidate metric tables, `report.md`, and a frozen retrospective test lock. Model selection includes the existing TCN and physics baseline. Previously inspected test participants remain retrospective. The training command refuses to overwrite an already selected comparison.

## Parallel accuracy experiments (v4)

The consolidated findings are in `outputs_accuracy_program_v4/report.md`. New train/validation-only comparisons include a CUDA RoNIN-inspired ResNet, supervised skid proxies, mean-square process covariance, explicit lateral-velocity ridge corrections, and a CUDA forward/lateral/yaw neural residual. The best development candidate scores 0.3685 m versus frozen TCN's 0.3747 m on the same 72 validation recordings/four participants; it improves three participants and worsens one. This is exploratory reused validation, not new independent test performance or millimeter accuracy.

The neural planar candidate uses 1.28 seconds of future IMU context for offline reconstruction. Its training-fitted normalization, weights, full checkpoint history, source hashes and GPU runtime are preserved in `outputs_planar_neural_v4/`. Frozen earlier experiments remain unchanged. Scripts preserve selected runs and refuse to overwrite them.

```powershell
python test_ronin_experiment.py
python test_skid_experiment.py
python test_planar_experiment.py
python test_planar_neural_experiment.py
```

Acquisition firmware/units, marker and sensor geometry, synchronization uncertainty, and independent reference uncertainty must be established before pursuing a millimeter accuracy claim. The oracle diagnostic's submillimeter reference integration error is a numerical consistency check, not achieved IMU accuracy.

## Synchronization refinement (v5)

Run `python synchronization_experiment.py` to build a separate development experiment. It refuses to overwrite `outputs_synchronization_v5/`. After the frozen coarse peak alignment passes, the experiment searches its local basin at 1 ms and then 0.1 ms using native-rate correlation on identical valid samples. It retains the existing peak, correlation and ambiguity gates; position RMSE never selects a lag. The experiment uses only the parent's accepted training/validation recordings and does not revisit exclusions.

On the same 72 validation recordings/four participants, the frozen planar neural model changes from 368.499 to 366.248 mm RMSE (0.61% improvement); three participants improve and one worsens. Frozen TCN changes from 374.739 to 372.276 mm. The physics baseline refitted on 477 refined training recordings changes from 468.933 to 465.705 mm. Original alignment scores reproduce the parent results. No test signals were opened and neural models were not retrained. The report and per-recording alignment diagnostics are in `outputs_synchronization_v5/`.

This local lag resolution does not establish synchronization accuracy or correct residual clock drift. The original pipeline/configuration and evaluated experiments stay frozen; the new script supplies the refinement settings explicitly in its versioned preparation configuration. Actual acceleration range remains researcher-confirmed +/-2 g and CSV encoding remains unverified.

## Planar retraining on refined labels (v6)

`python refined_training_experiment.py` retrains the planar residual using the frozen v5 synchronization caches and refuses to overwrite `outputs_refined_training_v6/`. Feature normalization, target scales and clipping bounds are fitted from refined training recordings only. The inherited TCN and physical calibration stay frozen. The run uses CUDA, the same architecture and a fixed 12 epochs; validation selects checkpoint and gain from 0.25/0.5/1.0. Known participant groups have equal sampling weight; older unidentified participants are grouped by date.

The best retrained checkpoint (epoch 7, gain 0.5) scores 366.318 mm versus the reproduced frozen model's 366.248 mm on the same 72 validation recordings/four participants. The frozen model remains selected. Two participants improve and two worsen; OS/PS errors remain around 1.6 m. This single-seed experiment does not establish an improvement or statistical significance. All 477 refined training recordings and 3,641 eligible windows are used; no test signals are opened. Results, checkpoint, normalization, history, hashes and participant/maneuver comparisons are preserved in `outputs_refined_training_v6/`.

## Observed-reference validity correction (v7)

The former reader accepted zero C3D residuals, including generated leading coordinates with false initial headings. The C3D format marks these as processed points. Across 646 readable training/validation C3Ds, zero residuals exactly match missing camera support. `observed_reference_experiment.py` corrects the rule before reference filtering, requires positive residuals and camera support when the export populates it, and initializes from the first observed synchronized pose. Later reference gaps remain masked and never reset reconstruction.

The controlled correction uses fixed v5 clock alignment and unchanged neural weights. On identical observed frames from 71 validation recordings/four participants, the old reconstruction scores 373.243 mm and corrected initialization scores 118.490 mm. OS changes from 1,574.721 to 109.488 mm; PS from 1,920.428 to 193.911 mm. This is a reference/initialization protocol correction, not improved neural accuracy on the old full-duration benchmark. Four training recordings and one validation recording lack sufficient observed data, leaving 473/477 training and 71/72 validation recordings from the parent's accepted set. See `qc.csv` for duration/heading changes and exclusions. No test signals are opened.

The new reader and output are separately versioned; the original pipeline, sources, results and historic test locks are preserved. Results are in `outputs_observed_reference_v7/report.md`; observation support is audited in `outputs_reference_support_audit_v7/`. Do not use the earlier full-duration RMSE as verified accuracy against original MoCap measurements. Independent optical uncertainty, CSV encoding and clock accuracy remain unresolved. ADR 0003 records the rule and coverage implications.

## Observed-reference model comparisons and corrected trajectories (v8)

On the same corrected 71 validation recordings, a 12-epoch retraining run scores 117.791 mm versus 118.490 mm for the corrected frozen planar model. A training-fitted group-balanced ridge residual over that frozen model scores 116.898 mm (alpha 0.1, gain 0.25), the best of these candidates. All four participant averages improve with the ridge residual, although PS and 10x5 condition averages worsen slightly. These additional model gains are small; the substantial recovery comes from correcting reference validity and initialization.

The report and 71 corrected trajectory plots are in `outputs_reference_recovery_v8/`; `before_after.png` shows the same previously failing OS/PS recordings on identical observed score frames. `observed_ridge_inference.load_observed_ridge()` loads the selected IMU motion predictor, with sealed dependencies and no reference feature access. It outputs forward/lateral/yaw motion; integration still receives one observed initial pose. Models retain 1.28 seconds of future IMU context and inherited v5 clock mapping. Results remain exploratory, not millimeter accuracy or a new blind test. The runner/weights are in `observed_ridge_experiment.py` and `outputs_observed_ridge_v8/`; the independent neural retraining is in `observed_training_experiment.py` and `outputs_observed_training_v8/`.

## Limits to state in the paper

The researcher confirms accelerometer +/-2 g and gyro +/-2000 degrees/s. CSV integer encoding remains unknown; conversion is empirical and must not be described as verified factory scaling. Legacy scale/delay values in the YAML are not used. Geometry starts from configured values, including radius 0.30 m, hub distance 0.52 m, and symmetric reflector offsets 0.066 m.

The reference currently projects onto C3D XY. Confirm the acquisition's Z-up coordinate convention before publication. With symmetric outboard markers and zero camber, their midpoint supplies the hub midpoint. More complex geometry requires additional acquisition evidence.

Reported accuracy is conditional on accepted synchronization/reference quality. Always publish attempted counts, exclusion reasons, reference/reconstruction coverage, and participant-level results alongside averages. Validation results guide development and are not final test performance. Architecture and tuning budget can be revisited using validation only, before opening final test data.

The agreed design and terminology are in `docs/design.md`, `docs/adr/`, and `GLOSSARY.md`.

## Observed-reference improvement build (v9)

`long_horizon_experiment.py` compares the same residual network with short loss and observed endpoint SE(2) losses at 1/3/5/10 seconds. Three predefined seeds use a training participant fold for epoch/gain selection, then refit all training recordings before final validation. The inherited TCN/calibration saw the inner fold previously, so this is conditional selection, not independent whole-pipeline evaluation. Short recordings use supported horizons; empty beyond-record contexts are excluded from BatchNorm. Optical gaps need no invented intermediate poses. Incomplete attempts and their executed sources are preserved.

On identical 71-recording observed validation support, the endpoint ensemble scores 114.057 mm versus the existing ridge's 116.898 mm, but SL worsens from 145.482 to 147.682 mm and two participant averages regress. Endpoint individual seeds score 118.247/123.002/142.175 mm; matched short-loss seeds score 118.870/157.649/138.503 mm. Retain the existing ridge. The preselected endpoint seed 43 scores 123.002 mm overall and 138.525 mm on SL; its selection predates validation.

`observed_sync_experiment.py` rebuilds clocks using observed-only optical features and train-only bootstrap calibration. On a separate paired native timestamp benchmark, ridge scores 116.823 → 116.508 mm, with one participant worsening. Accepted coverage is 465 training/71 validation. `physics_state_experiment.py` implements a bounded empirical yaw-bias comparator; it scores 230.680 mm versus static empirical physics 222.128 mm and does not justify fusion. Unverified sensor encoding/mounts prevent claiming full calibrated attitude INS.

Reports and comparison tables: `outputs_build_v9/report.md`. All twelve paired SL plots and drift/turn/straight diagnostics: `outputs_build_trajectories_v9/`. Build record and audit: `docs/build-v9.md`, `docs/build-v9-audit.md`. Six checkpoints and all seed histories: `outputs_long_horizon_v9/`. `long_horizon_inference.load_endpoint_ensemble()` supplies an IMU-only candidate predictor; the current ridge loader stays selected. No test signals were reopened; below-100 mm overall/SL and global millimeter accuracy remain unproven.

## All trajectories, image diagnosis and correction comparisons (v10–v11)

`outputs_trajectory_report_v10/gallery.html` contains all 71 accepted validation trajectories, with reference, ridge, endpoint ensemble and training-fitted calibration comparison. The folder includes a 71-page PDF, seven maneuver overview sheets, individual trajectory/position/heading panels, cached trajectories, CSV metrics and SHA256 manifests. Plot legends and missing-recording labels were corrected after visual review. Thirteen planned repetitions remain unaccepted; coverage is only 3 OS and 8 PS recordings.

`research_docs/trajectory-findings-v10.md` gives the primary-source method review and image findings: late SL yaw drift, unresolved physical-left/right or initial-heading ambiguity in No.5 AR2/3, genuine near-in-place CR motion, and persistent PS braking displacement loss. Calibration scores 116.255 mm overall / 140.446 mm SL, but worsens PS, OS and one participant, so ridge stays selected. The v11 acceleration smoother failed all 24 nonzero training-fold candidates; its best rejected full-training refit scores 116.918 mm, versus ridge 116.898 mm. Reports, coefficients and braking plots are preserved in `outputs_chassis_acceleration_v11/` and `outputs_chassis_acceleration_v11_rejected_comparator/`. These are exploratory validation comparisons, not final test results or evidence of millimeter accuracy.

## Completed trajectory improvement loop (v12–v24)

The measured exploratory minimum is v21: 102.585 mm overall and 122.943 mm SL, versus paired CPU ridge 116.899/145.487 mm (12.24% overall improvement). All participant and maneuver means improve, but individual failures remain, especially No.14 SL and No.18 PS braking. The v24 conservative three-fold candidate scores 108.950 mm overall /131.316 mm SL. Its training selection covers all twelve target training participants and passes a <=5% worst-person guard; v21 does not pass that broader guard. Use v24 for a separately frozen next evaluation; retain v21 as the exploratory minimum-error comparator.

Best measured plots, all 71 cases: `outputs_trajectory_best_v21/gallery.html` and `all_71_trajectories.pdf`. Final findings: `research_docs/trajectory-loop-findings.md`; experiment journal/epoch chart: `outputs_trajectory_loop/`; independent exact reproduction and reference-poison audit: `research_docs/trajectory-loop-audit.md`. More epochs, iterative endpoint refinement, channel blending and stronger endpoint weighting did not establish consistent improvement. All failed comparisons and executed sources remain preserved.

Inference: `nonlinear_endpoint_inference_v21.load_nonlinear_endpoint()` for the exploratory minimum; `participant_folds_inference_v24.load_participant_folds()` for the guarded alternative. Both are CPU predictors using only IMU and optional IMU startup initialization, returning forward/lateral/yaw motion. Supply the initial pose separately to `integrate_planar`; neither uses later optical poses. Most target recordings lack stationary startup. Sensor integer encoding and full mounting geometry remain unverified. No test acquisitions were reopened in this loop; reused validation is not a blind final test. Original frozen pipeline and model artifacts remain unchanged.
