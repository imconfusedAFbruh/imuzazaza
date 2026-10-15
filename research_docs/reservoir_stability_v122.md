# v122: descriptive stability of the frozen v121 TRAIN gain

Before calculation: use only sealed v121 lambda0/lambda10 participant summaries
and run.json. No predictions, raw data, new fitting, model selection, or validation
and test reads. Keep all12 participants and207 recordings, equal-person weighting.

Question: does the selected model's mean benefit survive omission of any one
participant? Report all paired benefits and all12 leave-one-person-out means.
Also report a descriptive percentile interval from4096 paired participant
bootstrap resamples, seed122, and all4096 exact sign flips of paired benefits.
Use a two-sided absolute-mean statistic with inclusive equality for sign flips.

These are conditional, post-selection TRAIN diagnostics. Folds share training
data and the winner was selected on these participants; neither the interval nor
the sign-flip fraction establishes independent generalization or significance.
No acceptance threshold, retuning, promotion, or new candidate follows from this
audit. Preserve inputs and save source/protocol/input/output hashes in a new folder.
