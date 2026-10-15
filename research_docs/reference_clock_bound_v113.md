# Fixed-reference clock-gate upper bound v113

Preregistered9October2026. v108/v109 confirms changing the existing IMU feature
does not change any of eight rejection diagnostics. Next decision: is more IMU
feature search capable of satisfying the all207gate while reference channels,
motion eligibility and event definitions remain frozen?

Use ONLY sealed v86candidate metadata and v84acceptanceIDs; no raw/ref reads,
filtering, peak reconstruction, lag search or fitting. Existing reviewed v89/
v90 already verifies event definitions/counts. For each rejectedID, a reference
channel is potentially usable only if motion_eligible and reference_peaks>=the
existing minimum. If neither channel qualifies, changing IMU features alone
cannot provide the required matches. Count such cases and derive207minuscount
as a permissive upper bound, not achieved acceptance or timing observability.

Verify input hashes, unique two channels/eightIDs and all207baseline IDs. Test
the logical bound on syntheticmetadata before recording results. No gate change,
new events, reference changes, dropping records, inherited clock fallback or
accepted-subset estimator fitting. This audit synthesizes established metadata;
do not repeat v89/v90 numerical work or manufacture a new empirical experiment.
If the bound is below207, stop further IMU-only feature attempts for gate recovery
and redirect to independent timing evidence or other authorized campaign work.
