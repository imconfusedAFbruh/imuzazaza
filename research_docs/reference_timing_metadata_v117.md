# Existing rejected-TRAIN reference timing metadata audit v117

11 October 2026. Hypothesis: C3D headers/parameters in the eight rejected TRAIN
recordings may contain synchronization event/channel or absolute capture metadata
not inspected by the earlier motion-event gates. This is a metadata audit, not
another peak/feature/lag search, firmware hunt or reference-mask modification.

Verify the sealed v113 cases hash, select exactly those eight IDs in the existing
inventory, assert TRAIN partition and immutable input file hashes before/after.
Use the installed ezc3d parser. It loads the C3D files; analysis examines only
header/parameter metadata, not point/analog sample arrays or localization outcomes.
Record parameter names, EVENT/TRIAL metadata, analog channel labels/units and
explicit DATE/TIME/CLOCK/SYNC/TRIGGER names. Preserve raw fields; frame origins
and relative event times are not automatically an independent IMU correspondence.
No automatic clock acceptance follows from finding a field or named channel.

Self-check JSON conversion of numpy values and metadata selection on synthetic
fixtures. No validation/test file access, training, gate change or promotion.
Write a fresh immutable output directory with input/source/protocol hashes.
