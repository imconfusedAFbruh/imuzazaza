# Temporal residual correction for wheelchair IMU trajectory reconstruction: an exploratory matched evaluation

**Manuscript status:** working draft for a future Q1-targeted submission. This draft reports only completed evidence. It is not submission-ready: the validation cohort was previously exposed, only four participants contribute validation results, and the training lineage of the frozen parent model includes 266 historical records that still require record-level attribution.

## Abstract

### Background

Wheelchair-mounted inertial measurement units (IMUs) can support mobility measurement outside motion-capture laboratories, but small errors in estimated speed and yaw accumulate during trajectory integration. Existing wheelchair IMU studies commonly validate kinematics or short sequences; longer-horizon trajectory error remains sensitive to sensor calibration, synchronization, wheel interaction, and reference quality.

### Objective

To evaluate whether a bounded temporal residual model can improve a retained wheelchair motion-estimation baseline by correcting forward speed and yaw while preserving the baseline's lateral motion and integration support.

### Methods

A fixed 16-state leaky-tanh recurrent reservoir was applied to 15 existing gravity-rotation features from a three-IMU wheelchair pipeline. A regularized readout predicted bounded forward-speed and yaw corrections around the frozen v34 baseline. Readout fitting used exact native-timestep trajectory integration and a joint position-heading objective. Candidate regularization strengths were evaluated using participant-held folds on 207 identified training recordings from 12 people. The selected penalty-10 model was frozen before a matched evaluation on 71 validation recordings from four participants. The primary outcome was equal-person XY absolute trajectory error root mean square (ATE RMSE), compared on identical supported frames with the frozen v34 model.

### Results

On participant-held training folds, the selected model reduced equal-person ATE RMSE from 132.240 to 129.740 mm (1.89%). On the previously exposed validation cohort, v121 achieved 99.304 mm compared with 100.702 mm for v34, a 1.398 mm (1.39%) reduction. The predeclared participant, maneuver, position-P95, last-supported-endpoint, heading, and support guards passed. Three of four validation participants improved; one worsened. The validation sample represents four independent people, not 105,821 independent observations.

### Conclusions

The results support feasibility of bounded temporal residual correction for offline wheelchair trajectory reconstruction under the studied pipeline. They do not establish prospective generalization, deployment readiness, or superiority over the wider literature. The exposed validation cohort, small number of validation participants, inherited parent-model data lineage, offline temporal context, optical-dependent crop and initial-pose contract, and unresolved acquisition timing and geometry require a new prospectively frozen study before a generalizable Q1-journal claim.

**Keywords:** wheelchair; inertial measurement unit; trajectory reconstruction; dead reckoning; recurrent reservoir; motion capture; validation

## 1. Introduction

Manual wheelchair mobility is difficult to characterize continuously with laboratory motion-capture systems because those systems require calibrated equipment and a bounded capture volume. Wearable IMUs provide a practical way to record motion in sport and everyday settings, but integrating estimated speed and orientation into position accumulates error. Wheelchair-specific studies have examined sensor configurations against optical motion capture, frame rotation from wheel-mounted sensors, and inertial performance metrics; these studies establish that sensor arrangement, reference alignment, and repeatability matter [1–3]. More recent wheelchair-specific work also uses paired IMU and motion-capture recordings for related tasks such as user-pose estimation [4].

This study examines a constrained correction to an existing wheelchair trajectory pipeline. Rather than replace the physical and calibrated baseline, the model learns a low-dimensional temporal residual for forward speed and yaw. The design hypothesis is that a compact recurrent state may capture motion-dependent accumulated error that a fixed baseline does not represent, while bounded corrections and existing acceptance guards limit regressions.

The present evidence is exploratory. The frozen validation comparison showed a small improvement on a previously exposed cohort of four people. The aim of this report is therefore to document the method and matched result accurately, and to identify what a future independent study must establish. We do not claim a new recurrent architecture, state-of-the-art performance, real-time operation, or generalization to unseen users.

## 2. Methods

