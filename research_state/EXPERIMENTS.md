# Experiment ledger — 2026-10-04

## Latest root integration

- v38correctedclockresidualrefit:473train(465v9+8explicitoldfallback),71val;fixedα.1/endpoint1/gain.5/tilt.3/blend.75; ownclock100.702→96.329mm, nativecommon100.593→96.172mm;all4valpeopleimprove but30trialsregress. v39independent213motionintegrations/masks/hashes exact. v39trainingfoldguardFAIL1.559583; No13periodicclockalias dominates. Rejectpromotionpendingclockarbitration. Source clock_refit_experiment_v38.py; output models/caches/tables sealed.
- v40damping: oldfoldcoeff evaluatednewrawclock, predeclare0/.1/.25/.5/.75; .75selected126.319mm training, guard1.02836vssameclock but1.58037vsoldclock. Nativeval96.561mm. Rejectoverallpromotion; doesnotrepairbadclock.
- v40/v41independent TRAINONLYclockbasinaudits:all473screened,5changes>.25s. No13T3old/newyaw.997856/.664752 andspeed.868/.291→old. SlopeHAR9old/new speed.966/.433→old. No15PS1old/new speed−.961/.999 andyaw.792/.976→supportednew. No15OS3strongnewyawandbrakingevent→supportednew. No19OS1moderateyaw/broadmonotonic speed→ambiguousoldfallback. No positionerrorsselectclock. Strongestpeak alone andfullIMU-vsfragmentedopticalfirstordinalmatchingfailed diagnostic; retain failures. outputs_clock_alias_v40/report.md andoutputs_clock_basin_v41/report.md agreeindependently.
- Rootquiet_yaw_bias_experiment_v41: strictall3IMUfullrecordquiet; predyawmedian clipped±.01rad/s, piecewiselinearofflinebias, gains0/.25/.5/1.207heldtrain12people,55eligible; .25mean132.866mm,worst1.124; .5=135.143/1.264;1=142.284/1.559vs132.076control. Zero selected before71val:100.702unchanged,24eligible. No velocityzero orC3Dupdates. Rejectasdefined; stationarityproxy/motionclassification/biasextrapolation uncertainty remains. outputs_quiet_yaw_v41.
- PDFresearchreport82pages created, method/atlas consistencyfixed afterindependentreview. LatestQA pending; do not deliver stale renders. Builderreport_research_window_v38.py.

## Resumed window audits

- IMU-only dynamic loader v36: all71validation, fresh native startup; trajectory difference<=5.879e-9m, RMSE100.702119424mm; reference-poison independence passes. Source dynamic_blend_inference_v34.py and audit_dynamic_loader_v36.py; output outputs_dynamic_loader_v36. Supports implementation reproduction, not full-stack generalization.
- Route metric v36: original/selected routeRMSE50.283/49.726mm; meantrialP9597.842/96.769, sampledHausdorff148.641/149.285, endpoint133.760/127.772, abs supportedlength108.714/104.732, max-runFrechet165.580/165.919mm. Unchangedinitialpose, no transforms/timefitting; masks disconnect both curves. 10mm spatial sampling exact point-to-segment; Hausdorff sampledquery maximum, Frechet25mm discrete withinruns. Failed broad-improvement hypothesis: synchronized/route averages improve but two tail/order metrics worsen. outputs_route_metrics_v36/report.md.
- Independent skeptic v36: hashes/splits/folds/metric reproduce.45improve26worsen; descriptive four-person bootstrap includeszero. Not robustly established universalgain. outputs_blend_audit_v36.
- Affine clock v36: native544records; 8s blocked signalcorrelation residual affine ±2000ppm vs offset ±100ms; training196identifiable,validation24; training-selected offset. No positionalmodelscore changed. outputs_affine_clock_v36/report.md. Wider residual signal-only offset counterfactual pending.
- Wheel phase v37 RUNNING:4Hz lowpass,51sample anglederivative,30contextfeatures; gyro-derived wheelvelocity/accelerometerphase medianmapping from fittraining only; plausible radius magnitude.15-.6m, normsquality; zero/.25/.5/.75 blends withthreefoldguard. No independent slip/SIclaim. Source wheel_phase_experiment_v37.py.

Common protocol: frozen participant partition; all473 accepted train and71 validation; fixed observed masks; no test access this window; inherited base/calibration. Conditional training folds do not establish full participant-independent generalization. All candidate outcomes retained.

