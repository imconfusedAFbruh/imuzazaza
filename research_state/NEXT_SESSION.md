# Resume without restarting — current v55 checkpoint (2026-10-05)

Read STATUS.md, TODO.md, BEST_RESULTS.md, EXPERIMENTS.md and FAILED_IDEAS.md first. Older chronological state is archived under history/2026-10-04_before_final_v44.

## Current best
Retained v34:100.702119mm. New v42:94.834759mm own-clock /94.661740mm common-native, **not promoted** because No.8 worsens5.80% above frozen5%guard. Conditional training mean improves132.075863->116.305014mm. Full calibration/base folds remain outstanding. Test untouched.

## Exact next command
```powershell
Get-Content research_state/STATUS.md, research_state/TODO.md, outputs_firmware_audit_v53/run.json, outputs_projected_yaw_v52/run.json, outputs_projected_yaw_validation_v54/run.json, outputs_braking_counterfactual_v55/run.json
```
Then read `research_docs/firmware_receiver_audit_2026-10-05.md` and start the next **TRAIN-only** forward-travel/braking residual experiment from v55. Do not rerun sealed scripts into existing outputs. Use a new versioned output directory. Do not tune thresholds/clocks on validation and do not access the historical test split.

## Strongest findings
No.13 longT3 +4.8517s shift is a repeated-cycle alias; old signed yaw/speed and distributed windows win. No.15 PS1 +4.1598s repair is valid. Three clock-arbitration fallbacks plus8QC fallback IDs keep all473 training records. Multichannel arbitration fixes No.13 regression but No.8 still fails. v42 loader has exact motion reproduction and no C3D prediction inputs.

All71 latest images reviewed. Latest route mean46.124mm does not erase roughly.5m No.18PS2 braking deficit, No.5AR2/3 physical-front ambiguity, or worsened supported length113.306mm. No fitted alignment.83-page PDF contains methods and all71 trajectories; finalQA checks71 image identities and426 captions.

## Next priorities after v53-v55
1. Build a continuous **TRAIN-only forward-travel/braking residual** for the No.18-type mechanism; v55 already isolates speed/travel as dominant. Do not repeat the rejected broad braking bridge.
2. Fit/select only inside participant-held TRAIN folds with frozen worst-person ratio <=1.05; validation evaluates only a preselected candidate.
3. Add ODR-vs-poll sample-age uncertainty (~one 104Hz sensor period) and packet/device-clock uncertainty to interval fusion / SE(2) smoothing; no C3D resets.
4. Revisit No.8 only through model-error/uncertainty mechanisms; its corrected clocks remain signal-supported and must not be reverted by position RMSE.
5. Validate optical marker geometry, physical-front convention and full mounting/pitch evidence; resolve No.5 AR2/AR3 without oracle flips.
6. Define a new independently frozen acquisition with exact firmware/version/range metadata, register readback, preserved `.waj` START/STOP/SYNC evidence and a hardware-shared MoCap timing event.
7. Preserve all failed ideas and keep the historical test non-blind; final claims require new independent data.

## Unfinished / blocker
Primary-source firmware/receiver/timebase audit is no longer a blocker; v53 completed it. Remaining blockers are exact flashed-binary provenance, full mounting/pitch geometry, independent reference uncertainty, and a new prospectively frozen evaluation. Full whole-pipeline participant nesting remains incomplete despite the v49/v50 simple-estimator folds. Retained best remains conditional development.

## Experiments not to repeat
Naive v9 clock promotion; same-clock-only damping guard used as overall guard; broad braking bridges; weak processed labels at equal weight; wheel-phase features as already tested; direct wheel-yaw blends; start5s quiet assumption; simple predictor-yaw median bias subtraction; validation-selected thresholds; metadata-only wheel-radius changes; oracle180degree flips; C3D reset/alignment.

## Best current hypothesis
Some training labels contain clock aliases; signal arbitration helps but remaining error combines braking/travel deficits, yaw and lateral accumulation, mounting/pitch coupling and reference-front ambiguity. A simpler calibrated estimator plus learned interval residual and uncertainty fusion remains promising, but must pass full participant evaluation. A lower mean alone is insufficient.

## Resumed v46-v48 work (active)
No8 independent TRAIN audit:20records77.156534->81.631989mm; frozen corrected-clock contributes+4.386704mm, refit only+.088751mm. Timing/preparation includes timestamp-conditioned features, not pure lag. PS2/PS3 dominate. v46damping weights0/.1/.25/.5/.75/1 all fail BOTH guard requirement; lowest old-clock worst ratio1.054644 at.5. Fail-closed before validation, sealed outputs_clock_arbitrated_damped_v46.

v47 metric diagnostic retainedv34: afterfirstsecond RMSE105.237mm, within10mm4.755% vs10.158%allframes; within100mm69.333% vs71.792%. Translating> .05m/s has74.574%within100mm, so nearquiet does not simply inflate every tolerance. Diagnostic opticalderivatives only, no gapbridges; unequal available strata not directly pooled. outputs_match_motion_v47.

