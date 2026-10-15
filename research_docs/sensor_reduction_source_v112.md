# Optical-reference sensor reduction comparator, v112

van Dijk et al.2022, DOI10.1016/j.jbiomech.2021.110879. Institutional final
published7pagePDF includes a cover; PDFpages4/5/7 (article3/4/6) rendered and
visually inspected. Ten participants, rightwheel+frameNGIMUs100Hz, ten-camera
OptiTrack100Hz/fiveframe markers, sport tasks and20sstatic bookends. No local
recordings, held outcomes or new predictor were used in this source audit.

Optical analysis interpolates gaps shorter than1/6s, fits rigid motion from at
least three markers using SVD against the first static sample, filters translation
at10Hz and differentiated rotation at6Hz. The prose names sagittal-plane angle
but discusses horizontal wheelchair yaw elsewhere: preserve the convention
ambiguity. Local observed-only support/reference construction is different.

TwoIMUs: frame vertical gyro6Hz, wheel axle gyro10Hz, camber/wheel circumference/
frame-center correction. OneIMU: Madgwick gain.03, differentiated global Euler
angles6Hz; same wheel-to-center speed correction. IMU/reference synchronization
uses angular-rate cross-correlation; exercises selected manually from plots.
Linear metrics include only absolute speed>.1m/s; rotational only |rate|>5deg/s.
Table3mean-of-participant angular MAE8.1vs3.0deg/s, RMSE11.2vs4.6deg/s;
linear MAE.10vs.10m/s, RMSE.19vs.20m/s (one versus twoIMUs). No XY ATE.
No independently held calibration/model-selection evaluation is specified.

AppendixA visually verified:
AVwheel_corrected = AVwheel + tan(camber)*AVframe*cos(camber)
LVwheel = AVwheel_corrected*WheelCircumference
daxle_center = WheelBase/2 - sin(camber)*WheelDiameter/2
LVframe = LVwheel - tan(AVframe/fs)*daxle_center*fs

Angular units/turn conversion are not explicit in these displayed formulas:
circumference multiplication needs turns/s, while tan(AVframe/fs) needs radians.
Do not silently equate a raw rad/s signal with turns/s or claim unpublished code
used a wrong conversion. Source WheelBase must be mapped to physical lateral
geometry before adopting Eq2.3; local nominal hub separation is not established
to equal that parameter. Filter order/phase, yaw convention, initialization,
actual gyro/accel use in Madgwick and parameter measurement/code are incomplete.

The paper helps define comparator inputs and velocity metrics but does not remove
the local calibration/clock/provenance gates. Its conclusions against an optical
reference must remain separate from2023single-wheel rotation versus frameIMU.
No new author-data download, implementation/adaptation or accuracy victory.
