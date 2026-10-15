# v125: separate speed and yaw priors

Preregistered 15 October 2026 in response to the renewed direct request,
"Make the best model ever!!!!!". Continue TRAIN development; do not treat the
completed v124 experiment as a reason to stop. Preserve the separate validation
authorization boundary, original timing/provenance limits and reserved test.

## Hypothesis and fixed scope

The v124 trial-RMSE objective uses the same quadratic prior strength for the
forward-speed and yaw readouts. Their correction scales and propagation through
the integrated path differ. The scalar penalty1 candidate improved the mean
but failed participant guards, whereas penalty10 passed. Separate shrinkage
may retain useful corrections while controlling the less transferable axis.
This is a hypothesis; no candidate result is known at preregistration.

Use exactly three (speed, yaw) prior strengths: (1,10), (10,1), (3,3).
The third is a symmetric intermediate control. The prior and initialization
remain the same fold's frozen v121 penalty10 weights, with its normalization,
fixed16-state reservoir, v34 .75 parent, correction caps .05m/s/.02rad/s,
three participant folds and fitting-only twelve-step GN/IRLS optimizer.
Use the identical v124 smoothed trial XY/heading RMSE loss, every original
integration timestep and every-tenth supported fitting sample. The only change
is replacing lambda*sum(delta_weights**2) with

    lambda_speed*sum(delta_weights[:,0]**2)
      + lambda_yaw*sum(delta_weights[:,1]**2).

All207 TRAIN recordings /12 people /15 No20 /314498 scored frames are mandatory.
No new features, identities, clocks, crops, calibration, masks or exclusions.
Fitting, priors and normalization exclude each fold's held participants.
Repeated development selection and the inherited266 parent training records
remain limitations. No held validation/test data informs this screen.

## Execution, acceptance and export

Before fitting, reproduce all207 saved v34, v121 and selected v124 motions,
trajectories, headings, reference/support arrays and primary metrics. Validate
all consumed input/source/output hashes; preserve older artifacts unchanged.
Keep a single process owner with research_run_guard.py and honor STOP.

Select the lowest equal-person mean trial XY ATE that improves v124 and passes
all original guards against ALL THREE controls v34/v121/v124: every participant
and maneuver ATE ratio and overall equal-person P95 position, last-supported
endpoint and heading ratio <=1.05. A zero control permits no increase. Retain
v124 if no new candidate qualifies. Save every candidate, rejection, fitting
history, full trajectory/support, historical/v74 metric and availability count.
No changes to the three configurations or criteria after scoring begins.

Synthetic checks must verify all34 objective-gradient columns including clipped
corrections for both asymmetric priors, exact scalar equivalence for (3,3),
monotone deterministic fitting and preservation of an exact prior. Independent
review checks source, exclusions, supports, metrics, guards and provenance.

If selected, fit once on all207 using the frozen full-TRAIN v121 prior and
normalization, seal a separate callable bundle, check all207 public sensor-only
predictions and optical/identity poisoning, then independently review/report.
The existing v121 public loader can use the unchanged readout representation.
Report paired participant uncertainty against v124 using the unchanged v122
4096-draw seed122 bootstrap and all4096 exact sign flips. These are descriptive
post-selection TRAIN statistics. Update README methodology and durable state.
New validation/test scoring, deployment, commit and push remain outside this
TRAIN protocol; no generalization or global-best claim follows from the screen.