### 2.1 Study design and data partition

Model development used 207 identified training recordings from 12 participants, including all 15 recordings in the No.20 subgroup, with the original participant-fold assignments. The residual readout and its normalization were fitted within participant-held folds, excluding each held participant from the newly fitted readout and normalization. However, the frozen v34 parent contains dependence on 266 additional historical training records whose participant-level lineage is not yet fully resolved. The fold design therefore does not establish complete end-to-end participant independence for every component.

The final completed comparison evaluated v121 and v34 on the same 71 validation recordings from four participants, using 105,821 scored frames. These validation records had prior development exposure and are not a blind final test set. The historical test set was not used in this comparison and is not described as an untouched blind test.

### 2.2 Baseline and temporal residual model

The retained v34 baseline combines its frozen physical-product and dynamic-tilt motion estimates. It supplies forward, lateral, and yaw motion. The candidate adds a fixed 16-state leaky tanh reservoir driven by 15 existing gravity-rotation features from the wheelchair IMU pipeline. The recurrent weights are fixed and seeded; the learned readout maps the recurrent state plus intercept to forward-speed and yaw residuals. The readout is fit separately by acquisition setup. Corrections are clipped to ±0.05 m/s for forward speed and ±0.02 rad/s for yaw. Lateral motion remains inherited from v34.

Features are normalized using fitting-participant statistics, with a standard-deviation floor of 10^-5 and clipping to [-5, 5]. Reservoir state resets at invalid IMU frames. No participant identity, maneuver label, or optical value is an input to the prediction function. Optical labels are used for model fitting and evaluation, and the evaluation uses the original optical initial pose as the starting pose for trajectory integration.

### 2.3 Fitting objective and model selection

The readout is optimized through exact trajectory integration at every native timestep. The preregistered objective combines equal-person/equal-trial mean squared XY trajectory error, scaled by 0.1 m, and wrapped heading error, scaled by 0.1 rad with relative weight 0.1, plus an L2 penalty on the readout weights. Eight analytic Gauss–Newton updates are used, with a line search over steps 1, 0.5, 0.25, and 0 on fitting data only. Three penalty values (0.1, 1, and 10) were evaluated.

Selection required lower aggregate ATE than the frozen training baseline, no more than 5% regression for any participant or maneuver, and no more than 5% regression in position P95, last-supported endpoint error, or heading error, while retaining all 207 recordings and exact support. Penalty 10 was selected. Penalty 1 produced lower mean ATE but failed participant-level guards and was rejected. The selected readout was subsequently fit on all 207 identified training recordings and frozen as the v121 bundle.

### 2.4 Validation protocol

Before candidate prediction, the evaluation reproduced both public controls on all 71 validation recordings and checked their saved reference, time grid, clock/crop, support, motion, position, heading, and metrics against the frozen prior comparison within its original tolerances. It then predicted v121 once and integrated from the same original initial pose. Both models used identical reference support and scoring rules. No fitting or retuning occurred on validation data during this comparison.

The primary outcome was equal-person XY ATE RMSE in millimeters: per-recording root mean square Euclidean position error over matched supported frames, averaged within participant and then equally across participants. Secondary outcomes included position P95, last-supported endpoint error, heading RMSE, route RMSE and P95, and relative trajectory error (RTE) at 1, 5, and 10 seconds. RTE availability differs by interval and is reported with denominators. The “last-supported endpoint” is not a genuine acquisition endpoint.

### 2.5 Statistical interpretation

The validation cohort contains four independent participants. Participant and maneuver scores are descriptive; recordings and frames are not treated as independent participants. No independent significance or prospective generalization claim is made. All participant-level changes and guard decisions are reported to show whether aggregate improvement was uniform.

## 3. Results

### 3.1 Training-fold model selection