| Experiment | Hypothesis/parameters | Selection and overall result | Conclusion |
|---|---|---|---|
| weak labels v33 | Existing point terms unchanged; processed endpoint confidence 0/.1/.25/.5; two processed endpoints w squared | Four-person training fold selects .5; validation102.585 ->103.212mm | Reject; PS improves but AR/CR/SL/10x5 regress |
| dynamic tilt v33 | Empirical center lowpass acceleration .3/.75Hz; 30 extra context features; original correction parameters | Three training folds; undamped .3 gives100.565mm but worst person1.0857 | Reject undamped; not verified physical attitude |
| dynamic blend v34 | Fixed .3Hz train-selected parent; motion blends0/.25/.5/.75 | Three folds select.75;132.240mm train,100.702mm validation,1.260899deg heading | Keep as candidate pending complete audit; No.10 slight regression |
| long intervals v34 | Add observed-only15/30s endpoint equations; weights0/.1/.3 | Four-person fold selects.3; validation102.257mm,heading1.376044deg | Small gain; yaw slight regression; no claimed combination gain |
| braking bridge v34 | Center-acceleration trained integration <=1s after IMU disagreement; blends0/.25/.5 | Training chooses0; validation .25=114.483,.5=136.825mm | Reject broad gate; ordinary-motion/tilt false positives |
| joint planar v35 | Full3channel endpoint Jacobian; lateral reg.3/1,gain.25/.5; forward/yawgain.5 | Four-person fold selects.3/.25; validation102.610mm,heading1.398deg | No useful gain; 46 improve25worsen;10x5+8.113mm |

Source scripts: weak_label_experiment_v33.py, dynamic_tilt_experiment_v33.py, dynamic_tilt_blend_v34.py, long_interval_experiment_v34.py, braking_bridge_experiment_v34.py, joint_planar_interval_v35.py. Corresponding output folders contain protocol/model/selection/trial/person/maneuver tables and prediction caches.

Visual diagnosis: No.18 PS2 mostly longitudinal braking deficit (~0.52m); No.10 PS2 mostly lateral offset after early yaw excursion; No.18 SL1 late cross-track/yaw drift; ST early yaw transient changes sign by setup/day; No.5 AR2/3 opposed displacement directions despite small reported heading error. Three worst trials contribute15.306mm to102.585 objective; perfect removal would still leave87.279mm. Keep failures in evaluation.

Research evidence: research_docs/trajectory_failure_research_v33.md (Wheel-INS2, wheelchair skid paper, TLIO, VQF, C3D and observability primary sources). It supports physical calibration and uncertainty-aware wheel/body fusion, not automatic transfer of pedestrian models or an RL accuracy guarantee.

## Synchronization specialist — v36 / v37, 2026-10-04 resumed window

**v36 hypothesis:** residual C3D/IMU affine skew remains after per-device-to-PC affine fitting and inherited v5 single-offset alignment. `affine_clock_audit_v36.py` audits all473 accepted train/71 validation native CSV/C3D metadata; no test. Nonoverlapping8s signed-yaw or wheel-speed windows search ±100ms in2ms steps on identical support; robust skew bounded ±2000ppm; offset/affine/guarded affine selected using alternating-block training correlation holdout before validation. This is reference-assisted evaluative synchronization, unavailable at IMU-only deployment. Training labels contain legacy identity groups;17 aggregation labels are not17 verified people.

Training196 recordings have enough cross-fit support. Equal-group correlation gains: offset .001027325, affine .000976439, guarded .001008942; **offset selected**. Validation24 identifiable recordings: .003053849/.003051762/.003052506. Short47 recordings lack two windows, so failure to identify skew is not evidence of zero clock error. Full-record descriptive slopes may be confounded by slip/mounting/filter differences. No position scores or trajectories changed in v36.

Native544 C3Ds all POINT/header100Hz;543 header-first-frame0, one90 (earlier cropped SlopeF trial). IMU median102.396068Hz, no accepted stream nonmonotonicity, missing_before, or interval>20ms. About90% PC arrival timestamps repeat within batches. Per-device affine-to-PC residual median4.783ms,max82.654ms; packet jitter must not be confused with uniform sensor sampling. C3D timing metadata lacks a verified shared IMU trigger/timebase. Source/report/tables: `outputs_affine_clock_v36/`.

