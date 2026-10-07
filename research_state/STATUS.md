# Current research status — 2026-10-05, v55 checkpoint

## External blocker
All three active research agents reported workspace credits exhausted. Collection, final route audit, PDF generation and artifact checks completed afterward. No experiment is known to remain running. Primary-source firmware/timebase investigation did not finish; do not claim it did.

## Retained candidate and new experiment
- Retained conditional development candidate: v34 tilt motion blend .75, synchronized equal-participant RMSE **100.702119 mm**, heading 1.260899 degrees. Original v21: 102.585179 mm.
- Signal-arbitrated clock refit v42: own-clock **94.834759 mm**, common-native **94.661740 mm**. This is **not promoted**.
- v43 conditional participant guard: 132.075863 -> 116.305014 mm on 207 held-target training recordings / 12 people, but No.8 ratio **1.058004869** fails the frozen maximum 1.05 rule. No.13 ratio .937920 after alias correction; No.15 .418815. Do not loosen the guard.
- All 473 training recordings / 71 validation recordings retained. 462 corrected training clocks, 11 old-clock fallbacks. Fixed model parameters; no validation tuning. Final test untouched.
- Calibration/base are inherited; these are conditional correction folds, not independent full-pipeline participant evaluation.

## Strongest evidence
The No.13 long10x5 T3 corrected clock matched the wrong repeated cycle (+4.8517 s). Signed yaw, speed and distributed events independently favor the old basin. No.15 PS1 +4.1598 s is a supported repair. Arbitration also rejects earlier SlopeHAR9 shift and falls back for ambiguous No.19 OS1.

The v42 IMU-only loader reproduces all 71 motion streams exactly (maximum difference zero), with startup, IDs, parent hashes and training-label counts audited. Reference inputs do not enter prediction; C3D-assisted alignment is an offline evaluation operation.

## Geometry and visual findings
Latest v44 common-native v42: symmetric route RMSE 46.124049 mm; mean trial P95 89.031705; sampled Hausdorff 139.983334; max-run discrete Frechet 155.161866; last-supported endpoint 122.307880; absolute supported length error 113.305502 mm. Length worsens versus old-blend 105.713574 mm. These are equal-person means of trial metrics, with disconnected observed support, not complete-route guarantees.

All71 latest plots visually reviewed through 12 contact sheets. No.18 PS2 braking travel loss remains about half a meter. No.5 AR2/3 opposed-route initialization ambiguity remains unresolved without external evidence. Slalom and long-route errors are heterogeneous; timing alone does not explain them. No fitted spatial alignment, scale, reflection, endpoint snapping or C3D resets.

## Delivered artifact
83-page PDF: output/pdf/trajectory_research_accuracy_audit.pdf (12 methodology pages + all71 trajectories). SHA256 d3840b49ccf2f2adb4b53ee1411951fd1d39e636e9b22d98229df0a21492db62.
Final QA: outputs_research_report_v38/final_qa.json. All71 embedded images equal latest source pixels; all426 caption values match sealed v44 CSV. Latest PDF pages10-13 visually checked; prior draft methodology independently reviewed. Earlier title overlaps and stale descriptions repaired. Experimental guard failure appears on every atlas page.

## Limits
Primary-source v53 supersedes the old +/-2g assumption: September research CSVs are supported as raw int16 at approximately +/-4g and +/-2000deg/s; requested100Hz configures sensor104Hz while recorded poll cadence is ~102.4Hz. The historical firmware Info gyro scale is wrong, but raw research CSVs are unaffected because the trajectory pipeline fits raw counts and uses device timestamps. Exact flashed patch version, full mounting matrices and absolute MoCap uncertainty remain unverified. Two axle markers do not establish full pitch. ST optical Z is reference-only; no reliable predicted3D Z. No achieved synchronized 50/20/10/1mm claim.

See NEXT_SESSION.md for exact resume command. Earlier state snapshots preserved under research_state/history/2026-10-04_before_final_v44.

## Resumed v46-v48 work (active)
No8 independent TRAIN audit:20records77.156534->81.631989mm; frozen corrected-clock contributes+4.386704mm, refit only+.088751mm. Timing/preparation includes timestamp-conditioned features, not pure lag. PS2/PS3 dominate. v46damping weights0/.1/.25/.5/.75/1 all fail BOTH guard requirement; lowest old-clock worst ratio1.054644 at.5. Fail-closed before validation, sealed outputs_clock_arbitrated_damped_v46.