The frozen v34 baseline achieved 132.240 mm equal-person ATE RMSE on the matched training-fold evaluation. Penalty 10 achieved 129.740 mm, a 2.500 mm (1.89%) reduction, and passed the original guards. Penalty 1 achieved 127.491 mm but failed participant-level guards; it was not selected. Penalty 0.1 achieved 131.913 mm and also failed participant guards. The selected penalty-10 model’s worst participant regression was 3.356%; its worst maneuver regression was 0.264% against the relevant matched control.

### 3.2 Matched validation comparison

| Metric | v34 | v121 | Relative change |
|---|---:|---:|---:|
| Equal-person XY ATE RMSE (mm) | 100.702 | 99.304 | -1.389% |
| Position P95 (mm) | 159.335 | 156.126 | -2.015% |
| Last-supported endpoint error (mm) | 127.772 | 124.259 | -2.750% |
| Heading RMSE (degrees) | 1.2609 | 1.2038 | -4.531% |
| Route RMSE (mm) | 49.726 | 48.716 | -2.032% |
| Route P95 (mm) | 96.769 | 93.790 | -3.079% |
| RTE 1 s (mm) | 45.514 | 43.920 | -3.503% |
| RTE 5 s (mm) | 99.371 | 98.437 | -0.940% |
| RTE 10 s (mm) | 75.608 | 71.561 | -5.353% |

The RTE denominators were 71/71 recordings for 1 s, 39/71 for 5 s, and 4/71 for 10 s; the 10-second score covered only two participants. Coverage was 87.365% for both models under the fixed reference/support contract.

Three participants improved in ATE: No.10 (67.571 to 67.108 mm), No.14 (96.406 to 95.409 mm), and No.18 (134.342 to 129.754 mm). No.5 worsened from 104.491 to 104.944 mm (+0.434%). By maneuver, v121 improved 10x5, AR, CR, OS, and ST; PS and SL worsened slightly. Every predeclared guard against v34 passed.

### 3.3 Subsequent exposed validation comparison

After v121 was frozen, v125 was later evaluated on the same exposed validation cohort. V125 scored 99.700 mm versus v121's 99.304 mm and failed the mean and OS-maneuver guards against v121; all four participants worsened. This later comparison does not change the v121 result, but it confirms that the reported cohort has continued to support development decisions and must not be presented as a fresh blind test. V125’s separate 127.532 mm training result is not directly comparable with validation results.

## 4. Discussion

In this matched evaluation, a bounded temporal residual reduced ATE RMSE on training folds and on the exposed validation cohort while preserving the predeclared guard set. The model retains an established motion baseline and makes only forward-speed and yaw corrections. The result is therefore best interpreted as feasibility evidence for constrained temporal correction, not as proof of a broadly superior estimator.

The main result is modest and not uniform. The 1.389% ATE reduction is descriptive across four validation participants; one participant and two maneuvers worsened. Lower route/RTE values do not erase these limitations, particularly because 10-second RTE is available for only four recordings from two participants. The guard pass is useful evidence against severe regressions under the frozen evaluation contract, but it does not establish repeatability or clinically meaningful benefit.

The design is related to published wheelchair IMU research but answers a different question. Prior studies have measured velocity and rotation against optical reference or evaluated IMU-based propulsion metrics [1–3]. Other wheelchair-specific work demonstrates paired IMU/motion-capture data for body pose [4]. Those results are not direct ATE baselines because the sensors, estimands, timing, routes, support, and integration horizons differ. A future comparison must implement conventional wheelchair odometry or an EKF under the same inputs and reference protocol instead of comparing headline scores across studies.

The reservoir is a fixed random recurrent state with a learned regularized readout. The contribution should be framed as the full bounded, path-integrated residual estimation method and its evaluation, not as a novel recurrent architecture. Ablations against a linear readout, a non-recurrent temporal model, and the baseline alone are needed to establish which part contributes. The exposed validation history also means any new model selection must occur exclusively on a new development partition, followed by a prospectively locked final cohort.

## 5. Limitations and next study

