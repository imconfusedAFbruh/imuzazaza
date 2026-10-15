# Source-required input evidence audit, v105

Registered9October2026 before mask counts. No predictor, clock fit or real-signal
score. Read only TRAIN207 v80sensor time/validity masks and v84fold calibration
metadata after parent hash checks. Preserve all15No20 and completed artifacts.
Check complete first500ms valid support separately from stationarity: valid
sensor availability is not evidence that the wheelchair is quiet. Count internal
invalid runs to determine whether cross-gap filtering is a real current concern.
Do not invent physical calibration from these counts.

| Required input | Actual existing evidence | Defensible use / unresolved |
| --- | --- | --- |
| Three sensor roles, raw encoding and nominal units | default.yaml and firmware/receiver audit; L/R/C, raw int16, nominal.070dps/count/.000122g/count | Supported conversion; exact flashed runtime range remains inferred. No second conversion. |
| Signed wheel/frame coordinate system | Outward mirrored mounting in config; v84joint-midpoint gyro-axis/sign fits | Scalar supervised fits are not a measured3D mounting transform. Neither Wheel-INS gyro-x nor Fuss both-axes-left can be assumed. |
| Physical radius, camber and track | ConfigR.30,L_hub.52,alpha0; v97source contract | Nominal settings, not independent measurements. Hub separation is not established as source ground-contact track under camber. |
| IMU and reference lever arms | ConfigIMUoffset.04, reflectoroffset.066 | Scalar assumptions do not prove a full3D lever arm or reference-point equivalence on slopes. |
| Physical gyro bias/sensitivity | v84fold fit IDs disjoint; selected bias=-intercept/scale from supervised joint midpoint regression | Legitimate conditional training fit; not source quiet-prefix or independent wheel calibration. No joint terms rebranded WhAG. |
| Quiet500ms baseline | v80common100Hz masks/time can show available prefix | Stationarity not certified by valid support. No first-prefix bias fit or calibration change. |
| Noise/rate/gaps | Native device/packet timing audit,100Hzcommon grid; sourceWheel-INS fixed200Hzbuffer | Quantify masks below. Any comparator needs explicit rate/gap handling, not nominal-dt substitution. |
| External distance calibration | Sources use100/300m and straight-push procedures | No permitted local equivalent established; no known-route snapping or per-trial ground-truth scale. |
| Evaluation clocks/support/initial pose | Sealed v84/v92 contracts |199/207failsall207gate; original observed masks/all15No20/single initial pose fixed. No comparator trajectory run. |

Source references and primary equations are in wheel_source_results_v100_v101.md,
wheel_implementation_v102.md and fuss_consistency_v103_v104.md. Missing evidence
is a qualification, not proof physical parameters could never be inferred. A
future training-calibrated adaptation must be labelled and pass existing gates.
