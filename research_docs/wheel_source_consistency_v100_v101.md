# Wheel-source compatibility and equation consistency, v100-v101

Preregistered 9 October 2026, before the synthetic checks below. No recording,
calibration, prediction or held-out score is used. This is a source audit, not
a new predictor family. Preserve existing outputs and the all-207 clock gate.

Hypothesis: the source's geometry equations can be checked independently before
implementing a same-data comparator. Baseline: literal source equations, compared
with identities derived from those same equations. Accept transcription only
where visual evidence exists; an extraction-only inconsistency remains provisional.
No repair is selected by trajectory error. A published typo and an extraction
error must remain distinguishable.

## v100 source evidence

WISDOM, Pansiot et al. (2011), DOI10.1088/0957-0233/22/10/105801:
https://scispace.com/pdf/wisdom-wheelchair-inertial-sensors-for-displacement-and-2kk5hddhye.pdf
is an 18-page author accepted manuscript, not the authenticated publisher version.
The browser reads the full text; its page screenshots fail. Author HTTPS fails
certificate validation, author HTTP returns404, and the mirror download is empty.
Do not call the zero-byte file a recovered PDF. Do not bypass TLS verification.

Text-derived Eq2 is
`g = [yaw*cos(a)*sin(w), wheel + delta*yaw*sin(a), yaw*cos(a)*cos(w)]`,
with delta+1 right/-1 left. Eqs5-7 recover signed yaw magnitude and subtract
its camber contribution from the wheel-axis gyro. Eq14 uses the gravity-dominated
accelerometer sign on the larger transverse gyro axis. Eq18 integrates using
the updated heading. The method assumes no skid, measured geometry and a quiet
500ms baseline; sensitivity is calibrated with30 straight pushes. Neither the
quiet prefix nor independently measured geometry is established locally.

Extracted Eqs10/12 imply
`R = B*(wheel1+wheel2)/(2*(wheel1-wheel2))` because equal wheel radius cancels
from numerator and denominator. This agrees with extracted Eq13. The first
synthetic audit failed because the agent incorrectly retained radius only in
the numerator. Preserve that failed script and original preregistration in
outputs_wheel_source_checks_v101_attempt. This falsifies the agent's proposed
inconsistency; no source error is established. The immutable v100 contract's
provisional suspicion is superseded by this arithmetic correction.
Also, Eq18's displacement follows one wheel's ground velocity; the local target
is the hub midpoint. A lever-arm/reference-point mapping must be explicit.

The2026 Sensors paper, DOI10.3390/s26092657, is locally recovered as a31-page
PDF from the institutional repository:
https://publica-rest.fraunhofer.de/server/api/core/bitstreams/0264a2d2-d601-4998-82e1-2e295dfd6e6f/content
Rendered pages6-7 verify its affine trigger mapping and external300m calibration.
It studies seven people on an approximately800m urban route with GPS/seat mat,
known geometry, hardware-synchronised IMUs and a velocity scale correction from
known distance. This is not a same-data optical XY ATE benchmark. It delegates
wheel kinematics to Fuss (2012), DOI lookup still pending; no local reproduction.

## v101 planned checks and acceptance

Use only synthetic wheel/yaw rates, radius.30m and track.52m as arbitrary test
values, not claims about actual wheelchair geometry. Include both sensor sides,
positive/negative/zero yaw, wheel phase near quadrature and camber0/3.2/12degrees.
Generate gyros from Eq2; recover yaw via Eq5 using its known synthetic sign, then
wheel via camber subtraction. Require absolute errors<=1e-12.

For non-equal wheel rates, compare radius from Eq10 plus Eq12 with the literal
extracted Eq13. Require discrepancy<=1e-12 without changing equations. This
replaces the expected-discrepancy hypothesis after analytic falsification, without
any recording scores or tuning. Validate the
2026 affine map at both trigger endpoints and an interior point for nonzero
offset/skew; reject equal slave timestamps. Require error<=1e-12.

Record source hashes, assumptions, test inputs and results in new sealed output
directories. These checks cannot validate actual mounting, gravity-sign reliability
under acceleration, physical bias, source-image typography or trajectory accuracy.
Next useful work: audit the official Wheel-INS code's actual single/multi-IMU
capability and the delegated Fuss source, preserving all missing inputs explicitly.
