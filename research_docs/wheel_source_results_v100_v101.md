# Verified source compatibility and synthetic checks, v100-v101

Completed 9 October 2026. The31-page2026 primary PDF and rendered method pages
are sealed in outputs_wheel_sources_v100. WISDOM's accepted manuscript is read
through the browser only: local retrieval and browser screenshots failed.
Its equation typography is therefore extraction-level, not visually certified.

The2026 article has three IMUs but uses GPS/seat-mat urban-route analysis and
external300m distance calibration. That calibration cannot silently replace the
local training-only contract, and its results cannot rank against local XY ATE.
Fuss's delegated method is identified as DOI10.1080/19346182.2012.754895; an
author-uploaded full-text copy is accessible through ResearchGate, but formula
extraction there is incomplete. Full wheel-kinematic reproduction remains open.

WISDOM's extracted kinematic equations pass216 synthetic camber/side/phase/rate
cases: maximum gyro recovery error2.220446049250313e-16. Four curvature cases
agree with radius calculated from wheel distances within1e-12. A source affine
clock equation maps both endpoints and the interior point exactly at reported
precision; coincident slave triggers are explicitly rejected. Synthetic known
yaw sign is supplied, so this is not a test of accelerometer sign reliability.

The first radius test failed because the agent incorrectly retained a wheel
radius factor after algebraic cancellation. The failed script and original
preregistration are preserved in outputs_wheel_source_checks_v101_attempt.
The final result falsifies that suspected source inconsistency. The immutable
v100run.json's provisional suspicion is superseded, not erased. No source typo
or new trajectory correction is claimed.

Command: Python313 research_run_guard.py wheel_source_checks_v101.py.
Final output: outputs_wheel_source_checks_v101/run.json and manifest.json.
These are source/synthetic checks, with zero recording reads and predictions.
No validation/test, fitting, model-family search, clock change, promotion or push.
Bestv34 stays100.702119399mmATE/49.726226563mmroute on71exposed validation trials.

Next useful independent task is pinned official Wheel-INS implementation audit,
including initialization, rate, mounting, gap handling and actual multi-IMU
capability. Source compatibility cannot bypass199/207clock coverage or permit
guessing physical inputs. See wheel_source_consistency_v100_v101.md for the
protocol and source URLs; see skid_source_domain_results_v97_v99.md for the
earlier conditional formula-domain results and their supervised-bias limitation.
