# Broad maneuver minima: provenance and whole-model tradeoffs v116

Completed guarded job exits0. All seven previously reported maneuver scores
reproduce from sealed trial summaries within1e-9 mm. Every candidate has the
same71 recording IDs and matching person/maneuver labels; all read CSV hashes
match their respective parent manifests. Different scored-frame counts persist.
Equal counts for AR/CR do not by themselves establish equal clocks/masks/poses.

| Maneuver | Broad minimum (mm) | Winning model overall (mm) | Maneuver trials with different frame counts versus retained v34 |
| --- | ---: | ---: | ---: |
| 10x5 | 136.055073 | 94.661740 | 12/12 |
| AR | 73.259161 | 142.175376 | 0/12 |
| CR | 48.787164 | 116.878910 | 0/12 |
| OS | 40.141807 | 233.620690 | 2/3 |
| PS | 166.176760 | 96.172432 | 7/8 |
| SL | 103.611161 | 96.329130 | 3/12 |
| ST | 56.651394 | 94.834759 | 1/12 |

AR's best seed is not the training-preselected deployment seed. The CR winner
is a training-selected candidate with worse overall historical validation error.
OS's low score comes from only three trials/two people and a model with233.62 mm
overall error, on different support from retained v34. These facts qualify the
requested cherry-picked table; they do not invalidate its literal recorded values.

Do not combine the seven minima into a claimed overall estimator score.
v115 separately calculates an outcome-informed selector for SIX already-audited
common-native v42 models, yielding94.462747 mm; that is a different candidate set.
No selector was trained/deployed, no new prediction or test evaluation occurred.
No promotion. Independent review passed: both output hashes,15 input hashes
against parent manifests, source/helper/protocol hashes, all seven scores,
71-recording identity sets, method filtering and frame-count differences agree.

Follow-up artifact inventory: the winning outputs_long_horizon_v9 manifest has
no saved NPZ arrays; outputs_nonlinear_endpoint_tuning_v22 contains only fold/full
normal-system NPZs, not trajectories. These winning folders alone cannot certify
AR/CR exact reference masks/time/initial poses or support a trajectory-level
switching comparison. Do not regenerate missing candidate predictions merely to
chase the retrospective minima. Equal-count evidence remains qualified.
