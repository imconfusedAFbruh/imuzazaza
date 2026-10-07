# Offline wheelchair reconstruction design

## Confirmed decisions

- First deliverable: an offline pipeline that reconstructs wheelchair trajectories from three IMUs and measures error against Qualisys. Selected by the user in interview round 1.
- Paper target dataset: Sept. 24 and Sept. 25 capture sessions. Earlier dates may be used for model training.
- Evaluation: held-out recordings with leakage prevention.
- Trajectory: a 2D path of the midpoint between wheel hubs.
- Partition unit: participant across every capture date. Split participants before creating windows; fit calibration, normalization, and model parameters on training data only. Keep the final test partition untouched during development.
- Build sequence: establish the physics baseline, then select the strongest supported learned model using development data.
- Identity confirmation: the user confirms No.1-20 are 20 distinct people.
- Cross-date identity confirmation: the user confirms earlier-session participants do not appear among No.1-20. Earlier-session recordings are eligible for training, subject to pairing and quality checks.
- Target participant split: 12 training, 4 validation, 4 test, balanced across dates (6/2/2 per date). Every maneuver and repetition from a participant follows that participant's assignment; freeze assignments before development.
- Primary metric: trajectory position RMSE in meters. Supporting metrics: endpoint drift, heading error, and error over fixed travel distances. Report per participant and maneuver, aggregate with equal participant weights, and list excluded trials with reasons.
- Hardware range supplied by user: accelerometer +/-2 g and gyro +/-2000 degrees/s. This contradicts the current config accelerometer range of +/-16 g; the conversion from CSV integers remains to be established.
- Synchronization method: use corresponding peaks in C3D-derived motion and IMU signals. Signal choice, peak matching, and rejection rules remain to be specified.
- Missing MoCap: continue IMU reconstruction, mask unavailable ground truth from scoring, do not reset on marker return, and report coverage. Long gaps must not be interpolated into evaluation labels.
- Baseline milestone: reproducible, correctly calibrated reconstruction with documented errors. Choose the learned-model improvement target from validation results before accessing the final test set.
- Evaluation alignment: MoCap may provide the initial position and heading only, from the first synchronized camera-observed pose. Do not fit rotation, translation, or scale over the full evaluated trajectory. Require positive C3D residuals and camera contributions when populated; processed zero-residual coordinates are not accepted as original observations. Filter/differentiate separately within observed segments (ADR 0003).
- CSV encoding: unknown. User documentation describes conversion from g and degrees/s using saved sensor scales but does not identify register counts versus scaled readings. Use training-only empirical calibration and document the conversion as empirical.
- Peak synchronization: match multiple peaks to estimate one offset per trial, reject ambiguous matches, and use a fixed wheel-speed fallback when turning peaks are insufficient. Freeze the procedure before final testing.
- Interface: a Python command-line pipeline producing a quality inventory, frozen participant split, trajectory plots, and paper metric tables, with run settings and calibration parameters saved.

## Proposed execution details for final confirmation

- Generate a deterministic participant split using seed 42, stratified by date, before inspecting target signal quality or fitting parameters. Save the 6/2/2 assignments per date in a manifest.
- Earlier sessions supply training data only. Verify pair lineage and quarantine ambiguous or unmatched IMU/C3D pairs. Earlier trial-to-participant mapping remains an inventory limitation; the user confirms no overlap with target participants.
- Fit sensor conversions, axes/signs, geometry adjustments, gyro biases, normalization, and learned parameters on training participants only. Use validation results for model and development-setting selection; never use final test scores for selection.
- Baseline: derive forward speed from wheel gyros and yaw rate from the frame gyro, then integrate a planar hub-midpoint trajectory. Determine mounting axes and signs using training data, accounting for acquisition setups.
- Start with configured geometry: wheel radius 0.30 m, hub distance 0.52 m, reflector offset 0.066 m, zero camber. These are configured values; any fitted adjustment uses training data. Refit unexplained legacy scales and delay rather than treating them as validated calibration.
- Derive rates and sample timing from device timestamps and C3D metadata. Detect quiet intervals instead of assuming five stationary seconds at each trial start.
- MoCap supplies reference construction, evaluation clock alignment, and initial position/heading. Subsequent MoCap motion does not correct reconstruction. The paper must state the known-initial-pose and external-clock-alignment evaluation assumptions.
- Develop peak selection and synchronization quality thresholds on training data and apply fixed rules later. Log failed or ambiguous synchronization rather than hand-adjusting offsets after viewing errors.
- Score trustworthy reference frames without resetting trajectories at gaps. Report coverage, exclusions, and failed trials; do not discard trials because their reconstruction error is high. Endpoint and heading metrics require valid reference at the relevant frames.
- Select fixed-distance metric intervals using development data and freeze them before final testing. Aggregate results with equal participant weights.
- Establish baseline performance on validation data first. Design and compare learned correction candidates next, then freeze the chosen method. Evaluate the baseline and chosen model on final test data together after development concludes.
- Save run settings, input identities, split manifest, calibration provenance, software versions, QC/metric tables, trajectory exports, and plots for reproducibility.

