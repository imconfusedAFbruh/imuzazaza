# Reviewed mobility sources and code limits, v106-v107

9 October 2026. Both papers, rendered methods pages and the MASSWU S1
supplement are sealed in outputs_mobility_sources_v106. The static assertions
are sealed in outputs_masswu_code_audit_v107. Separate read-only reviewer
review_v94_v95 verified every manifest entry and parent/code/protocol hash.
The original preregistration remains unchanged.

DeVries et al. (2023) require participant-specific quiet level and straight
travel calibration. Their timing procedure also requires rigid-beam rotations
before and after recording, cross-correlation and visual assessment; reported
alignment is 10–20 ms. Wheel distance during turns is not midpoint path length.
Velocity RMS 0.02 m/s and distance/turn agreement are not optical XY ATE.

MASSWU (2025) validates task outcomes with mixed Pearson/Spearman statistics
and rater analyses; do not label all coefficients Pearson or ICC. The source
prose supplies an EMA, radius conversion, integration and quiet/onset rule,
but published S1 snippets do not implement these processing steps. The formula
v = gz * radius requires radians/s; supplied float-read/transmission snippets
do not establish the conversion used by absent processing code.

S1 queues a 16-bit millis value while six readings remain shared globals.
The transmitted six-axis values are not a frozen sample associated with the
queued time, and that time is not transmitted. This is a static snippet-level
coherence limitation, not observed deployed corruption. Missing headers,
build/tick configuration and host processing prevent faithful reproduction.
Matching MCU/IMU models establish no firmware or recording identity.

The initial v107 format-count assertion counted a commented alternative sprintf
and failed (12 occurrences). Its failure is preserved in
outputs_masswu_code_audit_v107_attempt/failure.json. Excluding full-line comments
correctly establishes six active transmitted fields; completed artifacts were
created only after correction. No third-party code was built or executed.

A precise distinctive-code search of the acquisition repository's current
hardware source and its hardware_firmware history found no matching queued-time
statement. This limited negative result is not an exhaustive provenance claim.
Unavailable host/build evidence remains unknown; do not repeat broad old hunts.

Neither paper has been reproduced locally or supplies a comparable XY ATE
victory. No recordings, predictions, validation/test outcomes or model selection
were used. Next highest-value empirical work is a preregistered existing-feature
clock diagnostic, preserving all 207 TRAIN recordings and unchanged gates.
