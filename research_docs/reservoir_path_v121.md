# v121 nonlinear temporal residual on retained v34 — preregistration

User explicitly requests a new model beating all attempted models. Renewed TRAIN
development is authorized; no guarantee of success, altered metric, test exposure
or validation promotion. Benchmark the strong retained v34 fold model on its exact
frozen old-clock support. Reproduce all207 scores and132.24020010362922mm aggregate.
Historical inherited266 other training IDs remain ONLY inside frozen parent fits;
new residual fits use207 identified TRAIN/12people, all15No20, same three folds.

Hypothesis: nonlinear temporal state captures motion-dependent accumulated error
that fixed temporal products/EMA models miss. Frozen random recurrent state16,
seed121, recurrent spectral radius.9, input gain.2, leaky update.2, tanh activation.
Inputs are the central15 existing v14 gravity-rotation features (columns30:45),
normalized on fitting people only with std floor1e-5 and clipped[-5,5]. Recurrent
input matrix N(0,1)/sqrt15; recurrent N(0,1)/sqrt16 rescaled to spectral radius.9.
State resets at invalid IMU frames; append intercept after state16. No maneuver,
participant identity or optical values supplied to the prediction function.

Learn forward/yaw readout jointly around frozen v34 motion. Corrections
clip(state@weights,-1,1)*[.05m/s,.02rad/s]; lateral stays frozen. Initial weights0.
Exact trajectory integration, eight GaussNewton steps with analytic Jacobian;
line search steps1,.5,.25,0 on fitting objective only. Three ridge penalties
lambda.1,1,10; intercept regularized too. Objective equal-person/equal-trial mean
of XY squared error/(.1m)^2 +.1*wrapped-heading squared error/(.1rad)^2,
pluslambda*sum(weights^2). Observe every tenth supported sample, but integrate
every native timestep. No downsampled motion integration or pose resets.

Before candidate scoring reproduce all baseline scores/counts. Acceptance lower
ATE and every person/maneuver ATE<=1.05 times v34; equal-person P95position,
last-supported endpoint and heading<=1.05; exact207 support/no omissions. All
v74 supplementary metrics retained. Baseline eligible. Compare additionally to
v33's131.460088mm rejected model, without presenting incomparable score sets as
beaten. Save every fold model and all held predictions/checkpoint each fold.

Test analytic trajectory Jacobian against finite differences including clipping
and nonzero lateral motion; check recurrence reset/determinism and zero correction.
Independent review required. New architecture/loss is a hypothesis, not a novelty,
state-of-the-art or publication claim. No validation/test scoring or push.

Before numeric fitting: initial preparation failed on an absent v2 manifest.
Preserved failed source/log; calibration now verified against v16 parent run's
recorded provenance hash. Reviewer also identified append/prepend wording:
intercept is appended, an equivalent feature permutation under isotropic ridge.
Corrected wording before any candidate fit; no hypothesis or hyperparameter change.
