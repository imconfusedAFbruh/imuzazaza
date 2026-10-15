# Timing-aware wheel/body disagreement: cheap falsification before another smoother

Date: 2026-10-08. Scope: source/research only; no model fitting, validation/test
reads, or shared research-state edits were performed for this note.

## Recommendation

First test whether timing-aware wheel/body acceleration disagreement predicts
**held-participant forward-speed error variance**, beyond wheel braking magnitude.
Only if it does, test a velocity/slow-acceleration-bias observer with adaptive
wheel confidence. A plain acceleration smoother is already rejected here.

The diagnostic is cheap, uses the existing 207 identified TRAIN records and
participant folds, and can falsify the proposed uncertainty mechanism before
adding a filter or network. It is not evidence of an accuracy improvement yet.

## What existing work rules out

- `chassis_acceleration_v11.py` already fits empirical chassis acceleration and
  solves a tridiagonal velocity smoother. Its continuous braking/disagreement
  prior reduces confidence in the inherited speed prediction. All 24 nonzero
  candidates failed to beat the baseline on its development fold. The source
  explicitly acknowledges shared information and conditional inherited fits.
- `braking_bridge_experiment_v34.py` used short acceleration bridges after a
  broad event gate; ordinary turns/ascent triggered false positives. Do not
  repeat that event gate or import a literature skid threshold.
- `braking_hysteresis_folds_v56.py` predicts signed speed residual from causal
  wheel derivatives and acceleration-memory features. The proposed diagnostic
  predicts error *variance*, not another signed residual from the same bank.
- `projected_yaw_folds_v52.py` changes gravity-projected yaw. This experiment
  leaves yaw/lateral estimates unchanged and targets forward confidence.

These conclusions follow from the local scripts and
[`FAILED_IDEAS.md`](../research_state/FAILED_IDEAS.md). The relevant novelty is
explicit sample-age uncertainty and a slow bias state, not acceleration fusion
itself. Do not label a reimplementation of v11 as a new physics method.

## Primary-source support and limits

