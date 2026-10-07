# Failed ideas — preserve evidence

- Newclockv38 mean96.329mm cannotbepromoted: trainingworstperson+55.96%;No13periodic4.8517s clockalias independentlysupportedold. Same-newclockdampingguardpassisnotanoveralloldclockguardpass.
- Strongestmatchingeventalonecanpickawrongperiodiccycle; first/last eventordinal acrossfullIMUandfragmentedoptical peaks isundefined unless correspondingacquisitionboundariesarevisible. Twochannels onfixedsupport plusdistributedwindowsneeded.
- Purephysicalwheelyaw remains979.634mm afterindividualfits; nonzero yawblends fail. Jointmidpointwheelcoefficients aren't physicalindividualrimvelocities.
- Pertrialstartupwheelbiasmechanism unsupported:only1/207train+1/71valquiet; almostall usefallback. Laterquietexistsbutdoesnotvalidateautomaticbodyvelocityzeroing.
- Root fullrecordquiet predicted-yawbias interpolationv41 worsens everypredeclarednonzerotraininggain;worstpersonratios1.124/1.264/1.559. Zerochosen. Do notrepeatsamegate/cap/interpolation.

- Equal-weight stored processed endpoint labels: 105.172 mm; plus rates 110.932 mm vs 102.585 control. outputs_recovered_training_v32. Rejected.
- Confidence weighting processed endpoints v33: training-selected weight .5 gives 103.212 mm. Weight .1 gives only .00145 mm validation gain. Do not choose .1 from validation. outputs_weak_labels_v33.
- Undamped dynamic tilt: 100.565 mm but >5% training-person guard violated. Damping .75 selected on training resolves this conditional guard; separate experiment.
- Braking acceleration bridge v34: .25=114.483 mm, .5=136.825 mm. Training selects zero. Gate fires 597 events including ordinary turns/ascent; gravity/tilt confounding. Improves No.18 PS2 but creates large regressions elsewhere. outputs_braking_bridge_v34. Do not repeat broad gate.
- Joint forward/lateral/yaw interval v35: training-selected .3 lateral regularization/.25 lateral gain gives 102.610 mm and worsens heading 1.362 -> 1.398 deg. Other validation-selected grid scores are ineligible substitutes. No material improvement. outputs_joint_planar_v35/report.md.
- Larger training/epochs alone previously reduced loss while trajectory accuracy worsened.
- No.5 AR2/AR3: optical-front/180-degree ambiguity unresolved; no independent physical evidence. Never choose a sign flip by minimizing evaluated error.

- Residual affine clock skew v36: no heldout signal-correlation advantage over residual constant offset. Training .000976439 affine/.001008942 guarded vs .001027325 offset; validation likewise favors offset slightly. No deployed clock-skew improvement established. Do not repeat an unguarded skew fit without distributed independent timing events. Short trials are unidentifiable in this8s protocol, not proven drift-free. Source `outputs_affine_clock_v36/`.
- v37 offset reassignment has regressions despite99.506231mm aggregate synchronization-counterfactual RMSE: No14long10x5Trial1 +21.578mm, several No5/No10 long trials +1–3mm. This is not a replacement production model; refitting corrected training labels and preserving initialization/coverage must precede an estimator improvement claim.

- Unguardedv9corrected-clock residualrefitv38 validation96.329mm is NOTrobustlypromoted: same-fitting-ID conditionalfolds v39 worstpersonNo13+55.96%,No8+5.80%; headingworsens. No13long10x5Trial3 v9clock+4.8517s repeatedcyclealias causes1.589m vs182mm. NativeCOMMONsupport signalcorrelation favorsoldclock(.99786vs.66475yaw;.85886vs.29529speed), so thisis referenceclockfailure ratherthanmerely modelgeneralization.
- Same-newclock refitdampingv40 .75 passesrelative-to-frozennewclock5%guard andgives96.561mm nativecommonvalidation, butoldclockguardfails58.04% dueunchangedalias. A badnewclockbaseline mustnot hideclockregressions. Do notpromote untilbasinadjudicationfixed.
- Hardrejectingalllargeclockjumps wouldloseNo15PS1legitimaterepair: old−4.925→new−.7652s, commonspeedcorr−.96344→.99866, trainingtrial−1.834m. Needfixed-support multichannel/event evidence, not blanketjumpthresholdorposition-minimizing clocks.


Restored individual wheelgyro calibration againstv±L*yaw/2,v38: purewheel yaw979.634mm/39.01deg; allnonzero yaw blends failparticipantguard. Zero-wheel-yaw midpoint refit has no validationgain. Do not add wheel yaw to v34 as a trusted physicalconstraint. Stationary wheelbias is a different futurehypothesis. Evidence: outputs_physical_wheel_v38/report.md.


v39nativewheelquietbias+zero-intercept fits do not rescue differentialyaw: .25/.5blends474.675/673.158mm. Startupgatequalifies only1heldtrain+1validation record; mostcasesdatefallback. Tiny0.091mmvalidationgain atzero yaw is not usefulphysicsimprovement. Avoid relaxinggates fromevaluatedtrajectoryinspection. Evidence: outputs_wheel_bias_v39/report.md,gate_diagnostics.csv.

## v42 arbitration improves means but does not pass guard
Do not promote94.835mm: No.8conditional fold regression5.80% exceeds frozen5%guard. Clock alias correction is supported; universal improvement is not. Absolute supported path-length error also worsens. Full calibration/base folds are still inherited. Next experiment must isolate No.8, not loosen acceptance thresholds.

Arbitrated-clock dampingv46 fails old-clock guard at every predeclared weight; same-clock guard alone again hides correspondence regression. Do not try additional finely searched weights to evade1.05.

v49 simple fullyrefittedphysics+nonlinearendpoint gain.5 hasNo20+83.28% despiteoverall4mmgain. Reject. Do not revertNo8correctedclocks onpositionRMSE: yaw/speedevidencefavorsnew, opticalboundarymidmotion explains accumulatedtravelshift.

## 2026-10-05 additions
- v50 confirms pointwise/endpoint simplification does not solve full-refit robustness: linear endpoint reduces mean to214.171mm but worst participant ratio1.769287; point models are much worse. Physics remains selected.
- Do **not** apply the firmware Info gyro correction factor (~1.14688) to kight_recover research CSVs. They are raw int16 and empirical calibration already operates on raw counts. Doing so would double-correct a metadata bug that was never applied.
- Do **not** replace recorded device timestamps with row/100, seq/100 or seq/104. Firmware audit proves requested100Hz, sensor104Hz and recorded polling~102.4Hz are distinct; pipeline already uses device timestamps.
- Do **not** repeat v52 projected-gravity yaw as if new for v34: related projection features already exist in v33/v34. v54 validates the mechanism only within the simpler full-refit physics family and still sits153.607mm versus retained v34 100.702mm.
- v55 rejects a yaw-first explanation for No.18 PS2: observed-yaw-only leaves405.114mm versus405.191mm predicted, while observed-speed-only gives60.344mm. Future work should target bounded continuous forward-travel/braking residuals or uncertainty fusion, not another broad yaw correction or the failed v34 braking gate.
