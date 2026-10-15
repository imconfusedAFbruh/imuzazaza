# Timing correspondence feasibility v118

11 October 2026. Following v117, determine whether its metadata supplies an
independent correspondence to native IMU timing. Read only sealed v117 metadata,
inventory and the first CSV row/header of the eight rejected TRAIN acquisitions.
Hash input files before/after; do not analyze IMU samples, optical trajectories,
analog waveforms, motion peaks or localization outcomes.

Count only named header events as named events; eighteen empty zero-time slots
are not synchronization anchors. Record analog labels mentioning sync/trigger/
clock (no unlabeled hidden-pulse exclusion claim). Record C3D crop/creation fields
and first-row device/PC-monotonic/session identifiers. No absolute mapping is
inferred from numeric proximity, creation-time strings, frame0 or unknown epochs.

Acceptance: a clock correspondence requires identified common event or established
epoch conversion with recording linkage. Metadata presence alone cannot pass.
No such mapping is implemented in this descriptive audit. Test blank/named event
and channel classifications on synthetic inputs. No fitting, gate relaxation,
new-clock acceptance, reserved evaluation access or promotion.
