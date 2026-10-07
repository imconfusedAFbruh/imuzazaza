# Best results

## Updated guard / clock benchmark decisions

Retained robust conditional candidate remains100.702119mm. v38clockrefit96.329130mm ownclock /96.172432mm nativecommon is NOTPROMOTED: old132.076→new126.514mm conditionalfoldmean butworstpersonratio1.559583 fails5%guard. Nativecommon oldblend100.592598→new96.172432; route49.680804→46.629864;P9596.768545→90.051368;Hausdorff149.329413→141.124487;Frechet165.876480→159.650336. Lengtherror105.713574→112.103834 worsens.30/71sync and32/71route regress. Benchmark definitions mustnotmix.

v40damping96.561154mm nativecommon passes SAMEcorrectedclockcontrolguard1.02836 butfails OLDclockoverallguard1.58037. AlsoNOTPROMOTED;clockaliaspersists. Arbitratedclockv42inprogress, no claimedresult yet.

Storedprocessedsource v37 isweaksecondary only:61continuous71records, blendroute49.484mm vsprimary49.726mm; fullsupportedlength182.785mm showsreference-dependenttravel differences. Primaryscoresunchanged.

Metric: mean of trial synchronized 2D position RMSE within participant, then equal mean across four validation participants. Directly observed supported frames only; no post-hoc alignment. This is not pooled-frame RMSE.

| Method | Validation mm | Decision |
|---|---:|---|
| physics/ridge | 116.899 | historical baseline |
| original v21 | 102.585179 | established control |
| dynamic tilt 0.3Hz undamped v33 | 100.564663 | rejected: worst training-person regression 8.57% |
| dynamic tilt blend 0.75 v34 | **100.702119** | best new training-selected candidate, visual/full-stack audit pending |
| long observed intervals v34 | 102.257419 | small training-selected gain; not combined with tilt |

Blend heading RMSE: 1.260899 degrees. Training pooled participant score 140.030322 -> 132.240200 mm. Worst held training-person ratio 0.993947.

Blend participant RMSE mm: No.10 67.570596, No.14 96.405508, No.18 134.341813, No.5 104.490560. No.10 worsens relative to original 67.180 mm: overall gain is not universal.

Blend maneuver RMSE mm: 10x5 143.900042, AR 87.942655, CR 55.128844, OS 95.004803, PS 188.816248, SL 118.068214, ST 58.404170. PS remains the largest mean error. OS has only 3 recordings / 2 people.

Artifacts: outputs_dynamic_blend_v34/run.json, selection.json, model.json, trajectories/*.npz and artifact_manifest.json. The model blends IMU motion predictions before integration; it never blends to evaluated truth. Need build/review deployment loader before operational promotion.

50/20/10/1 mm have not been established. Current evidence supports modest empirical improvement, not a millimeter claim. Reference absolute accuracy, units and mounting remain unverified.