**v37 hypothesis:** training-selected residual signal offset explains part of synchronized localization error while route geometry stays fixed. `signal_offset_counterfactual_v37.py` reassigns saved v21/blend prediction timestamps: prediction(t+delta) vs fixed observed C3D(t); same path/initial pose, no geometric alignment or reintegration. Delta is median v36 signal lag only if>=2 accepted windows;47 fallback unchanged. All71 retained,24 reassigned,28 directly observed samples removed by common overlap. All original scores reproduce exactly.

Matched originalv21102.585825→101.946985mm; matched blend100.707814→**99.506231mm**. **Not promoted as a model improvement**: production blend remains100.702119mm. Heading1.260963→1.201192deg. Blend counterfactual people No10 67.502,No14 97.357,No18 128.289,No5 104.877mm. Maneuvers10x5 137.790,AR87.943,CR55.129,OS95.005,PS188.816,SL118.053,ST58.404mm. No18long10x5 timing shifts70/45/45ms change293.0→251.2,225.4→198.0,243.0→216.0mm. No14Trial1 worsens76.9→98.5mm; other regressions retained in paired table. Both actual clock figures inspected; residual route inflation/yaw remains after correspondence changes.

Independent historical evidence: v9 observed-only sync No18long10x5 lag corrections +70.5/+46.5/+44.9ms closely reproduce v36 +70/+45/+45ms. This identifies an inherited-clock issue: current v21/blend still use v7 inherited v5 clocks. A new matched retrain on observed-only corrected label clocks is warranted, while v9's465/473train reacceptance requires explicit fallback/coverage handling. Signal-only offsets cannot be selected from position RMSE. Source/report/71 caches/participant and maneuver tables: `outputs_signal_offset_v37/`. No blind-test, calibrated timing accuracy, or new estimator claim.

### Corrected-clock residual refit v38

`clock_refit_experiment_v38.py`, `outputs_clock_refit_v38/`: preserve all473train/71validation acceptedIDs. v9correctedclocks465train+71validation;8trainv7fallback exactly CR1No7,CR3No4,OS1/2No7,PS1No4,AR1No19,AR3No15,OS1No17 (fullIDs in protocol/run). Fixedv21α.1/endpoint1/gain.5,tilt.3Hz,blend.75; no validationretuning. Recompute IMU-only inheritedridge andnative-startupfeatures, refittrainclip/normalization/caps/endpointweights. Base and calibration remain inherited, so conditional residual refit rather than fullpipelineindependent result.

Own-clockfull benchmark: oldv21102.585179/oldblend100.702119 reproducedexactly; newclockfrozenv21101.919404/blend99.629889; newclockrefitv2199.565301/blend**96.329130mm**,heading1.166827deg. Different preparations have different initialpose/masks; use below matched benchmark for causal comparison.

Native-common benchmark: ONE shared nativeobservedinitialpose, identicalC3Dtimestamps/masks/IMUcoverage, no resets. Oldv21102.491114→newclockfrozen101.787211→refit99.377490mm. Oldblend100.592598→frozen99.491278→refit**96.172432mm**,heading1.167598deg. Eachmotionstreaminterpolatedusingits ownref_t; native reference neverinterpolated. All71retained. Common caches, ownclockseparatemasks, fullcoverage, participant/maneuver tables,modelweights andmanifest preserved.

Common people oldblend→refit: No10 67.416→63.134;No14 96.050→94.116;No18 134.369→125.936;No5 104.535→101.504mm. 41trialsimprove/30worsen. Largestregressions No14long10x5Trial1+50.623mm,ST2+27.649,10x5Trial2+22.478. Largestgains No18long10x5Trial1−87.907,No14PS3−62.099,No14SL1−42.915mm. Own-clockrefit maneuver means10x5 137.988,AR92.690,CR60.895,OS85.307,PS167.103,SL103.611,ST60.652mm. AR/CR/ST worsen againstoriginalblend; allpersonimprovement does not mean everymaneuverimproves. Keep as promisingcandidate pending71plotvisualreview/independentaudit/fullconditionalparticipantguard; no automaticpromotion or millimeterclaim.

