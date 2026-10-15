# Distributed clock evidence and event observability, v86-v90

Completed 9 October 2026. v86/v87 were already sealed when this session began;
their unfinished v88 verification was resumed without rerunning them. Three
substantive cycles in this session: v88, v89, v90. Preregistrations remain
unchanged in distributed_seedless_clock_v86_v88.md and
clock_observability_v89_v90.md. No separate-agent review was performed here.

## Results and decision

v86 independently generated twelve signal/event candidate basins in three of
ten investigated cases (the eight v84 rejects and two >250 ms discrepancies).
Twenty channels were retained, including every failed/weak channel. v87
compared thirty candidate pairs on identical derivative/sensor support:
sixty channel comparisons and 276 informative eight-second windows. Two cases
have distributed contrasts, but a contrast does not certify an accepted clock.
Ten of twelve v86 refinements hit their +/-25 ms search boundary.

For No.13 10x5 Trial3, fresh speed-proposed -0.825 s versus v84 +4.1517 s has
signed-yaw correlation 0.946575948 versus 0.664751708 and speed correlation
0.953976073 versus 0.293608727 on the same 1,669 derivative frames. Each channel
favors -0.825 s in all six informative windows, with no contrary windows.
This rejects the alias relative to the fresh alternative under the diagnostic
contrast; it does not establish independent absolute timing truth. -0.825 s
is at its local refinement boundary, so its exact lag remains unresolved.
The alias loses 458 frozen IMU-support frames, including twelve scored frames;
the fresh alternative loses zero. Do not conflate these two support counts.

No.7 CR1 has speed-proposed alternatives and distributed contrasts, but its
-1.725 s alternative has speed correlation only 0.521513 on the common pair
support and loses 101 frozen scored frames. Stronger relative evidence does
not meet the existing 0.6 correlation/unchanged-support requirements. Its yaw
events remain incompatible with the two-peak gate. No.19 OS1 has only one
informative window, zero speed peaks and no distributed contrast, so it stays
inconclusive. The two existing overlay figures were inspected: fragmented
repeated motion is visible for No.13; No.19 speed is broadly monotonic.

v88 verifies 1,066 parent artifact hashes and independently recomputes sixty
channel correlations and 276 window scores. Maximum difference is
8.881784197e-16. Known-lag, missing-bracket, one-peak exclusion, distributed
contrast and contrary-window/channel veto self-checks pass. These are numerical
checks in the same context, not a blinded external timing study.

v89 measures event observability over all twenty channels. The existing
chronological matching gate can change only when a pair enters/leaves the
200 ms tolerance. Enumerating those boundaries and intervening midpoints
over +/-5 s tests continuous-lag event feasibility without selecting a lag.

| Diagnosis | Channels | Evidence |
| --- | ---: | --- |
| Too few peaks | 10 | One channel has fewer than two existing events |
| Insufficient motion | 4 | Raw reference yaw spread below the frozen gate |
| Incompatible event timing | 2 | At most one chronological match at any allowed lag |
| Feasible events, candidates present | 4 | Existing candidates already cover these channels |

The two incompatible channels are signed yaw in No.15 AR3 and No.7 CR1.
Both have two IMU and two reference peaks but maximum matching count one.
No eligible multiple-peak channel has an empty coarse search despite feasible
events. Thus denser binning alone cannot rescue the seven candidate-empty cases
under these fixed feature/peak definitions. This does not prove other event
definitions or clock methods impossible, and it does not certify event identity.

Short (<20-frame) derivative runs remove 184 **channel-frames** across both
channels, corresponding to 92 shared temporal frames: No.4 PS1 eighteen and
No.13 10x5 T3 seventy-four. All other investigated channels lose zero frames
at this feature-smoothing stage. No.4 CR3 retains all 845 derivative frames
in five observed runs (longest 2.70 s), but has zero yaw peaks. No.19 AR1 has
only one peak per observed channel across four runs. Low-motion OS cases have
single continuous observed runs, so optical fragmentation alone does not
explain their failure. Boundaries are never invented as matching events.

v90 verifies 853 hashes, independently reconstructs full-sensor/reference
filtering and every saved peak list, and reproduces run accounting exactly.
Twenty dynamic-programming event maxima agree with the chronological matcher;
maximum feature difference is zero. Synthetic shifted, incompatible spacing,
empty-event, short-run and closed-tolerance-boundary cases pass. All 207 records
and fifteen No.20 recordings remain represented; accepted/rejected clocks remain
199/8. No geometry, support, initial pose, dataset or gate was changed.

## Preserved failures and process recovery

The inherited v88 ACTIVE_RUN.json named PID23684 with its creation/command.
Windows process lookup found no such process; the lock was preserved as
research_state/INTERRUPTED_RUN_v88.json before guarded continuation. It was
not overridden by age. Subsequent guarded jobs finished and released the lock.

v89's first attempt finished calculations/CSV writes but JSON rejected a NumPy
int64 short-run count. The attempt remains in
outputs_clock_observability_v89_serialization_attempt. Native Python integer
conversion at the run-accounting boundary and a JSON self-check fixed the
problem; corrected results were written to a new directory. No parent output
was overwritten, no numerical gate was adjusted.

## Reproduction and next task

Completed outputs are immutable. Inspect run.json, CSV tables and manifests in
outputs_distributed_clock_candidates_v86, outputs_distributed_clock_evidence_v87,
outputs_distributed_clock_review_v88, outputs_clock_observability_v89 and
outputs_clock_observability_review_v90. Do not rerun their main commands into
these directories. Synthetic checks may be run without producing new outputs:
`python -c "from clock_observability_v89 import check; check()"`.

All new trajectory metrics are unavailable because no predictions were made.
Historical v34 remains 100.702119399 mm synchronized ATE and 49.726226563 mm
route on 71 previously exposed validation recordings. v81 TRAIN207 simple
native/new remains 147.565311 mm on a different evaluation scope. No new
validation/test data was read, no estimator promoted and no commit/push made.
Inherited geometry/QC/acceptance, offline filtering, reference/front ambiguity
and exact acquisition provenance remain limitations.

Next: preregister one bounded basin-completeness audit on the twelve already
fresh-generated basins, preserving gates and fixed common derivative support.
Determine whether an independently prescribed local interval can contain an
interior optimum; report overlapping basins, event identity, all frozen support
loss and unresolved boundaries. Never pick the interval by ATE or inherited
clock agreement. Do not claim this resolves the seven peak-poor/weak cases.
If it does not produce complete clock coverage, finish the separate
reference-scoring-versus-training-geometry policy audit, preserving all No.20
records. Do not repeat event counts, bootstrap fits or completed model searches.
