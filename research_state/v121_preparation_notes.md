# v121 preparation and derivative review

Two pre-fit initialization failures preserved separately:
outputs_reservoir_path_v121_initialization_failure (old calibration folder has no
manifest), outputs_reservoir_path_v121_provenance_key_failure (Windows backslash
provenance key). Final source verifies the calibration hash from sealed v16 run
after normalizing path separators; no hash check bypassed. No candidate fit or
scores occurred before these fixes. Final source/protocol sealed in current output.

Protocol intercept wording corrected before numerical fits: actual intercept is
appended after16states, not prepended. Equivalent permutation under isotropicridge.
Independent reviewer checked all34 Jacobian columns with symmetric differences,
irregular timestamps, lateral motion and saturation; maximum discrepancy9.04e-10.
No mathematical defect found; final support/artifact/eligibility review pending.

Current run reproduced all207 frozen v34 baseline score/count pairs before fits.
