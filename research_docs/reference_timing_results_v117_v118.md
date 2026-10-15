# Independent timing evidence check v117-v118

11 October 2026. Both guarded audits complete/exit0 and independently reviewed.
The eight rejected TRAIN IDs remain unchanged. Hashes of eight C3Ds, eight IMU
CSVs, inventory, metadata parents, output artifacts, protocols and executed
sources were verified. No clocks, reference masks, splits or predictions changed.

All eight C3D headers contain18 blank zero-time event slots, not meaningful named
events. No EVENT/TRIAL parameter groups or explicitly sync/trigger/clock-named
analog channels were found. The12 analog labels describe two sets of force and
moment channels with N/Nmm units at1000Hz. No analog samples were analyzed;
unlabeled pulses are not ruled out. Point headers use first frame0, while crop
metadata uses start1/end equal to uncropped frame count: index conventions do
not establish an IMU alignment or justify adding10ms to a frozen clock.

Processing Creation date/time fields exist, but capture semantics, timezone and
shared-clock provenance are unverified. IMU first-row fields include session_id,
device microseconds and PC-monotonic nanoseconds; no verified wall-clock epoch
conversion or common QTM event accompanies them. No independent mapping was
established. This is not physical unobservability or proof none exists elsewhere.

v117 ezc3d loads reference file arrays, but analysis uses only headers/parameters;
v118 inspects only first-row timing fields. No optical/IMU/analog waveform analysis,
motion-event search, localization scoring, fitting, validation or test access.
Initial v117 Header-wrapper serialization failed before output creation; original
source and failed LAST_RUN preserved in research_state/v117_header_attempt. The
fix converts the wrapper to a dictionary; fresh execution and review pass.

Decision: this new evidence route does not unlock the strict all207 refit gate.
Do not convert creation strings or blank slots into timing truth, fabricate a
force-channel trigger, infer clock offsets from relative epochs, or repeat failed
IMU-only feature searches. Retained v34 remains100.702119399mm under its original
evaluation. Further model fitting needs verified independent existing timing
evidence or an explicit exception to the approved all207-before-fitting contract.
