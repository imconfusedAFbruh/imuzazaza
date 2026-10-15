# Preregistered seed-free clock experiment, v83-v85

Registered before execution on 8 October 2026. Budget: three substantive cycles:
uncalibrated seed audit, fresh fold calibration/held-clock audit, independent
provenance and coverage review. No trajectory estimator search or lag selection
from position error. Only 207 known TRAIN records; validation and test closed.

Hypothesis: full-record unfitted wheel/frame gyro magnitude events can supply
bootstrap labels without historical held-participant seed calibration. Reuse
the observed-segment signal/peak search and its frozen acceptance gates;
absolute reference yaw for the magnitude seed, signed yaw after fold fitting.
Reference gaps are never filled. Full-record sensor arrays are hash-verified
v80 inputs; inherited crop indices/offsets are not used by seed fitting.

Calibration uses only accepted fresh-seed labels from other TRAIN participants.
Hold all 207 identities fixed. Rejected seeds or held clocks remain unavailable;
never fill them from old clocks. Require all 207 supported held clocks, unchanged
scoring support/pose, and distributed alias review before a predictive refit.
No reduced-support aggregate may replace the benchmark. If coverage fails,
report diagnostics and missingness rather than fabricate ATE or other trajectory
metrics. This removes one seed dependency, not inherited reference geometry,
dataset acceptance, sensor time reconstruction assumptions, or all leakage.

Commands (immutable outputs, never rerun into completed directories):
`python research_run_guard.py seedless_clock_v83.py fold_seedless_clock_v84.py`

Synthetic check: magnitude seed recovers a known zero lag, survives poisoning
of inherited sync terms, and creates no-gap derivative labels. Fold fits assert
participant and ID disjointness. Third cycle independently verifies hashes,
reconstructs labels and counts, compares clocks without ATE selection, and
reviews the coverage decision. Historical v34 remains the retained benchmark.

## Completed results and decision

v83 accepted 190/207 magnitude seeds (163 frame-yaw magnitude, 27 wheel-speed
magnitude); 17 rejected under unchanged gates. v84 fits use respectively
126/125/129 fresh seeded training records, with 68/69/70 held records. All
fits exclude held participants/IDs; all six date/setup fits select positive
left gz, negative right gz and positive center gx. No inherited lag or fitted
clock seed enters these calibrations. The optical geometry policy, prior
TRAIN207 selection and device/packet reconstruction still remain conditional.

v84 accepted 199/207 held clocks (192 signed yaw, seven speed); eight rejected.
Missing held clocks: No.7 CR1/OS1/OS2, No.4 CR3/PS1, No.19 AR1, No.15 AR3,
No.17 OS1. All 15 No.20 wide-marker recordings remain represented and accepted.
This fails the preregistered all-207 gate; no reduced-support estimator is fitted.

Most supported clocks agree with the previous arbitrated offsets: median
absolute difference zero, only three differ by more than 1 ms. However No.13
10x5 Trial3 returns the known repeated-cycle alias: fresh +4.1517 s versus
saved -0.7 s, a **4.8517 s** difference. Its signed-yaw correlation is 0.66475
and runner-up 0.57275, demonstrating that acceptance alone cannot establish
correct timing. This offset would lose **458 frozen IMU-support frames**.
No.19 OS1 differs by **0.5821 s**, also requiring distributed signal evidence.
No.17 CR2 differs by 1.7 ms. These are diagnostic comparisons; saved offsets
are not treated as independent timing truth and ATE never selects a lag.

v85 checks 1,041 sealed artifact hashes, independently reconstructs all 190
fresh derivative-label masks and 249,296 labels with exact numerical agreement,
and matches all 207 observed reference XY/heading/mask arrays to saved v81.
The 1,041 hashes cover v83/v84/v80/v81; later v85 hashes and source dependency
hashes are separately recorded in research_state/seedless_v83_v85_verification.json.
A separate read-only reviewer independently verifies the 402 v83 and six v84
artifact hashes, source hashes, fits, counts and alias concern. Neither review
is a blinded independent timing study. Existing optical masks stay unchanged;
sensor smoothing retains offline future data and may cross interpolated sensor
gaps. The synthetic check verifies known-lag and poisoning independence; actual
190-trial bracket-mask reconstruction verifies label gap handling.

All new trajectory metrics (ATE, MAE, X/Y, endpoint/drift, RTE, yaw/velocity,
bias/LoA, R²/Pearson, position P95, route and length) are **unavailable**, because
these are clock/label experiments with no new trajectory predictions. Per-trial,
per-participant and per-maneuver coverage/clock tables are saved. Existing v81
TRAIN scores and v34 validation scores remain unchanged; no eligible predictive
experiment is being hidden by reporting only its clock metric.

Decision: the narrower seed-fitting provenance hypothesis is supported; the
hypothesis that this alone yields complete, reliable clocks is rejected.
No estimator promotion, commit or push. Retained v34 is **100.702119399 mm
synchronized ATE / 49.726226563 mm route**, on 71 previously exposed validation
trials, a different scope from TRAIN207 simple native/new **147.565311 mm**.

The first v84 attempt stopped before held results because the stored NPZ sample
rate was a zero-dimensional ndarray and SciPy requires a scalar. It is preserved
as outputs_fold_seedless_clock_v84_scalar_attempt; converting the loaded hz to
float fixed the artifact boundary. Only v84 was rerun; completed v83 was reused
after hash verification. Final successful commands:

```powershell
python research_run_guard.py seedless_clock_v83.py fold_seedless_clock_v84.py
# First command completed v83; v84 scalar attempt preserved, then:
python research_run_guard.py fold_seedless_clock_v84.py
python research_run_guard.py review_seedless_clock_v85.py
```

Three substantive cycles exhaust this run's bounded budget. All guarded jobs
finished and released their own lock; no persistent process remains. Next:
preregister v86 seed-free distributed yaw/speed basin diagnostics, starting with
the two aliases and eight rejects. Reuse full-record channels and fresh fold
fits, never inherited fitted clock fallbacks. Inspect candidate basins from
signals/events, not trajectory error; preserve every accepted identity and
frozen support. Do not blindly repeat v83-v85 or relax gates to gain coverage.
The fair published competitor and strict geometry/reference separation remain
unfinished; no superiority claim is justified.
