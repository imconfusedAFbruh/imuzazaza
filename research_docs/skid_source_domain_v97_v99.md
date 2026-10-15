# Preregistered source and formula-domain audit v97-v99

Registered9October2026 before sensor-domain scores. Three bounded cycles:
v97 source/physical-contract extraction, v98 literal-formula domain audit on
sealed native TRAIN207streams, v99 independent arithmetic/provenance review.
No new estimator family or accuracy experiment before existing coverage gates.

The primary PDF is locally saved outputs_skid_source_v97/skid_2015.pdf; page4
was rendered and inspected. Source Eq1: S_R=R/(R+L); Eq2: A_R=diff(L)/diff(R+L);
Eq3: W_R=(S_R*A_R)/(S_R*A_R+(1-S_R)*(1-A_R)); Eq4:
FrC=FrC_R*W_R+FrC_L*(1-W_R). R/L denote WhAG_R/L, not our joint midpoint
coefficients. Continuous frame rotation corrects each wheel-center estimate;
camber, wheel circumference and track width are physical prerequisites.
Concurrent skid compares20Hz-filtered accelerations and switches at2.5m/s2.
Filter order, switching/integration anchoring and signed/zero-denominator policy
are not established by this short paper. Do not invent those as faithful code.

v98 applies the literal weights only to nominal sensor-derived rim-speed proxies:
raw wheel gyro selected axis/sign and bias from sealed v84foldcalibration, nominal
.070degree/s/count and.30m radius. This is a conditional axis/unit/geometry proxy,
not physically verified WhAG or a reproduced displacement estimator. Existing
v84wheel terms fit JOINT midpoint speed, so never use their learned magnitudes
as individually calibrated rim velocities. No C3D signal/positions are read.
Load native v80sensor arrays; preserve valid runs; diff is a one-step backward
difference, first sample/run invalid. No smoothing/rectification/gate search.

For every207recording report exact/near singular denominators, finite weights,
weights outside[0,1], opposite signed wheels and opposite derivatives. Near-zero
is a prespecified relative1e-10 arithmetic diagnostic, not a fallback threshold.
Cross-check algebraic W_R=R*diff(L)/(R*diff(L)+L*diff(R)) only where every original
denominator is safely defined. An algebraic extension across original0/0 is not
the source's specified behavior. Save inputs/counts/profiles for review.

Acceptance: code passes analytic straight/decelerating/opposite/singular cases;
all207IDs/15No20, fold fit/held disjointness and parent hashes match. No clock
acceptance, fits, trajectory scoring, validation/test or promotion. Results only
decide faithful applicability; unknown physical inputs stay unknown. No fallback
or weight clipping is selected from these outputs. v99 independently reconstructs
literal formulas/counts, verifies source equation image and manifests; report
limits and next compatible comparator task. Scope is new diagnostics/tests,
local outputs/state/README; no callers/config/exports/production behavior changes.

Initial PDF download failed bundled Python certificate verification. Native
PowerShell HTTPS download succeeded with OS trust; certificate checks were not
disabled. Preserve source hash and render evidence. Earlier skid_experiment.py
is a learned disagreement adaptation, not these source equations; do not rerun.
