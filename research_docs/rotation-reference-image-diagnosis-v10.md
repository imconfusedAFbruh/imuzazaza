# Rotational trajectory image audit, v10

## Scope

Images inspected: `outputs_all_trajectories_v10/AR_all.png` and `CR_all.png`. Native C3Ds and frozen v7 caches inspected for the six AR/CR repetitions of validation participants No5 and No10. No test acquisitions or fitted artifacts were changed. No error-based exclusion, reference swap, or pose fit was applied. The audit script is `rotation_reference_diagnosis_v10.py`; native metrics and six diagnostic figures are in `outputs_rotation_reference_diagnosis_v10/`.

## Findings

| Recording | Native observed support | Separation SD | Heading sweep | Initial heading | GT/base forward correlation | GT/base yaw correlation |
|---|---:|---:|---:|---:|---:|---:|
| No5 AR1 | 100% | 0.920 mm | 748° | −88.6° | +0.985 | +0.99980 |
| No5 AR2 | 99.9% | 0.735 mm | 739° | +88.6° | **−0.833** | +0.99984 |
| No5 AR3 | 100% | 0.751 mm | 732° | +91.1° | **−0.919** | +0.99982 |
| No5 CR3 | 99.0% | 1.045 mm | 722° | −88.8° | +0.910 | +0.99981 |

The anomalous AR2/AR3 are not short or absent maneuvers. They last approximately ten seconds, contain nearly two complete rotations, and have densely observed, rigid marker pairs. Adjacent heading changes never exceed approximately 1.8°/1.9°; there is no within-recording 180° label jump. Their camera-supported midpoint moves through a small region, while the individual markers trace large circles. That geometry is consistent with a nearly in-place turn.

The striking discrepancy is the **signed forward component**, not yaw synchronization: AR2/AR3 optical forward velocities are strongly opposite the calibrated wheel prediction, while their yaw agrees almost exactly. Their initial headings differ by approximately 180° from AR1 and all No10 AR trials. This is consistent with an L/R optical assignment reversal or equivalent body-heading convention ambiguity. Swapping L_FAL/R_FAL changes heading by π, preserves the midpoint, and preserves yaw derivative, while reversing the signed forward reference velocity. Thus existing separation, rigidity, and yaw-peak gates cannot detect this ambiguity.

This is a strong diagnostic hypothesis, **not established proof that the labels are wrong**. The chair might begin facing the opposite direction; a recording-specific wheel sign/mounting change or nonstandard movement could also alter the velocity relation. Only two exported markers are available; the supplied C3Ds do not independently identify the physical chair front or validate L/R identity. The files' PROCESSING comments match their acquisition names, which supports file pairing but not physical side assignment. A blanket 180° flip selected because it makes the plotted path match would fit the validation reference and is not acceptable evidence.

All three files contain exactly `['L_FAL', 'R_FAL']` as their POINT labels; no front/rear marker is available for an independent initial-pose check. Raw first-frame positions, millimeters:

| Recording | L_FAL XYZ | R_FAL XYZ |
|---|---|---|
| No5 AR1 | (−386.75, −531.07, 297.93) | (−1058.98, −547.96, 287.05) |
| No5 AR2 | (−1183.59, −677.28, 282.03) | (−512.17, −693.82, 295.67) |
| No5 AR3 | (−1082.94, −667.97, 287.65) | (−411.61, −654.09, 295.49) |

The raw x-side and higher-marker identity reverse, but neither independently proves the physical chair front. Height difference could depend on mounting or floor/roll; it should not become an invented side classifier. Local acquisition documentation and calibration settings supply no auxiliary marker identity map. Consequently the allowed initial optical pose cannot resolve this ambiguity from the available data alone.

No5 CR3 is different. Its native marker paths show two full rotations around a relatively stationary hub midpoint; the midpoint's native bounding box is about **231×120 mm**. Both estimators also produce a small trajectory. Forward signs and yaw match. Its irregular shape in the overview is not evidence of corrupt reference or a missing turn. It is a genuine low-translation rotational condition in which the hub path is small compared with wheel-marker motion. The approximately 59–68 mm error is meaningful relative to that small path; a circular template would erase real motion rather than fix it.

## Appropriate correction

1. Flag AR2/AR3 as **unresolved signed-heading/side-identity consistency**, retaining their current score and images. Keep acquisition-wide error and reference ambiguity separate in reporting.
2. Validate these two trial marker identities in the original QTM project, acquisition video, or an independent chassis/front marker. If verified, create a separately versioned reference amendment and report the old and amended scores; do not silently rewrite frozen C3Ds.
3. For future acquisition, add a third noncollinear chassis marker or a surveyed initial front direction. Two labeled axle endpoints are sufficient only when side identity is correct.
4. A consistency diagnostic can compare training-calibrated signed wheel velocity with optical forward velocity, conditional on actual movement and adequate support. Its threshold should be fixed on training data and it should flag review, not automatically flip a validation heading or reject a high-error recording.
5. Retain time/direction annotation on low-translation AR/CR panels. Show the two marker paths in the diagnostic view so a small midpoint path is not mistaken for missing rotation.

These findings come directly from native camera-supported geometry and the frozen training-calibrated physical predictor. Residual and rigidity pass status does not prove side identity or absolute positional accuracy.
