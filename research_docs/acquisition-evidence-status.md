# Acquisition evidence status

Current-status note, 15 October 2026: this October 3 evidence log is historical.
Its unresolved serialization and +/-2 g assumptions are superseded by the
[firmware/receiver audit](firmware_receiver_audit_2026-10-05.md) and
[release verification](firmware_primary_audit_2026-10-08.md): raw int16 is preserved;
source and data support +/-4 g and +/-2000 dps. Exact flashed binary/runtime
range provenance, independent clock linkage and full geometry remain unresolved.
No frozen conversion changes follow from this documentation correction. Use the
[current protocol status](frozen-next-experiment-protocol.md) for remaining gates
and the [v123 review closure](frozen_validation_review_v123.md) for the latest result.

Updated 2026-10-03 (Asia/Bangkok), following the researcher's supplied status table.

## Evidence available versus independently inspected

`config/default.yaml` was inspected locally. It specifies board/sensor/library names, researcher-confirmed nominal ranges, mounting descriptions and configured chair dimensions. It explicitly retains `library_float_encoding_verified: false` and `units.verified: false`. These configuration values are not a firmware audit or dimensional uncertainty measurement.

The supplied file `Gait overlay 8.settings.xml.txt` was parsed successfully. It names `Gait overlay 8.qtm` under a Sept. 25 directory and records CaptureStart date `2026-09-25`, time `10:21:18.200`, and timestamp `5102.91724190` (timezone and timestamp correspondence to IMUs unspecified). It contains 16 active cameras, all marked calibrated: eight Arqus A5, four Miqus Video Plus and four Miqus Hybrid. Each includes transform, intrinsics and distortion parameters. Camera 54229 has average residual 0.610867 mm. Across cameras, residuals range 0.577224–0.945080 mm; their unweighted mean is 0.745387 mm. The mean is descriptive, not a propagated 3D uncertainty. Rotation matrices are consistent with proper rotations to XML rounding precision. The export also records two force plates and 12 named force/moment channels, but no force samples or demonstrated IMU synchronization. Association with canonical participant/trial C3Ds remains unresolved.

## Correction to residual terminology

