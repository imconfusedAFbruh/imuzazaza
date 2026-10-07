# V9 implementation audit

The parallel review inspected the new synchronization and training sources before final neural validation. It did not run unit tests or open test acquisitions.

## Checked

- Relative pose targets rotate observed endpoint displacement into the observed starting body frame. Intermediate reference poses are not needed by endpoint loss.
- Five possible 512-frame contexts stitch their central outputs in temporal and channel order. Inactive contexts beyond the actual recording end are excluded from the network and BatchNorm; partial boundary contexts retain the same standardized zero padding as inference.
- Differentiable indexed copying preserves gradient flow into active predictions. Valid endpoint indices cannot depend on later padded motion.
- Normalization inversion, three-channel residual scales, clipping, gain application and midpoint integration are consistent. Training caches are on the declared 100 Hz grid.
- New trainable weights, normalization and caps exclude the inner training participant fold during selection. The inherited base model/calibration already saw those participants; the report explicitly describes this conditional selection limitation.
- Epochs and gains are frozen before final validation. Three seeds, both losses and predeclared motion ensembles are retained.
- Native clock comparison queries each recording's shifted IMU motion at identical raw reference timestamps, integrates from one identical observed pose, and scores identical observation/reconstruction masks. Optical gaps are not filled for synchronization feature smoothing.

## Corrections before final neural validation

The first incomplete training attempt required full 10-second segments and therefore omitted shorter maneuvers. The correction permits shorter recordings to use supported 1/3/5-second endpoints and masks beyond-record targets.

A second incomplete attempt still forwarded entirely empty padded contexts through BatchNorm. The corrected runner forwards only contexts with real output samples. This removes 743 empty contexts from the 1,207 eligible all-training segments (12.3% of the original fixed five-slot batches). Both incomplete attempts, exact executed sources and histories are preserved. These fixes were based on implementation coverage/context consistency, without final validation signals.

The final support audit is `outputs_long_horizon_support_v9_active/support.json`: valid 10-second pairs cross optical gaps in approximately 63.4% of cases. Short PS/CR/OS recordings now participate.

## IMU support

The cached development recordings contain zero invalid IMU frames. A separate synchronization audit checked the full pre-crop inputs: 544 recordings, 1,452,623 resampled frames, zero invalid frames. Thus the synchronization runner's global IMU smoothing crosses no invalid samples in this experiment. A segmented IMU smoother remains necessary before using that runner on future inputs containing gaps.

Proof: `outputs_observed_sync_imu_audit_v9/audit.json`. The frozen original pipeline and model artifacts remain unchanged. This audit reduces identified implementation risks; it is not a guarantee of error-free code or millimeter measurement accuracy.