v47 metric diagnostic retainedv34: afterfirstsecond RMSE105.237mm, within10mm4.755% vs10.158%allframes; within100mm69.333% vs71.792%. Translating> .05m/s has74.574%within100mm, so nearquiet does not simply inflate every tolerance. Diagnostic opticalderivatives only, no gapbridges; unequal available strata not directly pooled. outputs_match_motion_v47.

Active: No8smallshift signal/event audit by agent; root TRAIN smallshift multichannel audit outsideNo8 outputs_clock_small_basin_v48/session33163; primarysensor timebase source investigation agent. Retainedbestunchanged, finaltestclosed.

## v46-v49 findings, superseding active notes above
No8PS2/3clockchanges are supported by signedyaw AND slightly improved speed; no evidence to revert. Optical support starts midmotion around2m/s. Boundary delta*(vend-vstart) predicts115.173/85.098mm vs actual added125.763/82.638mm longitudinal travel. Timing can compensate modelerror; do not minimize positionRMSEtochooseclock. Agent evidence outputs_no8_clock_signals_v46, outputs_no8_boundary_v46, outputs_no8_review_v46.

v48 TRAIN163smallclockupdates outsideNo8: five long10x5 show speedcorrelation regression>=.025 (No13T1/T2,No16T1/T2,No17T2); no automaticreversion, body/wheelspeed response confounds.

v49 207known-target TRAIN only, per-fold calibration/basephysics/feature normalization/clips/endpointcorrector fullyrefitted; earlier identity-unlinked data excluded. Frozen reference/QC/clockpreparation remains inherited. Physics219.002mm -> nonlinearendpoint214.977mm but No20worstratio1.832815, reject. No validation/test. Historical note: v50 was running here; v50 later completed and is summarized in the v53-v55 update below.

Historical v46 sensor note is SUPERSEDED by v53. `research_docs/sensor_timebase_v46.md` lacked firmware/receiver evidence; current primary-source conclusions are in `research_docs/firmware_receiver_audit_2026-10-05.md` and support raw +/-4g, +/-2000dps, sensor104Hz and ~102.4Hz recorded polling.

Historical test inspection is documented in archivedpreviousstate: test was NOT accessed in this window, but do NOT call existingtest a freshblindtest. A new independent evaluation is required. Retainedbest100.702119mm remains conditionaldevelopment.

## 2026-10-05 v53-v55 update
- v53 mandatory firmware/receiver audit complete: `research_docs/firmware_receiver_audit_2026-10-05.md`. Acquisition core stable across inspected v1.8.1-v1.8.4-era commits. Supported settings: +/-4g, +/-2000dps, sensor ODR104Hz, recorded polling ~102.4Hz, raw20-byte `<IIhhhhhh` samples. CSV uses raw counts; firmware Info gyro scale bug does not invalidate v34/v42. Accepted544 have zero sequence gaps; rejected/unselected Sep24 raw recordings include gaps.
- v50 completed: physics219.002mm selected; linear endpoint214.171mm has worst participant ratio1.769287 and is rejected; point models are worse. No validation/test.
- v52 TRAIN-only projected-gravity center yaw: 219.002->147.747mm, heading6.286->1.837deg, worst participant ratio0.961159, selected weight1.0. Conditional full-refit physics only.
- v54 fixed no-retune validation of that single TRAIN-selected v52 candidate: 229.801->153.607mm, heading5.407->2.049deg, all four participants improve, worst ratio0.843576. Test untouched. Still worse than retained v34, so no promotion.
- v55 diagnostic: No.18 PS2 v42 RMSE405.191mm; GT-speed-only counterfactual60.344mm, GT-yaw-only405.114mm. Signed travel4.762895m predicted versus5.247908m with observed speed: ~0.485m forward-travel deficit dominates. Diagnostic C3D substitution only; no model promotion.
- Retained headline remains v34 100.702119mm conditional development; v42 remains not promoted because No.8 ratio1.058005>1.05.

## PDF layout revision - 2026-10-05
Rebuilt83-page PDF withall71two-panel trajectory/yawplots,IMUred/C3Dblack. Wrappedrelativeyawandgap/wrapbreaks; model/numericmetricsunchangedv42experimentalfailedguard. PreviousPDFpreservedunderoutput/pdf/history. Builderreport_two_panel_v54.py; QAoutputs_pdf_two_panel_v54/final_qa.json.
