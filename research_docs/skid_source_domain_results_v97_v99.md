# Source equations and conditional formula domain, v97-v99

Completed9October2026. Two pages of the primary six-page skid PDF were rendered
and visually read; a separate read-only reviewer confirms all four transcribed
equations. Local source contract/images/PDF hashes are sealed in v97. Eqs1-3
produce a right-wheel weight; Eq4 blends wheel-derived frame-center speeds.
The preceding wheel acceleration/gyro fusion and camber procedure is delegated
to references, so these equations alone are not a full trajectory algorithm.

v98 evaluates the literal weights on full-record common100Hz TRAIN sensor grids,
preserving valid runs and backward-difference support. These are resampled v80
streams, NOT native acquisition samples. Proxies use nominal.070degree/s/count,
.30m radius and v84fold-selected wheel axis/sign/bias. Selected-axis bias itself
is overwritten as -intercept/scale after supervised JOINT midpoint regression.
Thus avoiding learned scale magnitudes does not make them independently calibrated
rim measurements. No genuine WhAG or physical skid prevalence is established.

All207recordings/all15No20 are retained:429790resampled grid frames,429583eligible
adjacent-valid frames. Literal weights are undefined on600eligible frames from
zero acceleration sums;153330finite weights lie outside[0,1](35.69%of eligible
frames).38571frames have opposite wheel signs and155141opposite derivative signs.
These counts diagnose the literal formula on conditional proxies only. The short
source does not establish rectification, clipping, zero-weight fallbacks or reset
behavior; none is silently inserted. Straight constant-speed and counter-rotating
synthetics expose singularities; mixed derivative signs can create nonconvex or
near-cancelling weights. Algebraically reduced weights agree within7.63e-12
relative error wherever original denominators are safely defined; this does not
license extending the reduced equation across original0/0.

v99 verifies639parent hashes, independently reconstructs all207proxy arrays,
validity masks/differences/literal weights and counts; maximum weight difference0.
Per-person/maneuver domain fractions are saved. Two analytic test cases pass.
No C3D signal reads, clock changes, fitting, prediction, validation/test access,
trajectory scoring, promotion, commit or push. Historical bestv34 remains
100.702119399mmATE/49.726226563mmroute on71exposed validation trials.

Config radius.30m/hub width.52m/camber0 are settings, not independently established
physical measurements. Existing skid_experiment.py is a learned disagreement
adaptation, not a source reproduction. Do not rerun it or rebrand these counts.
The reviewer exposed the resampling/supervised-bias qualifications above; completed
v98/v99 filenames/fields retaining 'native' must be read as resampled grid counts.

The next justified task is the source's ref[10], Pansiot et al.WISDOM, for wheel
rotation/fusion/camber conventions. The author-hosted PDF and the relevant2026
three-IMU paper are being retrieved separately; recover actual equations and
physical assumptions before a faithful comparator or clearly labelled adaptation.
No source-unspecified conventions are selected from position RMSE or these counts.

Preregistration: skid_source_domain_v97_v99.md. Completed immutable outputs:
outputs_skid_source_v97, outputs_skid_domain_v98, outputs_skid_domain_review_v99.
Guarded numeric commands were python research_run_guard.py skid_domain_v98.py
and python research_run_guard.py review_skid_domain_v99.py. Do not rerun into them.
Nonwriting test: python -m pytest test_skid_domain_v98.py -q.