Qualisys explicitly defines the calibration XML camera attribute `avg-residual` as an average camera residual **in millimeters**. The parsed attribute matches this schema: 0.610867 is approximately 0.611 mm, not a pixel reprojection error. This still does not establish a 0.611 mm absolute position uncertainty, a confidence interval, hub-reference uncertainty, or the uncertainty of every tracked sample. [Qualisys protocol, calibration XML attributes](https://docs.qualisys.com/qtm-rt-protocol/), [calibration results](https://docs.qualisys.com/qtm/content/running_the_system/calibration_results.htm).

## Updated status

| Requirement | Status | Established | Unresolved |
|---|---|---|---|
| Reference geometry and uncertainty | Partial | Camera metadata directly inspected; configured dimensions locally verified | Per-session/recording calibration linkage, reference uncertainty/validation measurements, physical world-frame convention, marker offset uncertainties |
| Sensor conversion and mounting | Partial | Configured hardware/library, nominal units/ranges, outward/mirrored mounting description | Executed firmware/source version, CSV serialization/scaling, timestamp semantics, full mounting rotations and lever-arm vectors |
| Synchronization | Partial | Existing packet-clock and multiple-peak diagnostics | A shared hardware timing event or independently measured alignment/drift uncertainty; CaptureStart alone does not establish clock correspondence |

Camera extrinsics describe camera placement relative to the calibration frame. They do not directly establish the IMU-to-chair mounting rotations. Scalar IMU/reflector offsets do not establish three-dimensional lever-arm vectors or their uncertainty. The provided geometry should continue to be described as configured until its measurement provenance is available.

## Next evidence to inspect

1. Link this named QTM recording/settings export to canonical study C3Ds and obtain calibration creation/version and validation metadata for each relevant capture date. The supplied XML has no calibration wrapper, creation/version attributes, or wand-length validation statistics. Do not assume it applies to every recording.
2. Exact acquisition firmware, including sensor range initialization, library reads, CSV integer encoding, device timestamp generation and packet/PC timestamp assignment.
3. Mounting/marker measurements or diagrams with coordinate axes, camber and uncertainty; evidence that exported C3D XY is the intended horizontal plane.
4. Independent calibration validation and timing measurements with uncertainty appropriate to the intended 1â€“10 mm target.

No model, conversion, split, synchronization rule or frozen experiment artifact was changed on the basis of this table. The best development candidate remains the previously reported 0.3685 m validation result; this new metadata does not itself improve trajectory RMSE or support a millimeter accuracy claim.

## Extracted evidence

[Parsed settings summary](C:/Users/poon1/Desktop/kight_recover/research_docs/qualisys-settings-summary.json) records the source hash, camera values and limitations. The XML improves documented calibration evidence, but neither requirement is fully verified and no estimator or frozen numerical result changed.

## Supplied YAML profile: unresolved range and encoding conflict

The researcher subsequently supplied a profile declaring acceleration range 16 g, gyro range 2000 degrees/s, storage `integer_raw`, and an observed resting acceleration norm around 8200. Its verification flags remain false. When asked to resolve the conflict, the researcher explicitly confirmed: "Actual acquisition was ±2 g". The acquisition range therefore remains researcher-confirmed 2 g, consistent with the frozen working configuration; the supplied 16 g value does not describe the actual acquisition. Executed firmware and register configuration have not yet been independently verified.

The inspected Seeed library constructor defaults to 16 g and 2000 degrees/s, but acquisition code can override those defaults before initialization. This is evidence about the library, not the installed acquisition executable or CSV serialization. [Seeed source](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/master/LSM6DS3.cpp).

ST lists nominal accelerometer sensitivities 0.061/0.122/0.244/0.488 mg per raw LSB for 2/4/8/16 g ranges. At rest with acceleration magnitude approximately 1 g, true unscaled register-count norms would therefore be approximately:

| Range | Expected raw count norm at 1 g |
|---|---:|
| 2 g | 16393 |
| 4 g | 8197 |
| 8 g | 4098 |
| 16 g | 2049 |

The supplied 8200 norm does not support unscaled raw-register CSV encoding under the researcher-confirmed 2 g range: that interpretation predicts approximately 16393 counts at 1 g. It is compatible with a 4 g raw-count interpretation, but scaled library readings or other serialization can produce similar values; it does not establish a different acquisition range or a factor-of-two correction. Firmware and register/serialization evidence are required before applying factory conversion. Gyro sensitivity at 2000 degrees/s is nominally 70 mdps per raw LSB, conditional on true register-count encoding. [ST datasheet, Table 3](https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf).

Two supplied YAML settings do not describe the effective frozen estimator:

- `synchronization.refinement_step_s: 0.0001` exists in YAML, but the frozen synchronizer uses a hardcoded 0.025 s candidate-lag grid and does not perform that refinement. Numerical resolution would not independently prove timing accuracy even if implemented.
- `sampling.gt_hz: 20` is a legacy nominal setting. Reference processing reads C3D metadata; the inspected target C3Ds are 100 Hz. Correlation scoring is downsampled to about 20 Hz for work reduction, which is different from reference acquisition rate.

No frozen YAML, source, calibration or fitted model was overwritten to resolve these contradictions. Existing conversion remains explicitly empirical and training-fitted. An amended synchronization or unit-conversion experiment must be separately versioned and evaluated on development data.

## Implemented synchronization refinement experiment

The separately versioned `synchronization_experiment.py` now implements a 1 ms then 0.1 ms local lag search after the frozen coarse alignment passes. All candidates use the same native-rate valid samples; peak support and the correlation gate remain required. The experiment searches correlation, not trajectory RMSE. It reprocesses the same accepted 477 training and 72 validation recordings; rejected recordings and test signals are not opened. Original coarse validation results reproduce their parent values. The training-only physics refit scores 465.705 mm versus 468.933 mm originally, and the frozen planar neural model scores 366.248 mm versus 368.499 mm originally. Neural models are not retrained. This is exploratory validation alignment sensitivity, not independent timing-accuracy evidence or millimeter trajectory accuracy. See `outputs_synchronization_v5/report.md` and `alignment.json` for results and diagnostics. The frozen production synchronizer itself still has its original 25 ms candidate grid.

## Later reference-validity correction

The subsequent v7 audit identified accepted zero-residual C3D coordinates with no camera support, including generated leading headings. These are processed values under the C3D specification, not original optical measurements. Their use as initial poses caused several major trajectory failures. The separately versioned observed reader excludes these frames before filtering/differentiation and initializes at the first actually observed synchronized pose; missing reference never resets reconstruction. Positive residual and support agree across all 646 readable training/validation C3Ds. The camera mask remains optional when an exporter does not populate it.

On the same observed frames of 71 validation recordings/four participants, the old reconstruction scores 373.243 mm, corrected initialization with frozen weights scores 118.490 mm, and the selected training-fitted ridge residual scores 116.898 mm. This changes reference coverage and initialization, so it is not a direct model improvement on the earlier full-duration benchmark. Four training and one validation recording are newly excluded for insufficient observed labels. The clock mapping remains inherited from v5 and independent optical/timing accuracy is still unresolved. No test signals were read. Current corrected development results and before/after plots: `outputs_reference_recovery_v8/report.md`; validity rationale: ADR 0003. [C3D residual specification](https://www.c3d.org/HTML/Documents/gloss_residual.htm).
