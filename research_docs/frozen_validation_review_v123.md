# v123 review closure and metric availability

14 October 2026. Both independent reviews passed:

- `research_state/v123_independent_review.json`: 153 output and 429 input hashes;
  71 paired records, 105,821 scored frames, exact historical baseline, core metric
  reconstruction and all decision guards. No inference rerun.
- `research_state/v123_report_review.json`: 1,704 grouped metric rows, input/output
  and report-source hashes, independent aggregation and availability counts.

The sealed evaluation's `review_status: pending` records its status when execution
finished. These separate review files record completion without modifying sealed
artifacts. The full results report's prospective review wording is superseded here.

The guarded matched result is **100.702119399 -> 99.303735166 mm XY ATE**. All 71
records/four participants contribute to the primary ATE decision. No.5, PS and SL
worsen slightly but remain within the predeclared 5% limits. This is conditional
development validation, not deployment promotion or a blind final evaluation.

| Relative trajectory error | v34 mm | v121 mm | Eligible recordings | Participants |
| --- | ---: | ---: | ---: | ---: |
| 1 second | 45.514455 | 43.920490 | 71/71 | 4/4 |
| 5 seconds | 99.371467 | 98.437431 | 39/71 | 4/4 |
| 10 seconds | 75.608374 | 71.561472 | 4/71 | 2/4 |

The durations describe different eligible subsets. In particular, the 10-second
result is not whole-cohort evidence. Means exclude unavailable trials and average
available participant means. These availability counts were checked independently;
the route/RTE calculation from trajectories was not independently reimplemented.

Genuine acquisition endpoint metrics are unavailable for all 71 recordings. The
reported endpoint guard uses the last supported frame, a distinct measurement.
The unchanged v74 evaluator retains the missing endpoint columns in trial tables;
the grouped table excludes columns with no numeric values.

The authorized evaluation and review milestone is complete. Do not rerun it or
retune from these validation outcomes. A separate protocol and independent timing,
firmware provenance and final-acquisition evidence are needed for stronger claims.