Wheel-INS2 fuses wheel/body information with distributed EKFs and rigid relative
position constraints. Its body IMU supplies pitch missing from wheel-only INS;
mounting angles were calibrated and lever arms measured. Initial headings were
taken from the reference. Therefore its results support the fusion mechanism,
but cannot justify transferring its accuracy to these unverified mounts or
enforcing ideal wheel yaw after this project's rejected tests.
[Authors' paper, IV-A, V-A, VI](https://arxiv.org/html/2012.10593v3).

TLIO fuses learned displacement and covariance with inertial propagation and
bias states. It discusses correlated errors from overlapping predictions and
inflates covariance in its implementation. Lower window MSE need not improve
trajectory error. Its pedestrian model also fails on chair rolling. Accordingly,
use participant-held wheelchair uncertainty evidence; do not transplant its
network, covariance, or independence assumptions.
[Authors' paper, III, V-D, VI, VII](https://arxiv.org/html/2007.01867v3).

The firmware timestamps register reads, not sensor conversion instants. Sensor
ODR is 104 Hz and recorded polling is approximately 102.4 Hz, leaving hidden
sensor-update age up to about 9.615 ms. Sequence counters count polls, so zero
sequence gaps do not remove this uncertainty. The research CSVs are raw counts
and existing empirical calibration must not be multiplied by 1.14688.
[Local primary-source audit](firmware_primary_audit_2026-10-08.md),
[firmware acquisition loop](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_reader.cpp#L187-L229).

The ODR period is an age bound, not a measured Gaussian standard deviation.
Uniform independent sensor phases are an optional sensitivity assumption, never
an acquisition fact. Device-to-PC fits and cross-board timing can add further
uncertainty; the ODR bound does not replace those fits.

## Precise first experiment

Suggested new artifact family: `wheel_body_uncertainty_folds_v60.py` and
`outputs_wheel_body_uncertainty_v60` **after checking that version is free**.
This filename is a proposal; no runnable dataset script was created here.

1. Reuse v56's exact TRAIN membership, `FOLDS`, frozen clock arbitration,
   `load_cache`, `p.calibrate`, and valid-run utilities. Assert every loaded row
   is `partition == 'train'`. Preserve clocks/support; fit calibration and all
   normalization excluding the held participants. Include the full-refit
   physics baseline and the stronger v52 projected-yaw baseline as separate
   unchanged controls. Do not compare these fold results numerically to the
   conditional 100.702 mm result as though they have identical fitting scope.
2. Fit a small **center-only** acceleration map on fitting participants. Inputs
   are center raw acceleration normalized by fold gravity counts and subtraction
   of the fold gravity vector. Target is the 0.2 s C3D forward-speed increment
   divided by 0.2 s, with both endpoints and all intervening samples label-valid.
   Use mean center acceleration over that interval, ridge alpha 1, and equal
   participant weights. Do not include wheel acceleration in this map: doing so
   would erase the independence being tested. This is empirical mounting
   calibration, not verified physical attitude.
3. On nonoverlapping 0.2 s valid blocks compute wheel predicted speed increment
   `dw`, integrated center predicted acceleration `dc`, and `u = dw - dc`.
   Correct slowly varying offset using a causal 2 s EMA of prior block `u`;
   use the *previous* EMA, never the current reference error. This removes a
   slowly varying gravity/tilt proxy; it cannot prove gravity compensation.
4. Build a conservative timing envelope `B` from endpoint wheel acceleration
   magnitudes and integrated absolute center jerk, multiplied by `1/104`.
   Add an explicitly separate measured clock-fit uncertainty term if available.
   Compare `abs(u)`, bias-centered `abs(u - prior_bias)`, and
   `max(abs(u - prior_bias) - B, 0)`. Do not optimize sample shifts to C3D.
5. The target is block-mean squared forward-speed residual of the frozen fold
   baseline. Fit log-variance with a tiny ridge model on fitting participants:
   control predictors are speed magnitude and wheel braking magnitude; candidate
   adds the timing-excess innovation. Epsilon for log variance is fixed
   `1e-6 (m/s)^2`. All caps/standardization use fitting data only.
6. Evaluate held participants with Gaussian NLL, variance calibration by
   fitting-defined quantile bins, rank association, and high-error block recall
   at equal selected-block fraction. Also report PS, AR, SL, ST and long 10x5
   separately. No position result is claimed from this diagnostic.
7. Reject if the extra innovation only recognizes ST tilt/ordinary turning,
   adds no held-person NLL advantage, or has no high-error discrimination beyond
   braking magnitude. A lower fitting error alone does not qualify.

Check first that center-only acceleration increment prediction outperforms
zero acceleration on held blocks. If it does not, reject acceleration-driven
fusion without running a large filter grid. Unknown mounting/lever-arm effects
are likely explanations, but reference labels cannot be used to fix them at
inference.

## Runnable timing-envelope check

The following isolated calculation is executable with the installed NumPy; it
tests units and the envelope behavior, not predictiveness on the dataset.

```python
import numpy as np

def timing_excess(dw, dc, prior_bias, aw_start, aw_end, jerk_integral,
                  sensor_period_s=1.0 / 104.0):
    # All increments are m/s. Acceleration endpoints are m/s^2;
    # jerk_integral is integral(abs(jerk) dt), also m/s^2.
    envelope = sensor_period_s * (
        abs(aw_start) + abs(aw_end) + abs(jerk_integral)
    )
    return max(abs(dw - dc - prior_bias) - envelope, 0.0), envelope

excess, bound = timing_excess(0.01, 0.0, 0.0, 1.0, 1.0, 0.0)
assert excess == 0.0 and np.isclose(bound, 2.0 / 104.0)
excess, bound = timing_excess(0.20, 0.0, 0.0, 1.0, 1.0, 0.0)
assert np.isclose(excess, 0.20 - 2.0 / 104.0)
assert timing_excess(0.20, 0.0, 0.20, 0.0, 0.0, 0.0)[0] == 0.0
```

This conservative bound assumes unmodeled sample-age variation on both block
endpoints and the integrated center signal; it deliberately does not assert an
exact sensor phase. Large discrepancies above it still may be mounting/tilt
errors, not necessarily skid.

## Only after the diagnostic passes

Test a two-state forward observer `x=[v,b]`:

`v_next = v + (a_center - b)*dt`, `b_next = b + random_walk`,
`wheel_speed = v + observation_error`.

Initialize velocity from the baseline IMU estimator and bias from fitting
calibration. Do not impose `v=0` when wheels lock, or estimate initial state from
held reference. Wheel observation covariance comes from the held-safe variance
model; bias process noise is selected inside nested fitting participants. Compare
fixed covariance, adaptive covariance, and adaptive+sample-age variants. A bias
state absorbs slow tilt only approximately; it is not a 3D attitude solution.

Use causal filtering first; an offline RTS smoother is a separate candidate with
future-IMU use disclosed. Reset only at actual IMU gaps, never C3D gaps. Keep
yaw and lateral estimates fixed to isolate forward effects. Report synchronized
XY RMSE, symmetric route RMSE, Fréchet, P95, endpoint, heading, path length,
participant/maneuver results, and worst regressions with frozen <=1.05 guards.

Shared sensors make observation/process errors correlated. Calibrated empirical
confidence and full participant refits are required; the filter covariance must
not be presented as guaranteed statistical consistency. Sustained coasting after
a locked-wheel transition may show little later acceleration disagreement, so
variance discrimination alone may still fail to recover travel. Preserve that
failure rather than adding a C3D reset.

## Interpretation

This is a staged mechanism test, not a promise to achieve 50/20/10/1 mm. At speed
`v`, an unmodeled constant time shift `T` contributes approximately `|v|*T` local
position discrepancy; for a 104 Hz period this is `9.615 mm` per `1 m/s`. It does
not by itself establish the observed half-meter braking travel loss. The useful
question is whether accounting for timing removes false wheel/body disagreement
and makes dynamic confidence generalize better than prior acceleration bridges.
