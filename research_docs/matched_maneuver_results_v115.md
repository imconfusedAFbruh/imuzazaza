# Same-support maneuver switching result v115

Completed 10 October 2026; guarded execution exit0. Synthetic unequal-person
weighting/switching checks pass. Five input hashes verified; all426 trial rows
contain six identical sets of71 IDs, person/maneuver labels and valid-frame
counts. Existing v77 source audit supplies the common-mask/initial-pose proof;
v115 does not reread trajectory arrays. All maneuver and overall scores reproduce
the sealed summaries within1e-9 mm.

Within these SIX common-native v42 candidates, retrospective winners are:

| Maneuver | Winner | XY ATE (mm) |
| --- | --- | ---: |
| 10x5 | new-clock refit blend | 136.055073 |
| AR | old-clock blend | 87.926007 |
| CR | new-clock frozen blend | 55.101099 |
| OS | new-clock refit blend | 88.460615 |
| PS | new-clock refit blend | 170.909772 |
| SL | new-clock refit blend | 106.610325 |
| ST | new-clock refit blend | 56.900539 |

Reconstructing participant means across their original trial counts gives
94.462747445 mm for the outcome-informed maneuver selector versus94.661739566 mm
for the fixed new-clock refit blend: only0.198992121 mm additional benefit.
Do not average the seven maneuver means to obtain the benchmark score.
The fixed old-clock blend is100.592598441 mm on this same support.

This is retrospective arithmetic, not a trained selector or prospective gain.
The user-requested broad historical minima remain in the original CSV with
different clock/support and rejected-candidate qualifications. No promotion,
test access, raw/prediction reads, new model fitting or parameter search occurred.
The all207 clock gate, participant robustness and inherited-fit limitations
remain. Independent review of v115 passed: all three artifact hashes, five input
hashes, protocol/script hashes,426 rows,71-recording sets, winners and arithmetic
reproduce. AR's old-blend margin over frozen new-clock blend is only0.0000701943 mm,
so that ordering has no practical interpretation.
