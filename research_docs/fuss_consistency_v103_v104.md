# Fuss wheel-kinematics source and conditional consistency check, v103-v104

Preregistered9October2026 before synthetic scoring. Hypothesis: signed camber
correction and frame-speed equations are internally consistent on ideal rolling
motion, but literal Eq6 is undefined at zero camber. No recording or calibration
is read; no model family, parameter tuning, accuracy comparison or promotion.

Primary source: Fuss2012 DOI10.1080/19346182.2012.754895, SportsTechnology5:29-42.
An author-uploaded publisher PDF is readable through the browser at
https://www.researchgate.net/profile/Franz-Fuss/publication/279731731_Speed_measurements_in_wheelchair_sports_-_theory_and_application/links/5598cd1608ae5d8f3933fbf7/Speed-measurements-in-wheelchair-sports-theory-and-application.pdf
The15-page document includes publisher cover. Local download is access-restricted;
page screenshots fail. Equations below remain text-derived, not visual proof.
Do not bypass the restriction or retry unchanged URLs.

Source Eq5:
`true_wheel = measured_axle - transverse_norm*tan(signed_camber)*sign(M_R-M_L)`.
Camber is positive left/negative right; both axle axes point left. Phone-specific
right-axis reversal applies to all gyro components, not an arbitrary scalar sign.
Eq6 uses the left-wheel convention:
`yaw = (measured_axle-true_wheel)/sin(camber)`.
Eq11 center speed is radius times the mean wheel angular speeds. The source
also recommends independent distance calibration. Local metadata does not prove
these physical conventions or calibration. In particular local config camber0
cannot justify substituting a zero-camber limit for literal Eq6.

Use arbitrary synthetic radius.30m/track.52m; camber0/3.2/17degrees; center
speed-1/0/1m/s; yaw-2/0/2rad/s; phases0/.7rad. Ideal rolling wheel angular
speeds are `(center +/- yaw*track/2)/radius`. Generate axle measurements with
opposite yaw*sin(camber) contributions and transverse norms abs(yaw)*cos(camber).
Use only measured axle difference to obtain turning sign. Require true wheel
and center speed recovery<=1e-12, and yaw recovery<=1e-12 where camber>0.
At camber0 record undefined literal Eq6 without clipping, division fallback,
or substitution. This is a formula-domain finding, not a physical sensor failure.
Compare balanced-wheel average before/after correction analytically; do not
infer local physical camber symmetry. Preserve all attempts/output hashes.

Next: map source-required inputs against existing setup artifacts and prohibit
faithful-comparator labels where physical mounting/geometry/calibration are missing.
All207clock gate, original support and single initial optical pose remain binding.
