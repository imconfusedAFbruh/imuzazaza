# Retained aggregate uncertainty v114

Preregistered9October2026. Publication reporting task, not model development.
Read ONLY original_v21_participants.csv/selected_blend_participants.csv/run.json
from sealed outputs_dynamic_blend_v34, after verifying their manifest hashes.
No validation recordings, predictions, trial signals or held test reads. This is
new retrospective statistical analysis of already exposed aggregate validation
results; do not call it untouched validation or tune any model from it.

Verify four identical participants and counts sum71, reproduce frozen equal-person
headline summaries. Report signed paired benefit old-minus-new, absolute and
relative means, each participant, and leave-one-participant-out mean benefits.
Enumerate all4^4=256 ordered participant resamples, resampling paired participant
means together. Report percentile2.5/97.5bounds with linear quantiles as an
empirical sensitivity interval, not a precise population confidence guarantee.
This weights people equally; it is not pooled frames or independent trial sampling.

Enumerate all2^4=16 sign flips on paired effects. Two-sided tail uses absolute
mean >=observed absolute mean, tolerance1e-12m. Report exact conditional p only
under independent participant/symmetric-effect null assumptions. Four people,
prior validation exposure/inherited calibration and model selection prevent a
prospective significance/outperformance claim; no multiple-model testing is
performed. If interval includes zero or p>=.05, explicitly preserve that finding.

Self-check identical pairs givezeroeffect/zerointerval/p1, equalpositive effects
yieldpairedmeanconstant and two-sidedp.125 forfourpeople. Reconstruct means with
standard-library arithmetic; statistical enumerations are deterministic, not
additional stochastic model seeds. No new experiment family, model evaluation,
trajectory/refit/promotion or remote push. Completed outputs immutable.