IMU-only loader `clock_refit_inference_v38.load_clock_refit()` accepts exactlysetup,t,raw,imu_valid plusnativeCSVpath, returnsmotion/startupstate, and rejectsreferencefields. Independent `audit_clock_loader_v39.py` / `outputs_clock_loader_v39/` verified all473/71maps, exact8fallbacks, trainlabelsupport/pointcounts, rawIMU/C3D/cache/modelhashes andunchangedparents. Freshnativefirst5s IMU-onlystates andall71refitblendmotions reproduced **exactly (maxmotionerror0)**. Loaderdoesnotestimateabsoluteinitialpose; offlinefuturecontextandinheritedcalibrationremain.

### Conditional folds v39 reject unguarded corrected-clock candidate

`clock_folds_experiment_v39.py` / `outputs_clock_folds_v39/`: threepredeclaredfolds,207heldtargettrainingtrials/12people. Oldclockcontrols reuse SEALEDv34same-fitting-ID foldcoefficients, neveralltraincoefficients. Correctedclockclips/caps/normalizers/coefficients excludeheldpeople. Nativecommonpose/masks. Base/calibrationstillinherited. Blend132.076460→126.514035mm butheading2.081173→2.135878deg. **Worstpersonratio1.559583(No13) violates5%guard;No8ratio1.058005 alsofails. Do notpromotev38's96.329mm asrobust.** No13long10x5Trial3 common182.203→1589.122mm fromv9aliasoffset−.700→+4.1517s. No15PS1 improves1834mm becauseold−4.925s aliascorrectedto−.7652s. Blindly limitingalllargejumps loseslegitimatecorrections.

Heldcommonmotion/reference/nativeclock caches saved in v39. `cache_clock_sensors_v40.py` / `outputs_clock_sensor_cache_v40/` adds207separate exactold/new raw/t/ref_t/valid andcommon-native rawinterpolation files with NOopticaltargets. Supportsfuturequiet-bias/smootherwithoutrefittingfoldmodels. Nativefirst5sstateprecedestheseoverlapcrops.

### Same-clock damping v40 and large-basin audit v41

`clock_damping_experiment_v40.py` / `outputs_clock_damped_v40/`: oldfoldcoefficients evaluatedon NEWclockraw, freshnativeinitialization, samecommonpose/masks; interpolatepredictedmotion tocommon-native time. Predeclared0/.1/.25/.5/.75 refitmotiondamping. Trainselects.75,mean126.319425mm,worst SAMEclockratio1.028356 passes. Independent OLDclockratio1.580367 stillfails; No13clockalias retained andexplicit. Nativecommonvalidation selected96.561154 vsnewclockfrozen99.491278 vsold100.592598mm. No validationretuning; no robustpromotion untilbadclockbasinsfixed.

`clock_basin_audit_v41.py` / `outputs_clock_basin_v41/`: sevenTRAINtrials withold/v9shift>.1s; compare exactlytwo offsets usingnativeobservedderivative/commonIMUsupport, no positionmetric ornewlagsearch. No13long10x5Trial3 on1669identicalframes: oldyawcorr.997856 vsnew.664752; oldspeed.858862 vsnew.295286. Oldbasin stronglysupported, corroboratingv36fourwindowsmedian−5ms. No15PS1 on421frames: oldyaw.791845/new.975049 andoldspeed−.963444/new.998664 supportnew4.1598srepair. EarlierSlopeHARTrial9 oldspeed.965659/new.436740 supportsoldbasin. No16SL2 channelpreferencesconflict(oldyaw.999514/new.980161; oldspeed.983796/new.993581). Thus observed-onlypeakalignment can rejectcorrectbasins andaccept periodic aliases withonly2matches. Nextclockprotocol shouldinclude originalbasin amongcandidates andevaluatebothyaw/speed onidenticalnativeobservedsupport; do notchooseclockfrompositionerror.


## Independent skeptic audit v36

Audit reproduced100.702119399mm exactly; parent/source/artifact hashes,473fitIDs, frozen split,71exact observed masks and three-fold exclusion/selection pass.45improve26worsen. Gain strongly concentrated inNo.14; leave-No.14-out0.584mm. Descriptive4person bootstrap gain95%[−0.104,4.380]mm includeszero.71actual new trajectory plots reviewed; No.18PS2 andNo.5AR2/3 remain unsolved. Keep candidate modest/conditional; no prospective significance or calibrated-attitude claim. Evidence: outputs_blend_audit_v36/report.md,audit.json,visual_review.csv.


## Calibration-only fold audit v37

