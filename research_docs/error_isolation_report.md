# Reference closure and error cancellation: v66-v69

8 October 2026. Existing data only; no model fitting, test access or candidate promotion.

## Hypothesis and locked experiment

The large v63 all-reference-derivative residual could be a faulty integrator or incompatible reference derivatives. Family1 reserves three diagnostics: consistent XY derivative local closure; cached body derivative local closure; absolute observed heading with predicted velocity. No parameter search. Controls use the identical frozen v52 motion, original initial pose, clocks and reference support on 207 identified TRAIN recordings/12 participants. Reference oracles are separate diagnostic programs and cannot be imported as inference inputs.

## v66: closure is accurate inside labelled runs

1,091 derivative-labelled runs, total2,423.29s. Each run is independently anchored solely for numerical reference closure, not continuous localization:

| Diagnostic | Frame-weighted local RMSE | P95 local endpoint | Maximum local endpoint |
|---|---:|---:|---:|
| Consistent sampled-XY gradient | 0.063013 mm | approximately0 | approximately0 |
| Cached forward/lateral derivative, observed absolute heading | 0.410798 mm | 0.850529 mm | 2.277767 mm |

**Decision:** reject the large within-labelled-run integration-error hypothesis. These local numerical errors are not reference uncertainty and are not IMU accuracy. They do not test unobserved intervals, full native timing correctness or physical-front semantics.

## v66: absolute-heading diagnostic

Continuous position, no position resets. Reference heading is supplied on observed support; predicted heading remains through missing-reference intervals. All414 metric rows have identical common supported-frame counts. Scores are equal-participant means of per-trial metrics, not pooled frames.

| Metric | Frozen TRAIN control | Absolute-heading oracle |
|---|---:|---:|
| XY RMSE | 147.746508 mm | 164.087198 mm |
| Position MAE | 127.602355 mm | 140.825109 mm |
| Position P95 | 241.848061 mm | 269.643616 mm |
| Route RMSE | 60.521354 mm | 65.235801 mm |
| Route P95 | 119.404180 mm | 132.905033 mm |
| Supported-run maximum discrete Frechet | 257.007912 mm | 268.739362 mm |
| Last-supported endpoint | 193.852803 mm | 228.982104 mm |
| Absolute supported path-length error | 330.121009 mm | 330.121009 mm |
| Heading RMSE | 1.836665 degrees | 0 by construction |

Participant/maneuver tables preserve regressions. 10x5: XY289.927042 ->397.034287mm; PS204.147641 ->199.655061mm; SL206.667073 ->196.753863mm; ST81.831921 ->76.900801mm. This does not establish that yaw repair is harmful or unimportant: the oracle is incomplete in gaps and motion errors interact.

## v67: observed-run versus gap accounting

For each trial, predicted minus reference endpoint displacement is exactly the vector sum of residuals within observed runs and between successive observed runs. Gap reference displacement uses observed endpoints only; no intermediate optical path is fabricated. Asserted telescoping identity on every trial. Signed dot products of each component with total endpoint error sum to squared endpoint error; negative values mean cancellation, not negative physical noise.

10x5 equal-person results:

| Quantity | Control | Heading oracle |
|---|---:|---:|
| Observed-run residual-vector norm | 978.498757 mm | 561.207650 mm |
| Gap residual-vector norm | 731.977689 mm | 715.700762 mm |
| Last-supported endpoint | 409.658903 mm | 620.799178 mm |
| Signed gap contribution to endpoint squared error | -0.189163 m2 | +0.524979 m2 |
| Observed contiguous1s world-displacement error | 135.488411 mm | 56.017358 mm |

Five/ten-second contiguous 10x5 windows are unavailable under the unchanged observed mask; report unavailable, not zero. RPE here is world displacement difference with starts every1s, no spatial alignment, no reference gap bridging. It is distinct from the historic distance-window rotation-normalized metric.

**Decision:** error cancellation is demonstrated in endpoint accounting. Better local heading agreement can expose unrepaired gap-motion errors and worsen aggregate localization. This accounts for an important part of the apparent oracle paradox; it is not a complete causal decomposition or proof of a timing/heading mechanism. Actual No.3 and No.8 plots were visually inspected; No.3's oracle develops strong lateral drift over repeated turns. Do not select estimators by cancellation or aggregate minimum alone.

## v68: historical data gate

49 declared pairs match49 metadata recordings. All30 declared July pairs have two exported IMUs and available C3Ds with positive-residual R_WC/L_WC support:60,006 supported frames; mean per-pair observed coverage81.379975%. Other July C3Ds are pairing-declared orphans. Zero nonpositive IMU time steps across inspected49 pairs. July median sample rates: L102.2913-102.4590Hz, R101.7294-102.4275Hz. These are scaled g/deg_s exports, not current raw-count CSVs. No rescaling performed. Physical marker roles, conversion provenance, semantic duplication and participant overlap remain unresolved; strict-track eligible count remains0. The small sensor rate difference does not itself prove clock drift.

## v69: historical reproduction gate

Rescored426 sealed common-native prediction rows (six methods x71 previously exposed validation recordings), with verified trajectory hashes. Maximum XY/heading metric difference0; scored-frame difference0. Historical old blend100.592598mm, refit94.661740mm exactly reproduced as artifact metrics, not a fresh independent model refit. No candidate selection. Existing v36 IMU-only inference reproduction was already complete: v34 100.702119424mm, max prediction difference5.878658e-9m, optical-input poisoning passed. Correct the old state note that v34 reproduction remained unfinished. The5.80% No.8 refit regression remains a rejection.

## Sources, checks and continuation

Commands: `python reference_closure_v66.py`; `python reference_gap_accounting_v67.py`; `python legacy_pair_quality_v68.py`; `python reproduce_headlines_v69.py`. All completed. Existing output directories are immutable: do not rerun into them. Outputs use corresponding outputs_*_v66/v67/v68/v69 directories, manifests, tables and diagnostic figures. v67 persists selected numeric trajectories. v66/v68 executed-source snapshots preserve pre-check code hashes; subsequent edits strengthen assertions without numerical changes. v66 post-run support audit checked all414 rows; straight-motion, wrapping, integrator-equality and IMU-gap self-checks passed. v67 has exact decomposition synthetic assertion; v68 verifies original258 input hashes; v69 checks every metric and mask against sealed controls.

Current retained model unchanged. Full strict-provenance calibration/base refits and source-grounded competitor comparisons remain prerequisites for a fair improvement claim. Next: freeze a complete fold/preprocessing provenance contract and target gap/turn heading dynamics using observed endpoint supervision; no speculative network training while those gates remain open.
