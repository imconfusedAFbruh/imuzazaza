# Best results � current checkpoint

| Candidate | Synchronized RMSE | Decision |
| --- | ---: | --- |
| Original v21 | 102.585179 mm | Reference benchmark |
| v34 tilt blend .75 | 100.702119 mm | Retained conditional development candidate |
| v38 naive corrected-clock refit | 96.329 mm own / 96.172 mm common | Reject: worst conditional training-person ratio1.559583 |
| v42 signal-arbitrated clock refit | 94.834759 mm own / 94.661740 mm common | Not promoted: No.8 ratio1.058004869 exceeds1.05 guard |

Comparisons across own-clock and common-native support are not interchangeable. Old v34 common-native comparator in v44 is100.592598mm.

v42 route diagnostics: symmetric RMSE46.124049mm, P9589.031705, sampled Hausdorff139.983334, max-run discreteFrechet155.161866, endpoint122.307880, absolute length113.305502, within-run arc85.805480. Old common-native route49.680804mm; absolute length105.713574mm. Smaller geometric mean coexists with worse length and participant regressions.

Evidence: outputs_clock_arbitrated_v42, outputs_clock_arbitrated_folds_v43, outputs_clock_arbitrated_loader_v44, outputs_clock_routes_v44. Retained v34 evidence: outputs_dynamic_blend_v34 and outputs_dynamic_loader_v36. All evaluation remains development/conditional; full calibration/base fold refit and fresh independent acquisition are outstanding. Test untouched.

## Later conditional results — do not replace headline
| Candidate | Result | Decision |
| --- | ---: | --- |
| v50 full-refit physics | 219.002 mm TRAIN folds | Selected baseline; alternatives fail robustness |
| v50 linear endpoint | 214.171 mm TRAIN folds | Reject: worst participant ratio 1.769287 |
| v52 projected-gravity yaw | 147.747 mm TRAIN folds | Passes guard (worst 0.961159), conditional simple-estimator result |
| v54 frozen v52 validation | 153.607 mm validation | All 4 participants improve vs same refit-physics baseline; no retuning; still worse than v34 |

v54 is useful mechanistic evidence, not a new best trajectory candidate. v55 is diagnostic rather than a candidate: No.18 PS2 405.191mm drops to60.344mm with observed speed only, while observed-yaw-only remains405.114mm, identifying a ~0.485m forward-travel deficit.