Status: the user confirmed implementation with "build". The offline CLI, baseline, regularized linear residual, and two causal TCN candidates have been implemented. Initial search budget was two TCN widths (16/32) with 12 epochs each and validation-based checkpoint selection. TCN32 was selected on validation, then the artifacts and protocol were frozen before final testing. Development in the evaluated output directory is now locked.

## Observed implementation results

- Eight runnable numerical, causality, timing, participant-isolation, and artifact-integrity checks passed.
- Training QC accepted 443 of 569 paired trials. Validation QC accepted 70 of 84 trials across four participants.
- Equal-participant mean validation position RMSE: physics baseline 0.5156 m; selected TCN32 0.4524 m.
- Final QC accepted only 32 of 84 trials, all from No.2 and No.9. No.11 and No.12 had no accepted trials because of synchronization/clock failures. The full planned test population is therefore not represented.
- On that accepted test subset, baseline RMSE was 0.5020 m and selected TCN32 RMSE was 0.6139 m. Validation improvement did not generalize; these results do not establish a learned-model improvement.
- Output reports disclose attempted counts, exclusions, participant coverage, empirical unit conversion, and known-initial-pose/external-clock-alignment assumptions.

## Observed dataset facts

- Sept. 24 and Sept. 25 each have 210 canonical C3D trials with matching IMU filenames: seven conditions, three repetitions, and ten subject identifiers per date.
- Subject filename identifiers are No.1-10 on Sept. 24 and No.11-20 on Sept. 25. The user confirms these identify 20 distinct people.
- Filename pairing does not establish synchronization or ground-truth quality.
- Configured IMU units are explicitly unverified; stored baseline scales and delay have no local derivation record.
- No file-based cross-date participant mapping is present. Earlier filenames use trial numbers, names, or pseudonyms; target filenames use No.1-20. The user supplied the target uniqueness and earlier-versus-target non-overlap confirmations above.
- Representative first-five-second acceleration medians are about 8157-8251 CSV integer units; this does not establish the conversion. Some sampled target beginnings vary substantially, so stationarity cannot be assumed.
- Sampled wheel gyro variance is dominated by gz; sampled center signals differ by setup. These identify candidate axes only, not universally verified mounting axes.

## Protocol amendment v2 results

Original evaluated results and source are preserved in `outputs/` and `experiments/v1_source/`. Training-derived marker bands recover the wider optical setup supported by training participant No.20; marker distance is not physical hub width. Stage-specific QC, one-to-one signed peak alignment, joint midpoint-speed calibration, physical features, group-balanced training and integrated-motion loss are implemented. The participant split is unchanged.

Twelve checks pass. Training accepts 477/569 recordings and validation 72/84 across four participants. Validation RMSE: baseline 0.4689 m, ridge 0.4810 m, TCN16 0.3849 m, TCN32 0.3747 m. TCN32 is selected and frozen.

The amended retrospective test accepts 69/84 recordings across all four participants (No.2:19, No.9:17, No.11:16, No.12:17). Baseline RMSE is 0.8562 m and TCN32 0.8028 m, a 6.2% reduction on the same accepted subset. Fifteen exclusions remain: 13 peak alignment, one non-monotonic clock and one clock-scale rejection. There are no reconstruction failures. Results are conditional on inclusion and cannot be presented as a new blind evaluation because the original test had already been inspected. Current artifacts are in `outputs_amended_v2/`, locked against further development.

## GRU and uncertainty-filter comparison v3

A separate comparison preserves the frozen v2 source and artifacts. A causal 32-unit GRU is trained for 12 epochs using the inherited training-only calibration/normalization, balanced windows and integrated-motion loss. Training-fitted log-error regression supplies diagonal measurement variance for speed/yaw random-walk Kalman filters; process-variance multipliers are selected on validation. This is not a full pose-and-bias EKF.

Validation RMSE: physics 0.4689 m, TCN 0.3747 m, GRU 0.3896 m, filtered TCN 0.6752 m, filtered GRU 0.6865 m. TCN remains selected. The frozen retrospective comparison uses the same 69 accepted recordings from four participants: physics 0.8562 m, TCN 0.8028 m, GRU 0.8085 m, filtered TCN 0.8433 m, filtered GRU 1.0265 m. None of these new candidates establishes improvement on TCN. All original checks and new GRU/filter checks pass, including batched inference equivalence and causality. Outputs and frozen artifacts are in `outputs_alternatives_v3/`.
