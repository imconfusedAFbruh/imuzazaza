# C3D recovery conventions for subject ST and SL

Reviewed 2026-10-04. Scope: provenance and display conventions for the uphill ST and SL 3D views. This note does not authorize replacing the frozen reference, modifying source C3Ds, fitting models, or inspecting the test partition.

## What the fourth component means

C3D distinguishes positive residuals (measurement data), zero residuals (processed coordinates, possibly filtering, interpolation, or modeling), and negative residuals (invalid coordinates). Finite stored XYZ is therefore insufficient to declare a point observed. Zero does **not** mean absent XYZ, and does **not** reveal which processing operation occurred. [C3D residual definition](https://www.c3d.org/HTML/Documents/gloss_residual.htm)

For floating-point C3Ds, the first three values are already scaled XYZ; the fourth value encodes residual and camera information and is not simply an additional coordinate. A reader should expose decoded residuals and camera masks rather than infer validity from raw fourth-word positivity. [C3D floating-point layout](https://www.c3d.org/HTML/Documents/3ddatafloatingpointformat.htm)

Camera contribution recording is optional. Some exporters omit it entirely. An all-zero mask alone cannot establish occlusion; a populated mask can support reconstruction provenance, but cannot turn a zero-residual processed point into an original measurement. [C3D camera masks](https://www.c3d.org/HTML/Documents/cameracontributionmask.htm)

## Defensible display categories

These are recommended application flags, not extra C3D standard fields:

| Flag | Rule | Display / use |
|---|---|---|
| `observed_original` | Finite XYZ, decoded residual > 0, existing geometry and quality checks pass | Solid observed path; retain the existing frozen evaluation mask |
| `stored_processed` | Finite XYZ, residual == 0, geometry checks pass | Display separately as stored processed XYZ; do not call missing or independently observed |
| `invalid_original` | Residual < 0 or nonfinite XYZ | Preserve original invalidity regardless of plausible coordinates |
| `estimated_short_gap` | Newly estimated bounded interior gap | Dashed estimate, with method, gap duration and anchor provenance |
| `unresolved` | Invalid gap outside the declared recovery rule | Keep absent; never silently connect across it |

For a hub midpoint, propagate both marker flags. It is directly observed only when both markers are observed; if either is processed or estimated, its midpoint inherits that qualification. Retain original XYZ, residual, camera flags, and invalid mask in the sidecar. New estimates may have a separate finite XYZ array, but must not overwrite the original invalid mask. If exporting a separate processed C3D in future, zero residual is the appropriate processing convention, not a fabricated positive measurement residual. [C3D point residual flags](https://www.c3d.org/HTML/Documents/3dpointresiduals.htm)

## Recovery limits

QTM supports linear, cubic polynomial, relational and kinematic gap filling. It explicitly distinguishes filled and virtual samples from trajectory measurements. Relational rigid fitting uses three context markers; with only an origin its recovery is translational. These methods are estimates rather than renewed camera observations. [Qualisys QTM gaps](https://docs.qualisys.com/qtm/content/processing_measurement/gaps.htm)

**Project recommendation:** first count true invalid frames separately from zero-residual stored processed frames. Redisplaying stored processed XYZ may restore most apparent continuity without creating new coordinates. Use only short interior interpolation with valid anchors, an explicit fixed maximum duration, unchanged marker identity, and plausible pair geometry. Do not extrapolate start/end gaps. Treat the chosen maximum as a conservative visualization policy, not a documented guarantee of accuracy.

**Geometry inference:** two axle markers determine midpoint and axle direction while both are available, but do not determine full rotation about the axle. If one is missing, fixed pair distance plus one visible marker leaves infinitely many possible locations. Temporal interpolation supplies additional assumptions; it does not recover independently verified pose. Long gaps and ambiguous marker swaps remain unresolved. Wheelchair pitch cannot be recovered from the axle pair alone, although midpoint XYZ can be displayed when both coordinates are available.

Correct identification errors before smoothing or gap filling. A smooth wrong marker assignment remains wrong. [Qualisys editing guidance](https://docs.qualisys.com/getting-started/content/26_labeling_series/26b_how_to_edit_trajectories/gap_filling_and_smoothing.htm)

## What can be claimed

Report separate percentages and longest gaps for observed, stored processed, newly estimated and unresolved samples, preferably both over the full capture and the existing maneuver interval. Preserve source hashes. No interpolation result is an independent reference measurement; no new RMSE improvement follows from recovering a display. C3D residuals also do not establish absolute millimeter accuracy: low residuals can coexist with geometric measurement errors. [C3D point residual interpretation](https://www.c3d.org/HTML/Documents/3dpointresiduals.htm)
