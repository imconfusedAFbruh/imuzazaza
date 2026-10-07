# Status — 2026-10-04

## Latest active checkpoint (supersedes earlier snapshot below)

Retained best remains v34dynamicblend100.702119mm. Corrected-clock refitv38 reached96.329130mm ownclock /96.172432mm nativecommon, independently reproduced with route46.629864mm, but FAILED conditionaltrainingguard No13+55.96% andNo8+5.80%; NOTPROMOTED. Training alias No13long10x5T3 v9shift+4.8517s independently disproved usingfixedsupportyaw/speed anddistributedwindows, no positions. No15PS1large+4.1598s repair is strongly supported. Another earlierSlopeHARTrial9newshift is contradicted;No19OS1ambiguous. Freeze multichannel arbitration before refit.

Active syncagent implementing clock_arbitrated_refit_v42.py /outputs_clock_arbitrated_v42 and subsequentmatchedfolds outputs_clock_arbitrated_folds_v43: two contradicted largeupdates +oneambiguous useoldclocks;two supportedlargeupdatesnew;smallv9updatesunchanged;8QCfallbackold;all473/71 fixedIDs. No validationretuning/test.

PDF82pages (11methods+71nativecommonclockatlas) created output/pdf/trajectory_research_accuracy_audit.pdf. Root repaired reviewer findings: historicalv34vsnewv39atlas descriptions, failedguardstatus on everyatlaspage, latestsources. Independent PDFagent stillreviewing; latestPDFmustrerender/review beforedelivery.

Quiet yawbiasv41 fails: trainingzero132.076mm selected; gain.25=132.866mm,worstratio1.124; .5=135.143/1.264;1=142.284/1.559. No velocityzero/referenceupdates. Wheelphasev37 fails102.829mm. Physicalwheel/yaw/bias experiments all reject meaningfulgain. Nativefirst5quiet qualifiesonly1/207train+1/71val;laterunchangedgatequalifies83train+32val. Most originalv14startup states are datefallbacks.

Active sensorcalibration specialist researching firmware/source, nominalunit vsphase consistency and quantizedtimestamp identifiability. Account ordinaryusageallowed atlastcheck; agentcreditfailurefrompreviouswindow no longercurrentblocker.

## Resumed window, active work

Read all six state files before resuming. Independent route, synchronization and skeptic agents ran in parallel. Root built an IMU-only v34 loader and freshly recomputed startup from native IMUs: all71 reproduced100.702119424mm, maximum cached XY difference5.879e-9m; poisoned reference fields cannot affect motion prediction. Audit: outputs_dynamic_loader_v36/run.json.

Route audit complete: supported-route RMSE49.726mm, mean trial P95 96.769mm, sampled Hausdorff149.285mm, last-supported endpoint127.772mm, max-run discrete Frechet165.919mm. Hausdorff/Frechet slightly worsen vs original. These partial-route metrics do not bridge invalid optical frames; no full-route Frechet claim. Report: outputs_route_metrics_v36/report.md.

Skeptic reproduced headline exactly, with45/71 improving and26 worsening. No14 supplies most gain; four-person descriptive bootstrap gain interval[-.104,4.380]mm includes zero. No18PS2 not fixed. All71 new plot review underway/completed by agent with straight-axis padding repair.

Affine residual clock audit favors offset over skew on training blocked correlations. All544 native acceptedC3Ds100Hz; IMU median102.396Hz. Device-to-PC affine fitting already exists; repeated receiver timestamps indicate packet batches. Residual signal-only offset counterfactual running, especially No18long10x5. No production score changed.

Root running wheel_phase_experiment_v37.py, session31387: train-selected accelerometer gravity-phase features, three conditional folds, independent physical proxy hypothesis; calibration/misalignment contamination explicitly recorded. No test access.

Current window ended at a real external blocker: both active sub-agents reported workspace out of credits. Their experiments finished before the failure. Main agent saved this state; no request for user to say continue.

Best new training-selected candidate: dynamic tilt motion blend v34, weight 0.75. Validation equal-participant mean trajectory RMSE **100.702119 mm**, heading **1.260899 degrees**; original v21 **102.585179 mm**, **1.362298 degrees**. Improvement 1.883060 mm (1.84%). Selection preceded validation, using three conditional training folds / 12 target-training participants. Worst-person training ratio 0.993947; base/calibration were inherited, so this is not a complete nested independent evaluation.

All 473 accepted training recordings used: 266 earlier, 207 target training. 71 validation recordings; fixed directly observed masks. Test not accessed this window. Historical validation exposure and retrospective test inspection prevent a fresh blind-test claim.

All 71 original individual trajectory figures plus seven maneuver sheets visually reviewed by visual specialist. Evidence: outputs_image_audit_v33/report.md and visual_audit.csv. New blend trajectories are cached but have not yet received a complete visual audit. Route metrics and affine-clock experiments requested at the end of this window are pending; do not imply they were completed.

No arbitrary rotation, reflection, scale, endpoint snapping, heading flips, or reference resets used. Original C3D files unchanged. Stored processed positions are not treated as directly observed scoring targets.
