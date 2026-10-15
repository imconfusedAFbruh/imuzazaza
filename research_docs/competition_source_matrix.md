# Primary-source comparison matrix — 9 October 2026

## Requirement-to-local decision checkpoint — 10 October 2026

Independent review of v112/v113/v114 now completed without substantive defect.
This supersedes the earlier pending-review status; the sealed artifacts remain
unchanged. Native get_goal now returns null and ordinaryUsageAllowed is true;
no old Goal resume/reset is claimed.

| Required capability | Available local evidence | Consequence for the next implementation |
| --- | --- | --- |
| Fixed support and comparable pose | v77 six v42 models share common native evaluation; v115 reconstructs426 rows/71 IDs | Same-support retrospective maneuver selector improves fixed refit by only0.198992 mm; no trained selector or promotion |
| All207 strict TRAIN clocks | v113 independently verified: six fixed-reference blockers, upper201/207 | IMU-only feature changes cannot clear the current gate; no new predictor/comparator fit until independent timing evidence or an authorized reference-clock contract revision |
| Whole-pipeline participant exclusion | Conditional base/calibration fits and unknown legacy identities remain | Historical gain cannot serve as independent whole-pipeline validation; unknown legacy stays quarantined |
| Physical wheel/frame inputs | v105 supports500ms prefixes but not stationarity; v112 source requires measured geometry and angular unit conventions | Supported startup duration does not authorize quiet bias calibration; empirical fitted coefficients are not physical wheel rate calibration |
| Comparable external outcome | v112 uses optical speed/angular-rate metrics with different masks; v110 uses frame-IMU angular rate | Neither source's published number is a same-data XY ATE comparator or a victory claim |
| Robust gain | v114 four-person benefit interval includeszero, p=.375; v42 TRAIN guard still fails | Keep retained v34; no significant/outperformance/promotion claim from these reporting audits |

The broad minima requested by the user are retrospective reports, not a new
selector specification. v116 verifies their trial/aggregate hashes and identical
recording identities while documenting changed support counts and weak overall
models. Repeating completed feature searches, scalar conversions, source retrievals
or installing Wheel-INS before these prerequisites would not resolve the gate.

This is a compatibility audit, not a leaderboard. No external method below has
yet been reproduced on the locked wheelchair recordings. Local best remains
conditional v34, 100.702119399 mm participant-balanced XY ATE, 71 already-exposed
validation trials. Raw recordings and private paths are not publication assets.