473observedtraining calibration vsheld-excluded folds on207target-training records:222.645→229.879mm (+7.234mm),5.682→6.439degrees. Stableaxes/signs,<0.9%scaleshifts; No20+54.211mm. Inheritedv2used477IDs/differentlabelsemantics, so separate231.330mm comparator notexactreproduction. Wheel-yaw1297.990mm rejected; jointmidpoint-calibrated wheelterms notphysical rimvelocities. Radiusunusedexactzeroeffect. Calibration-only conditional audit; no fullmodelrefit orvalidation/testaccess, no correctionof100.7mm headline. Evidence outputs_calibration_fold_v37/report.md.


Individual wheelcalibrationv38: trainselectszero wheel-yaw; purewheel979.634mm vs229.879center; nonzero blends475.671/673.396/820.575mm failguard. Individualmidpointspeed selected228.675mmtrain but232.257vs232.204mmvalidation—reject. No productionchange. Evidence: outputs_physical_wheel_v38/report.md.


Wheelstartupbiasv39: strictnativeIMUquietgate supports only1/207heldtraining and1/71validation. Zero-wheel-yaw selected229.702mmtrain,232.113vs232.204mmvalidation(0.091mmgain); nonzeroyaw474.675/673.158mmfailguards. Mechanism largelyunsupported; do not claim pertrial wheelbias improvement. Evidence: outputs_wheel_bias_v39/report.md,gate_diagnostics.csv.


## Startupgateattritionv40

Savedv14/newv39eligibilitymatches1/207targettrain+1/71val. Samefrozengateslaterquiet83train+32val; median native sharedstartspread61ms/validfraction1.0. Only7train+3val first5recordshave100opticalquietderivativesamples. OnopticalquietframesaccSDmedian.0213/.0225g justabove.02;3gyro.00644/.00450rad/s wellbelow.1. Moststartupfeatureinitializationthusdatefallback. Laterquiet102records/13,837observedsamples86.57%meetfixedopticalquietcriterion; notabsoluteprooforpermissiontozero-bodyvelocity. No thresholds/modelchanged; potentiallaterbiasupdatehypothesis. Evidenceoutputs_wheel_gate_v40/report.md.

## Final v42-v44 checkpoint � 2026-10-04

Hypothesis: wrong repeated-cycle clock basins corrupt training supervision. Data:473train/71validation,462corrected+11fallback train; no test access. Fixed residual regularization.1, endpoint1, gain.5, tilt.3Hz, blend.75; no validation tuning. v42 own-clock100.702119->94.834759mm; native100.592598->94.661740mm. v43 matched-ID conditional training folds207records/12people132.075863->116.305014mm; No13ratio.937920/No15.418815; No8ratio1.058004869 exceeds frozen1.05. Decision: **not promoted**, guard unchanged. Alias correction supported by signed yaw/speed/distributed events, with independent v40/v41 corroboration.

v44 IMU-only loader reproduces71motionstreams exactly; hashes/IDs/label counts/fallbacks audited. Route audit:46.124049mm symmetricRMSE,89.031705P95,139.983334sampledHausdorff,155.161866max-runFrechet,122.307880last-supportedendpoint,113.305502absolute length (worse vs105.713574). All71plots reviewed; braking/No5initialization failures retained.83pagePDF rebuilt,71images and426caption values verified. Workspace credit failure ended agent investigations; no jobs remain known. See outputs_clock_arbitrated_v42, outputs_clock_arbitrated_folds_v43, outputs_clock_arbitrated_loader_v44, outputs_clock_routes_v44, outputs_research_report_v38/final_qa.json.

## Resumed v46-v48 work (active)
No8 independent TRAIN audit:20records77.156534->81.631989mm; frozen corrected-clock contributes+4.386704mm, refit only+.088751mm. Timing/preparation includes timestamp-conditioned features, not pure lag. PS2/PS3 dominate. v46damping weights0/.1/.25/.5/.75/1 all fail BOTH guard requirement; lowest old-clock worst ratio1.054644 at.5. Fail-closed before validation, sealed outputs_clock_arbitrated_damped_v46.

v47 metric diagnostic retainedv34: afterfirstsecond RMSE105.237mm, within10mm4.755% vs10.158%allframes; within100mm69.333% vs71.792%. Translating> .05m/s has74.574%within100mm, so nearquiet does not simply inflate every tolerance. Diagnostic opticalderivatives only, no gapbridges; unequal available strata not directly pooled. outputs_match_motion_v47.

