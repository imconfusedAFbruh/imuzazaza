# Conservative robust motion model v120 — preregistration

11 October2026. User requested “create the new best model” after the completed
v119 screen. This authorizes renewed model development; earlier exhausted
one-family budget is historical. Keep frozen data/clocks/support and TRAIN-only
development; no reserved test, validation scoring, push or deployment in this run.

Hypothesis: v119 delta3 corrections are directionally useful across six maneuvers,
but fixedgain.25 is too large on ST. Fixed global shrinkage can retain an overall
gain while passing every original guard, without supplying maneuver labels.
Earlier v58/v60/v62 speed corrections showed the same ST sensitivity. This is
explicit follow-up shrinkage of existing robust fits, not a new objective claim.

Freeze v119 delta3 (lowest TRAIN overall error of that completed family), its
fold models, caps and features. Exactly three gains: .05,.075,.10. No new fits,
feature/gate search, refit clocks or support edits. Compare with v119 delta0
(v52) on all207 TRAIN recordings/12people/all15 No20. Use saved held motions:
candidate = baseline + (gain/.25)*(saved delta3 motion - baseline).
Integrate with identical initial optical pose and support; no resets or alignment.

Every candidate must reduce equal-person ATE and keep every participant/maneuver
ATE ratio <=1.05, overall equal-person P95position/last-supportedendpoint/heading
ratios <=1.05, exact same pertrial support/count and no missing records. Baseline
eligible. Preserve all extended v74 metrics, motion/position/heading arrays, and
pertrial/person/maneuver summaries. Checkpoint after each participant fold.

Synthetic check gain0 reproduces baseline and gain.25 saved delta3; coefficients
immutable. Verify source/parent/output hashes and independently review outcomes.
If a candidate passes, export its exact inference specification and use it as
the new accepted TRAIN development model, not a claim to beat retained v34's
different validation evaluation. No validation or deployment promotion.
