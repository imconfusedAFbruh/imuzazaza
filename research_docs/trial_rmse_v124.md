# v124: trial-RMSE readout anchored to v121

Preregistered 15 October 2026 before new fitting or candidate scoring. User's
direct requests, "Review understand the currently best model And make a better
one" and "I want best model possible", renew TRAIN development authority.
This is a bounded continuation of the inherited-clock research track. It does
not resolve the strict timing/acquisition gate or reopen the completed v123
validation comparison.

## Question and fixed comparison

v121 minimizes mean squared XY/heading error; selection averages trial XY RMSE
equally within each participant. Squared loss can overemphasize high-error
trials. Test a smoothed trial-RMSE objective with a quadratic prior centered on
the selected v121 weights. Reuse v121's fixed 16-state reservoir, fit-only
normalization, seed121, caps .05 m/s and .02 rad/s, unchanged v34 motion, all
207 TRAIN IDs / 12 people / all15 No20, and the original three participant folds.
No new features, clocks, calibration, crop, mask, maneuver or identity inputs.

Three and only three prior penalties: .1, 1, 10. Initialize each readout at the
same fold's frozen v121 penalty10 weights. For fitting recordings only, minimize
the equal-participant/equal-trial mean of

    2*sqrt(mean(||XY_error/.1m||^2)+.01^2)
      + .2*sqrt(mean((wrapped_heading_error/.1rad)^2)+.01^2)

plus lambda*sum((weights-v121_weights)^2). Integrate every original timestep;
observe the same every-tenth supported samples as v121. Twelve GaussNewton/IRLS
steps, fitting-only first-improving line search 1,.5,.25,.125,0. Stop early only
on an exactly zero accepted step. No held-person labels enter fitting, loss
weights, prior weights or normalization. Existing parent dependence on 266 other
training records and prior development selection remain disclosed.

Reporting also retains all participant benefits, the range after omitting each
one participant, and descriptive paired uncertainty using the existing v122
routine (4096 participant bootstrap draws, seed122; all4096 exact sign flips).
These are conditional post-selection TRAIN summaries and cannot establish
independent significance. They do not change candidate selection.

## Execution and checks

First verify all prepared TRAIN artifact hashes, exact fold exclusions and
v121's saved fitting IDs. Reproduce both v34 and selected v121 motions,
trajectories, masks and primary metrics on all207 before fitting any candidate.
Keep exact support; finite failure is a failure, never a dropped record. Save
all paired predictions, primary and v74 supplementary trial metrics, source and
input hashes, per-fold coefficients, fit histories and progress checkpoints.
Use the existing exclusive research_run_guard.py. Honor STOP before each phase.

Synthetic checks: numerical objective gradient for all34 readout parameters,
constant/near-zero residuals, finite clipped corrections, deterministic fitting,
monotone fitting loss and unchanged zero/prior prediction. Reuse the v121
trajectory-Jacobian self-check. Independent review checks source, fit exclusion,
all paired support and core metric/guard arithmetic after screening.

## Selection, export and boundary

Select the lowest equal-participant mean XY ATE that improves v121 and passes
every original guard against BOTH v121 and v34: each participant/maneuver ATE,
equal-participant trial P95 position, last-supported endpoint and heading each
at most1.05 times its control. Zero baseline permits no increase. Unchanged
v121 remains eligible. Do not substitute another loss, penalty, feature or gate
after scoring this screen.

If a candidate passes, fit its selected penalty once on all207 using the frozen
full-TRAIN v121 normalization/prior and full v34 parent. Seal a new separate
bundle, reproduce sensor-only inference on all207, test optical/identity-field
poisoning, and independently review it. These reproductions are not held-out
accuracy. Preserve existing model/code/artifacts unchanged. Report all outcomes
in state and README. New validation/test evaluation, deployment, commit and push
are outside this protocol. A new model's generalization remains unestablished.