| Method / primary evidence | Inputs and evaluation | Reported metric/result | Calibration, alignment and runtime | Reproduced here / missing evidence |
| --- | --- | --- | --- | --- |
| [Van der Slikke et al., 2015](https://research.vu.nl/en/publications/opportunities-for-measuring-wheelchair-kinematics-in-match-settin/) | Wheel/frame three IMUs, 20 participants, match-like tests, 24-camera optical reference | Abstract: frame displacement RMSE <=.05 m, speed <=.1 m/s except three vigorous tests; rotation <3 degrees | Skid correction is material. Exact displacement definition/reference point, filtering, clocks, initial pose and participant splits require full methods | No faithful reproduction; strongest directly matched sensor/task candidate. Abstract displacement cannot be substituted for synchronized XY ATE. |
| [Skid-correction companion, 2015, full primary PDF](https://repository.tudelft.nl/file/File_a9e38cd0-ca20-48ae-ab3a-f8056b64a4ee) | Related wheelchair three-IMU method,20people/21tests, DOI10.1016/j.proeng.2015.07.201 | Frame displacement/speed/rotation, test RMSE and ICC; synchronized XY ATE equivalence unestablished | Concurrent skid:20Hz low-pass acceleration discrepancy >2.5m/s2 switches to frame-acceleration speed. Single-wheel correction weights two wheel/frame-rotation estimates by speed/deceleration. Camber, wheel circumference and track width required | Rendered primary pages3-4 verify Eqs1-4. v98/v99 literal-domain audit:600 undefined/153330 out-of-range on conditional resampled proxies; supervised bias/sign and nominal geometry. WhAG fusion/filter/initialization unresolved. No faithful reproduction. |
| [WISDOM,2011 accepted manuscript](https://scispace.com/pdf/wisdom-wheelchair-inertial-sensors-for-displacement-and-2kk5hddhye.pdf) | Wheel gyro pair or single-wheel gyro+accel;9subjects; straight9-10m and36figure-eight loops | Reported calibrated straight-distance error18mm; loop-closure95mm average, neither synchronized XY ATE | No-skid geometry, quiet500ms bias,30straight-push sensitivity calibration; updated-heading integration | Browser full text only, screenshots/local PDF fail.216synthetic camber cases pass; true-sign supplied. Eq13 radius cancellation is correct; erroneous agent derivation falsified. Reference-point/mounting still unresolved. |
| [Smart Wheelchair,2026](https://doi.org/10.3390/s26092657) | ThreeIMUs/GPS/seatmat,7people/~800murban route; no optical C3D | Section mobility/COP statistics, not same-data XY ATE; calibration overtravel.4m/300m | Measured radius.305m/camber3.2deg/track.56m; hardwareIMUsync, trigger clock map, external300mvelocity scale |31pageinstitutional PDF rendered pp6-7; source map passes synthetic endpoints. Fuss2012fulltext extracted, screenshots/download fail.54ideal cases pass; literal yaw Eq6 undefined at0camber. No local reproduction or transferable calibration. |
| [Wheel-INS2 v3](https://arxiv.org/html/2012.10593v3) | Differential-drive robot, wheel/body IMU configurations; four chips/module; ~1227m loop route; PPK/GNSS-INS reference | Mean maximum horizontal position-error/traveled-distance ratios at100m distance increments: .82% dual wheels, .69% body/wheel, .73% triple; heading RMSE separately | Distributed EKF; measured lever arms/misalignment; reference initial heading; static initial roll/pitch/bias; velocity/NHC2Hz, relative-position1Hz | Not reproduced. Chip permutations are dependent, not participant splits. Long-route drift percentages cannot rank short-trial ATE. Mounting, synchronization, physical parameters and same-data implementation remain gates. |
| [TLIO](https://arxiv.org/abs/2007.01867) | Pedestrian headset IMU; learned3D relative displacement/uncertainty fused in stochastic-cloning EKF | No directly comparable wheelchair numerical result in fetched abstract | Learned updates and strapdown propagation; exact training split, alignment, causal windows and metric rules require full-method extraction | Methodological reference only; no wheelchair reproduction or transferable-weight claim. |
| [Real-Life Wheelchair Mobility Metrics, 2023](https://doi.org/10.3390/s23167174) | Wheel/frame IMUs at100Hz;10able-bodied people,40min campus; Smartwheel/video/inclinometer references | Wheel velocity RMS0.02m/s; wheel-distance and turn agreement, not midpoint XY ATE | Participant-specific10squiet level/10sstraight calibration; bidirectional2nd-order5Hz; rigid-beam rotations before/after, cross-correlation and visually assessed10–20ms sync | Full published PDF/rendered equations sealedv106. No local reproduction. Wheel distance explicitly differs from midpoint distance in turns; independent calibration/timing prerequisites unavailable locally. |
| [MASSWU, 2025](https://doi.org/10.1371/journal.pone.0333391) | Singleleftwheel10HzIMU;23people/sixskills; Kinovea task reference | Task validity coefficients.887–.998 with mixed Pearson/Spearman and rater analyses; no XY ATE | EMAalpha.8; wheel-radius conversion/integration;5squiet/3SDonset described in prose | Full PDF/S1 sealedv106/v107. S1 lacks supplied processing, timestamp transmission and frozen six-axis sample; ticks/units/host code unresolved. No build/reproduction; shared board/IMU does not prove recording identity. |
| [Single-wheel frame rotation,2023](https://doi.org/10.3390/s23177423) |9national rugby athletes,60HzXsensDOT; wheel prediction against quaternion-corrected FRAME IMU | Angular-rate RMSE.067/.074rad/s left/right; no optical heading or XY ATE | Participant2sstraight calibration, camber/mounting leakage/radial gravity correction;6Hzfilter; proprietary sync, level-surface scope | v110PDF/renderedpp3–7; v11181idealfigure casespass. Printed atan versus figureatan2/unit/selection ambiguities explicit; authorcode absent, no local reproduction. |
| [Sensor reduction,2022](https://doi.org/10.1016/j.jbiomech.2021.110879) |10people,100Hzrightwheel/frameIMUs versus100HzOptiTrack/fivemarkers | One/twoIMU angular MAE8.1/3.0deg/s, RMS11.2/4.6; speed MAE.10/.10m/s, RMS.19/.20; no XY ATE | Madgwick.03oneIMU;6/10Hzfilters;20sstatic; angularcrosscorr/manualtestsegments; speed>.1m/s, absolute rate>5deg/s | v112fullPDF/appendix visually checked. Referencegap/SVD and selection differ; physicalgeometry/units/filterdetails/code remain unresolved. No local reproduction. |
| [Pinnock Branford, 2026](https://researchrepository.wvu.edu/etd/13492/) | MS project report; four IMUs(two rear wheels/two frame), indoor optical and outdoor GPS | Indoor repeated-turning best fused2D RMSE .116m; outdoor metrics distinct | VQF/Mahony/Madgwick, +/-2g/4g, calibrated/uncalibrated; exact alignment, duration, reference point/splits need full report | Not reproduced; four sensors exceed local three-sensor contract. Single best trial cannot rank a four-person aggregate; report is not a peer-reviewed article. |

## Implementation provenance and the next gate

The official [Wheel-INS repository](https://github.com/i2Nav-WHU/Wheel-INS)
was audited at SHA1a3cc22f61b058612e8e69f6ecdcf5ec1dc95b5f: one binary IMU
loader and one21-state filter, not Wheel-INS2 distributed multi-IMU code.
Sixteen source/config files match pinned Git blob hashes. GPLv3 applies.
Initial-state values are not explicitly loaded before consumption; fixed200Hz
buffer and gap-dt substitution need documented adaptation. Parsed mounting
configuration is unused by the inspected filter; actual gyro-x/full3D conventions
and lever arms require calibration. No build or research-data execution.
See [static implementation evidence](wheel_implementation_v102.md).

Fuss2012 equation extraction and the source-input matrix are now completed as
qualified diagnostics (v103-v105). All429790sensor-grid frames are valid and all
207prefixes contain500ms support, which does not certify quiet calibration.
Literal zero-camber Eq6 is undefined; other yaw relations remain possible.
Recent2023/2025full-method/metric extraction is complete with independently
reviewed qualifications; see mobility_source_results_v106_v107.md. Next:
independent timing/reference evidence remaining under the existing contract.
Do not repeat failed WISDOM retrieval endpoints or run a comparator before the
all207clock/support/provenance gate. The binding eight-family/three-config
budget governs new model search; source/synthetic audits do not create families.

Comparison must lock participants, recording variants, one permitted initial
pose, reference point, clock/support, filtering, integration, and equal-person
aggregation. Retain route, tail, heading, speed and contiguous1/5/10s metrics,
coverage and unavailable genuine endpoints. No fitting/threshold choice from
held outcomes. Published and reproduced numbers remain separate.

Sources above were actually opened on9October2026; wheelchair abstract verified
on the author's university portal after PubMed returned no article text.
Wheel-INS2 full HTML methods/metric definition and skid-paper full prose were read.
TLIO/WVU rows are explicitly abstract/landing-page scope. This matrix does not establish exhaustive literature
coverage or identify an empirically strongest reproduced competitor yet.