First, the four-person validation cohort is small and has prior development exposure. Second, the frozen v34 parent has 266 historical training-record dependencies whose exact participant identities require resolution. Third, the end-to-end evaluation retains offline future-context dependencies, optical-dependent cropping, and an optical initial pose. It is not a complete real-time, IMU-only absolute-positioning evaluation. Fourth, independent time synchronization, firmware/runtime identity, physical geometry, and reference uncertainty remain insufficiently established for a prospective accuracy claim. Fifth, no genuinely observed acquisition endpoint is available; the last-supported endpoint is a distinct metric. Finally, the training-fold improvement is conditional on the selected protocol, and the participant sample is not a substitute for a power-justified independent cohort.

The next study should identify the complete lineage of all parent and preprocessing components; recruit a new cohort with the sample size selected from participant-level precision/power analysis; predefine the model, primary metric, support, synchronization, initial-pose contract, statistical model, and guard thresholds; record firmware, sensor mounting geometry, and a shared timing event; collect synchronized optical reference over repeated and meaningful routes; and compare v34, conventional odometry/EKF, and v121 with baseline and feature ablations. Participant-level confidence intervals, test–retest reliability, failure coverage, and reference uncertainty should be reported. Analysis code and permissible de-identified data should be released with frozen model hashes. A result that does not reproduce should be reported as such rather than used to retune on the final cohort.

## 6. Conclusion

A bounded 16-state temporal residual model improved matched equal-person XY ATE RMSE from 100.702 to 99.304 mm on a previously exposed four-participant validation cohort and passed the predeclared guard set. This is promising feasibility evidence for wheelchair IMU trajectory reconstruction. It does not yet establish unseen-user generalization or deployment readiness. A Q1-targeted paper should be submitted only after a new independent evaluation and complete parent-model lineage audit support the claim.

## Declarations to complete before submission

- **Ethics approval and consent:** [protocol, approving body, consent procedure, or documented exemption]
- **Participant characteristics:** [age, sex/gender where collected, wheelchair experience, inclusion/exclusion criteria]
- **Data acquisition:** [dates, sites, wheelchair make/model, IMU make/model, placements, sampling rates, calibration, synchronized reference specifications]
- **Author contributions:** [complete]
- **Funding and conflicts of interest:** [complete]
- **Data/code availability:** [licensing/consent review and persistent repository]
- **Protocol registration:** [identifier or state that none was registered]

## References

1. van Dijk MP, van der Slikke RMA, Rupf R, et al. Obtaining wheelchair kinematics with one sensor only? The trade-off between number of inertial sensors and accuracy for measuring wheelchair mobility performance in sports. *Journal of Biomechanics*. 2022;130:110879. https://doi.org/10.1016/j.jbiomech.2021.110879
2. Uchida K, Saito T, Kondo D. State estimation of wheel chair motion by nonlinear Kalman filter. *Proceedings of the Symposium on Sports and Human Dynamics*. 2022. https://doi.org/10.1299/jsmeshd.2022.C-4-2
3. Ouellet M, et al. Validity and Reliability of Inertial Motion Unit-Based Performance Metrics During Wheelchair Racing Propulsion. *Sensors*. 2025;25(6):1680. https://doi.org/10.3390/s25061680
4. Li Y, Mollyn V, Yuan K, Carrington P. WheelPoser: Sparse-IMU Based Body Pose Estimation for Wheelchair Users. *Proceedings of the ACM SIGACCESS Conference on Computers and Accessibility (ASSETS)*. 2024. https://doi.org/10.1145/3663548.3675638

## Source records for this draft

- Local method preregistration: `research_docs/reservoir_path_v121.md`
- Local training results: `research_docs/reservoir_path_results_v121.md`
- Local matched validation and metrics: `research_docs/frozen_validation_results_v123.md`
- Later exposed validation comparison: `research_docs/frozen_validation_results_v126.md`
- Independent review and limitations: `research_state/v121_review.json`, `research_state/v126_independent_review.json`, `research_docs/model_review_v121_2026-10-15.md`
- Related literature and Q1 target assessment: `research_docs/publishability_literature_review_2026-10-15.md`
