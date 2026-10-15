# Single-wheel rotation source and consistency protocol v110-v111

Klimstra et al.2023, DOI10.3390/s23177423. Publisher11pagePDF recovered normally;
pages3–7 rendered and visually inspected. Nine national wheelchair rugby athletes,
60HzXsensDOTwheel/frameIMUs, agility tests, proprietary sensor synchronization.
Reference is native-quaternion-corrected FRAME IMU gyro, not optical position.
Table1mean angular-rate RMSE left.067/right.074rad/s; not heading/XY ATE.
Level-surface specificity and non-shareable original data are explicit.

Wheel y-axis is axle; x/z in wheel plane. Two seconds of participant trial's
first straight10m section are selected with wheel rate>5rad/s for camber and
mounting leakage. Prose says minimal transverse rate but prints >.2rad/s;
preserve this ambiguity rather than silently changing inequality. Camber is
arctan(ay/g); all gyro/accel divided by cos(camber). Sx/Sz are mean transverse/
axle ratios; corrected gyros subtract S*axle. Radial acceleration omega_y²*rw
is subtracted from az before6HzButterworth filtering; order/phase unspecified.
rw is sensor hub lever radius, not necessarily the wheelchair rolling radius.
Reported accelerometers are in g, so radial correction requires compatible
units; conversion is not explicitly stated in the displayed formula.

Angle equation on page5 prints arctan(az/ax), while prose calls it two-argument;
Figures3/4 labels on page6 show sin(arctan2(AX,AZ)) for gyroX and cosine for
gyroZ. These argument and quadrant conventions cannot be silently interchanged.
Do not claim author code error: Labview implementation is not supplied.
The figure-implied sum equals the gyro dot normalized in-plane gravity.

## v111 preregistration before synthetic calculations

No recordings/fit/trajectory. Test source-consistency on ideal zero-camber
wheel axes with known SI units/radial lever radius, nine phases around full
circle, yaw{-2,0,2}rad/s and wheel spin{-8,0,8}rad/s. Compare figure-implied
atan2(ax,corrected_az) weighted gyro sum to true yaw. Explicitly test printed
single-argument ratio convention separately; report disagreements/undefined
denominators, never patch into a purported faithful implementation.

On ideal static tilted axle, evaluate arctan(sin(truecamber)) versus truecamber
for0/3.2/12/20degrees; report geometry approximation and associated gyro-scale
ratio. This analytic scenario is not evidence of empirical error or source
failure. Unit boundary check: SI radial acceleration must be divided by9.80665
if subtracted from an accelerometer expressed in g; equivalent SI/g paths agree.
Require figure yaw recovery/units equivalence within1e-12. Source hash/protocol/
script and outputs sealed; no filtering-order guess, bias/mounting fit or claim
of faithful dataset reproduction. This consumes no new predictor family/config.
