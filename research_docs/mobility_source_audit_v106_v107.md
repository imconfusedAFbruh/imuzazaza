# Recent mobility metrics and published-code audit, v106-v107

9 October 2026. Two full primary papers and MASSWU's publisher S1 code supplement
are recovered locally and sealed. Rendered pages confirm methods. The2023 PDF
is a publisher-version mirror after its institutional endpoint returns403; no
PMC challenge is bypassed. No external participant data enter the campaign.

## Metric compatibility

DeVries et al.2023, DOI10.3390/s23167174: two100HzIMUs, ten trained able-bodied
participants on40minute campus courses, Smartwheel/video/inclinometer references.
Calibration selects10squiet level data and10svideo-confirmed straight travel
for every participant, with bidirectional2nd-order5Hz filtering. The wheel
projection and rotation/distance equations are visually checked. Its distance
target is one wheel, explicitly different from center travel during turns.
Reported0.02m/s velocity RMS and distance/turn ICC are not trajectory ATE.
No participant-independent training split or transferable calibration is claimed.

Suansomchit et al.2025 MASSWU, DOI10.1371/journal.pone.0333391: one10Hzwheel-axis
IMU,23participants, six skill tasks, Kinovea reference. It shares the local MCU/IMU
model, which does not prove identical firmware or recordings. The prose specifies
EMAalpha.8, wheel-radius conversion, time integration and5sstatic/3SD onset.
Validity r.887-.998 and rater ICC summarize task outcomes, not optical XY paths.
The15pagePDF's equations1/2 are visually verified, with no heading/2Dpath algorithm.

## v107 supplement consistency check — preregistered before static assertions

Hypothesis: publicly attached S1 contains the stated processing and acquisition
contract needed for reproduction. Check all its extracted source text for sensor
reads, queue payload and transmitted fields, EMA/radius/integration/onset variables.
Do not compile, execute or repair third-party firmware. Require observed code
for an implementation claim; missing supplied code is not proof the researchers
never used it. Scope is the published supplement, not unseen host code/history.

Source S1 contains setup/sensor/BLE communication snippets. Reads use float
accelerometer/gyro calls and transmit six readings rounded to2decimals in JSON.
The queue carries a uint16millis value, but that value is not included in outgoing
JSON. The sampling delay is100RTOS ticks; the supplied snippet does not establish
tick duration/configuration. No EMAalpha.8, wheel-radius velocity, integrated
distance,5sbaseline/3SD onset or processed-result transmission is supplied.
Headers/build configuration and any host-side processing are absent. Therefore
S1 is incomplete evidence for the prose algorithm, not a faithful ready comparator
or proof of deployed acquisition provenance. Do not silently substitute this
float/rounded/no-timestamp interface for local raw-count/device-time packets.

All findings are source/static; no fitting, trajectories, validation/test or
promotion. Source-output manifests and exact code strings pin the evidence.
Next: determine whether supplementary missing host/model code exists in already
available primary/local artifacts; preserve unknown identities and avoid old
firmware hunts without this new evidence. Clock199/207/all207gate remains binding.
