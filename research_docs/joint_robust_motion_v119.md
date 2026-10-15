# Authorized TRAIN-only joint robust motion residual v119

11 October 2026, before numerical candidate execution. User explicitly approved
one additional family/max3 configurations in proposed_train_only_exception_2026-10-11.md.
This consumes that ONE additional family. Original strict timing track remains gated.

Hypothesis: fitting forward/yaw corrections with one shared two-component robust
sample weight reduces inconsistent large derivative-residual influence, improving
motion without sacrificing slopes. Existing scalar calibration already uses Huber;
this hypothesis changes only a joint downstream residual objective, not calibration.
It differs from v56/v60 speed-only least-squares fits and v35 joint planar fitting:
lateral remains zero, existing IMU-only causal hysteresis feature bank is unchanged,
and robust forward/yaw weights are shared. No new features, architectures or gates.

Use all207 identified TRAIN recordings/12people/all15 No20 and existing three
participant folds. Existing v42 cache choice/fallbacks, masks, initial poses and
v52 fold calibration/projected-yaw models are frozen. Baseline is v52 weight1:
147.74650809690637mm equal-person ATE. Reproduce its trial scores/counts before
candidate scoring. No unknown legacy training, validation/test reads or scoring.

Feature bank: braking_hysteresis_folds_v56.hysteresis_features, unchanged. Fit on
existing label-valid IMU samples decimated by5; existing training_group balancing.
TRAIN-fitting-only feature mean/std, target residual MAD scales with floors .005
in native m/s and rad/s. Ridge alpha1, intercept unregularized. Initialize from
scaled-target ridge; eight IRLS updates with shared Euclidean standardized residual
norm and weight min(1,delta/max(norm,1e-12)); normalize weighted mass each update.
Three configurations ONLY delta{1.5,3,6}; no gain/iteration/feature search.
Fixed inference gain .25, component correction caps .1m/s and .05rad/s before
gain, invalid-IMU corrections zero. All fitted normalization/scales/coefficients
exclude held people; caps/deltas fixed in advance. No calibration refit.

Acceptance: exact same scored support on every trial; no missing trial may be
dropped. Overall equal-person ATE must decrease; all12 participant and every
maneuver ATE ratios <=1.05; overall equal-person trial P95 position, last-supported
endpoint and heading RMSE ratios <=1.05. Baseline eligible. Any unsupported/failed
trial makes candidate ineligible and remains documented, with no fabricated score.
Report velocity/yaw-rate label RMSE descriptively; do not select on them. No
genuine-acquisition endpoint claim. Persist held TRAIN motion/position/heading and
per-trial/person/maneuver tables so later audits do not need prediction regeneration.

Self-check shared weights, finite coefficients, constant/zero targets, and suppression
of a synthetic outlier against ridge. Verify source/parent manifests and fit IDs.
Checkpoint after each fold. After3 configs stop numerical search and independently
review all outcomes. No validation evaluation or promotion, even if TRAIN passes.
