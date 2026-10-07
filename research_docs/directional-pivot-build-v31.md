# Directional pivot build v31

Overall equal-participant validation RMSE: 104.743219mm vs v25 106.309394mm. Original v21 remains102.585179mm; the new model does not beat its overall minimum. Reused validation exploratory, no test data.

Selected on training folds: {"name": "positive0.5_negative0.0", "positive": 0.5, "negative": 0.0, "score": 0.1386776041942417, "worst_person": 1.006779329718431, "worst_cell": 1.0494047921678507, "worst_vs_ridge": 1.0222584925604907}

| Recording | v21 mm | v25 mm | v31 mm |
|---|---:|---:|---:|
| AR_Trial2_No.5 | 319.232 | 321.423 | 267.967 |
| AR_Trial3_No.5 | 279.378 | 283.741 | 238.255 |
| CR_Trial3_No.5 | 65.909 | 67.337 | 67.337 |

All473 accepted training recordings are represented in the inherited full-training model: 266 earlier recordings and207 Sept24/25 training-person recordings. New pivot strengths selected on three four-person training folds, then applied to the existing all473 fit. No.5 is validation, never used for fitting. New guard also limits each held participant/maneuver cell regression to5%. Inherited calibration/neural weights previously saw innerfold training people; conditional selection, not independently refitted whole neural stack.

Mechanism: raw-calibrated wheel velocities determine a continuous counterrotation gate, attenuated at low yaw. For positive predicted yaw, blend model forward velocity halfway toward wheel mean; for negative yaw use no additional blend. Lateral and yaw stay exactlyv25. No condition, participant or recording ID enters inference. No ideal-circle forcing. No automatic heading swap.

User confirmed no independent video/QTM evidence for AR2/AR3 marker identity. Their physical-front ambiguity remains unresolved. Preserve original reference/starting orientation, retain these trials and their official scores. Alternativepi visualization is diagnostic sensitivity only and never selected by reference error.

All71 reference-free inference arrays reproduce exactly. Original pipeline/learning/test locks and reference caches remain preserved. No test access. Rotational trial CR3 is preserved relative tov25 rather than cosmetically repaired.

Sources: rotation_motion_experiment_v29.py, pivot_channel_selection_v30.py, directional_pivot_selection_v31.py, directional_pivot_inference_v31.py; versioned foldersoutputs_rotation_motion_v29/,outputs_pivot_channels_v30/,outputs_directional_pivot_v31/.