Active: No8smallshift signal/event audit by agent; root TRAIN smallshift multichannel audit outsideNo8 outputs_clock_small_basin_v48/session33163; primarysensor timebase source investigation agent. Retainedbestunchanged, finaltestclosed.

## v46-v49 findings, superseding active notes above
No8PS2/3clockchanges are supported by signedyaw AND slightly improved speed; no evidence to revert. Optical support starts midmotion around2m/s. Boundary delta*(vend-vstart) predicts115.173/85.098mm vs actual added125.763/82.638mm longitudinal travel. Timing can compensate modelerror; do not minimize positionRMSEtochooseclock. Agent evidence outputs_no8_clock_signals_v46, outputs_no8_boundary_v46, outputs_no8_review_v46.

v48 TRAIN163smallclockupdates outsideNo8: five long10x5 show speedcorrelation regression>=.025 (No13T1/T2,No16T1/T2,No17T2); no automaticreversion, body/wheelspeed response confounds.

v49 207known-target TRAIN only, per-fold calibration/basephysics/feature normalization/clips/endpointcorrector fullyrefitted; earlier identity-unlinked data excluded. Frozen reference/QC/clockpreparation remains inherited. Physics219.002mm -> nonlinearendpoint214.977mm but No20worstratio1.832815, reject. No validation/test. Historical note: v50 was running here; v50 later completed and is summarized in the v53-v55 checkpoint below.

Historical v46 sensor note (SUPERSEDED by v53): `research_docs/sensor_timebase_v46.md` lacked firmware/receiver evidence. Current primary-source conclusions are in `research_docs/firmware_receiver_audit_2026-10-05.md` and support raw +/-4g, +/-2000dps, sensor104Hz and ~102.4Hz recorded polling.

Historical test inspection is documented in archivedpreviousstate: test was NOT accessed in this window, but do NOT call existingtest a freshblindtest. A new independent evaluation is required. Retainedbest100.702119mm remains conditionaldevelopment.

## 2026-10-05 v53-v55 superseding checkpoint
Mandatory primary-source firmware/receiver audit is complete in `C:\Users\poon1\Desktop\kight_recover`. Source releases v1.8.1-v1.8.4 share the same IMU acquisition core. Supported acquisition is raw int16, +/-4 g, +/-2000 dps; requested100Hz configures sensor104Hz while RTOS polling/recorded cadence is ~102.4Hz. Historical firmware Info gyro scale 2000/32768 is wrong versus 0.070dps/LSB, but the research CSV is raw counts and the trajectory pipeline never applies that faulty Info scale. `pipeline.py:imu_streams` already uses device timestamps and packet-tail PC anchors before a100Hz model grid. Therefore do NOT rescale existing v34/v42 inputs and do NOT replace device time with row/100 or seq/104. Evidence: `research_docs/firmware_receiver_audit_2026-10-05.md`, `outputs_firmware_audit_v53/`.

Exact544accepted records have zero `missing_before`, direct sequence gaps, duplicates or out-of-order samples. Broader Sep24 raw folders contain dropped-sample records, but those are outside the frozen accepted set. Sensor104Hz versus poll102.4Hz leaves up-to-one-sensor-period sample-age uncertainty (~9.6ms) that future fusion should model.

v50 is FINISHED, not running: point/endpoint alternatives fail robustness and physics remains selected. Existing TRAIN-only v52 gravity-projected center yaw selects weight1.0, 219.002->147.747mm with worst TRAIN participant ratio0.961159. Frozen no-retune v54 validation confirms 229.801->153.607mm, worst validation ratio0.843576, but it remains worse than retained v34 and is not promoted.

v55 diagnostic isolates No.18 PS2: sealed v42 predicted RMSE405.191mm with signed travel4.762895m. Replacing ONLY forward speed by observed label-valid speed reduces RMSE to60.344mm and travel becomes5.247908m; replacing ONLY yaw leaves RMSE405.114mm. The ~0.485m travel deficit is therefore overwhelmingly forward-speed/travel error, not yaw. This is diagnostic/oracle evidence only, not a deployable correction.

### Exact next priorities
1. Build a TRAIN-only continuous braking/travel residual or interval-speed uncertainty model for the No.18-type mechanism; avoid repeating the rejected broad braking bridge/gates.
2. Keep participant-fold selection and frozen worst-person ratio<=1.05; no validation threshold search.
3. Add ODR-vs-poll sample-age uncertainty to wheel/body interval fusion / SE(2) smoothing without C3D resets.
4. Resolve No.5 AR2/AR3 physical-front convention from independent geometry evidence.
5. Define a new independently frozen acquisition with firmware/version/range metadata, register readback, preserved START/STOP/SYNC journal and hardware-shared MoCap timing event.
6. Keep existing historical test non-blind; acquire a new independent final evaluation.