Active: No8smallshift signal/event audit by agent; root TRAIN smallshift multichannel audit outsideNo8 outputs_clock_small_basin_v48/session33163; primarysensor timebase source investigation agent. Retainedbestunchanged, finaltestclosed.

## v46-v49 findings, superseding active notes above
No8PS2/3clockchanges are supported by signedyaw AND slightly improved speed; no evidence to revert. Optical support starts midmotion around2m/s. Boundary delta*(vend-vstart) predicts115.173/85.098mm vs actual added125.763/82.638mm longitudinal travel. Timing can compensate modelerror; do not minimize positionRMSEtochooseclock. Agent evidence outputs_no8_clock_signals_v46, outputs_no8_boundary_v46, outputs_no8_review_v46.

v48 TRAIN163smallclockupdates outsideNo8: five long10x5 show speedcorrelation regression>=.025 (No13T1/T2,No16T1/T2,No17T2); no automaticreversion, body/wheelspeed response confounds.

v49 207known-target TRAIN only, per-fold calibration/basephysics/feature normalization/clips/endpointcorrector fullyrefitted; earlier identity-unlinked data excluded. Frozen reference/QC/clockpreparation remains inherited. Physics219.002mm -> nonlinearendpoint214.977mm but No20worstratio1.832815, reject. No validation/test. Historical note: v50 was running here; v50 later completed and is summarized in the v50-v55 section below.

Historical v46 sensor note is SUPERSEDED by v53. `research_docs/sensor_timebase_v46.md` lacked firmware/receiver evidence; current primary-source conclusions are in `research_docs/firmware_receiver_audit_2026-10-05.md` and support raw +/-4g, +/-2000dps, sensor104Hz and ~102.4Hz recorded polling.

Historical test inspection is documented in archivedpreviousstate: test was NOT accessed in this window, but do NOT call existingtest a freshblindtest. A new independent evaluation is required. Retainedbest100.702119mm remains conditionaldevelopment.

## v50-v55 / firmware redo — 2026-10-05
- **v50 simple point folds finished** (`outputs_simple_point_folds_v50`): physics219.002mm; linear_endpoint214.171mm but worst participant1.769287; linear_point255.782mm/worst2.940934; products_point257.623mm/worst3.094429. Physics selected. TRAIN207 only; validation/test false.
- **v52 projected yaw** (`outputs_projected_yaw_v52`): dynamic low-pass acceleration direction projects bias-corrected center gyro; per-fold calibration/scalar mapping excludes held participant. TRAIN207: weight0 219.002mm/6.286deg; .25 198.010/5.036; .5 180.234/3.885; .75 161.881/2.700; 1.0 **147.747mm/1.837deg**, worst participant ratio **0.961159**. Selected1.0 before validation; no test.
- **v53 firmware/receiver audit** (`research_docs/firmware_receiver_audit_2026-10-05.md`, `outputs_firmware_audit_v53`): actual source shows default +/-4g,+/-2000dps; requested100Hz -> sensor104Hz; RTOS polling/recorded cadence ~102.4Hz; raw20-byte `<IIhhhhhh`; Windows CSV writes raw integers. Firmware Info gyro scale `2000/32768` is wrong versus0.070dps/LSB but does not enter research raw CSV pipeline. `pipeline.py` already reconstructs time from device timestamps with packet-tail PC anchors. Exact544 accepted records have zero sequence gaps; some broader Sep24 rejected raws do have gaps. No rescale/rerun of v34/v42 justified.
- **v54 fixed validation** (`outputs_projected_yaw_validation_v54`): one frozen TRAIN-selected v52 weight1 candidate, no validation retuning. 71 validation: refit_physics229.801mm/5.407deg -> projected_yaw **153.607mm/2.049deg**; participant ratios No10 .643522, No14 .646382, No18 .589790, No5 .843576. Test false. Strong mechanism evidence but not better than v34 headline.
- **v55 PS counterfactual** (`outputs_braking_counterfactual_v55`): diagnostic C3D substitutions only, no selection. Focus No.18 PS2 v42 predicted405.191mm, signed travel4.762895m. Observed-speed-only -> **60.344mm**, signed travel5.247908m; observed-yaw-only ->405.114mm. Thus ~0.485m forward-travel deficit dominates. Across PS trials mechanism is heterogeneous, so the already-rejected broad braking bridge should not be revived.
