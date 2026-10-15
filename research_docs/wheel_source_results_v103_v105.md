# Delegated source, synthetic domain and actual input support, v103-v105

9 October 2026. Fuss2012's15-page author-uploaded publisher PDF is browser-readable
but not locally recovered or visually certified. Access-restricted download and
failed page screenshots are recorded in v103; no restriction/TLS bypass.

v104 tests54ideal rolling cases, including both yaw signs, forward/backward/still
center speeds and camber0/3.2/17degrees. Wheel speed recovery is exact at printed
precision;36nonzero-camber cases recover yaw within6.22e-15, including12zero-yaw
cases. Only24cases apply nonzero correction (12positive/12negative yaw).
Literal Eq6 is0/0 for18zero-camber cases; no fallback is inserted. This does not
mean yaw is universally unobservable: other sensor/geometry relations exist.
The measured wheel-difference sign is valid for the tested geometry; arbitrary
track/radius/camber combinations are not certified. Balanced-wheel raw average
preserves ideal center speed but does not prove local physical camber symmetry.
A separate read-only reviewer verifies all hashes and these qualifications.

v105 checks actual sealed common-grid support and calibration metadata.423parent
hashes pass;207TRAIN trials and all15No20 are retained. All429790resampled sensor
frames are valid, with no internal invalid samples. All207have complete first
500ms sensor support. Availability is not stationarity, so no quiet-prefix bias
or sensitivity fit is authorized by these counts. Cross-sensor-gap smoothing
cannot explain this dataset's clock disagreement when its sensor mask has no
gaps; optical gaps and sampling/reference timing still require separate treatment.

The input-evidence matrix distinguishes nominal settings from measured physical
geometry, scalar supervised axis fits from3D mounting, and valid samples from
quiet calibration. It prevents a fake faithful-comparator claim while retaining
the possibility of explicitly labelled training-calibrated adaptations after gates.
See wheel_inputs_v105.md and immutable outputs_fuss_source_v103,
outputs_fuss_checks_v104, outputs_wheel_inputs_v105. Guarded commands:
`python research_run_guard.py fuss_checks_v104.py`
and `python research_run_guard.py wheel_input_audit_v105.py`.

No motion fits, predictions, scoring, validation/test access or promotion.
Clock gate remains199/207; retainedv34 remains100.702119399mmATE and
49.726226563mmroute on71previously exposed validation trials. Existing raw files
and completed artifacts remain untouched. Missing physical/reference/clock
provenance is not resolved by the synthetic/source checks.
