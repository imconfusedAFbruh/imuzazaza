# Existing-data competition: local execution checkpoint

The user's pasted instructions adopt the attached competition plan. The plan is saved verbatim in existing_data_competition_plan_2026-10-08.md. Latest constraints supersede prior unlimited searching: use a bounded preregistered budget, preserve acquisitions, no remote push, no new data/hardware dependency.

## Completed before adoption

Current workspace and six continuation files inspected. Firmware/raw conversion and timestamp checks reused, not restarted. v59 independently reproduced 621 fold predictions with differences below 2.23e-16. This reproduces those fold controls; retained v34 and v42 headline predictions still need their own reproduction under original definitions before a new competition claim.

v58/v60/v61 rejected. v62 and v64 finished: no candidate passes slope robustness. v63 diagnostic finished. v65 inventories the supplied historical folder. No protected-test or new validation selection in these experiments.

## v62/v64 outcome

Control: 147.746508 mm synchronized XY, 60.521354 mm route RMSE on 207 identified TRAIN recordings/12 people. Removing center acceleration yields 144.089421 mm at gain .25, but ST worsens 37.78%. Dynamic gravity gives 143.105848 mm but ST worsens 32.39%. Wheel products give 142.916684 mm at .25, ST worsens 32.11%; .5 gives 142.051218 mm, ST worsens 67.50%. Direction-aware slowing gives 144.324897 mm, ST worsens 38.27%. Reject all; historical retained result unchanged. Gain .5 and alternative feature variants are recorded in original run.json files, not hidden.

## v63 interpretation

Training-only, non-deployable derivative replacements: baseline 147.746508 mm, reference speed 112.241046 mm, reference yaw rate 151.681793 mm, all three components 116.548570 mm. This substitutes reference yaw RATE, not absolute heading: the requested absolute-heading counterfactual remains unfinished. Reference replacement covers about 74.8% of IMU samples overall and 44.9% in 10x5. Gap/boundary fallback remains predictive. Exact all-component MSE reduction is negative despite improved mean trial RMSE: long-trial regressions expose the averaging difference. Do not interpret Shapley credits as an additive physical error budget or oracle floor. The inability of derivative truth to close the path warrants reference-derivative/integration/support investigation before more model search.

## New competition gates / budget

No new architecture family starts until retained controls, strict provenance, common-support contract and competitor source matrix are resolved. Unknown legacy identities excluded from strict track including pretraining. Current folds refit simple calibration/yaw/speed fits but inherit clocks/QC/reference preprocessing; this is retrospective and not complete full-pipeline independence.

Reserve at most eight new hypothesis families, each at most three declared configurations: (1) reference derivative/integration repair; (2) full original-versus-arbitrated-clock refit; (3) physical rolling baseline; (4) faithful skid-correction baseline; (5) Wheel-INS adaptation; (6) linear interval motion residual; (7) compact TCN only if linear residual warrants it; (8) masked legacy learning only if provenance permits. Document exact configurations before fitting; unimplemented families are reservations, not results. Covariance/fusion replaces a reserved family only with a logged justification. Stochastic finalists require three seeds; deterministic repeat runs do not create independent evidence.

Keep frozen 5% participant guard. Tail/endpoint/maneuver tolerances must be preregistered before NEW candidate scores; existing 1.05 maneuver checks are exploratory safeguards, not a retrospectively independent preregistration. No promised 20%, 50 mm or publication victory.

## Boundary map

pipeline.py: acquisition/conversion, calibration, motion helpers and evaluation. clock_refit_experiment_v38.load_cache: hashed immutable reference/time mappings. trajectory_calibration_v10.integrate: one initial pose and continuous integration. research_metrics_v59: observed-support route/synchronized metrics. train_error_budget_v63: separate diagnostic-only oracle, never an inference dependency. Inventory does not modify training or reference paths.

Parallel agent turns ended with workspace-out-of-credits errors. Their launched numeric jobs nevertheless finished and produced run.json/manifests. Save completed evidence; do not respawn or rerun finished jobs blindly.
