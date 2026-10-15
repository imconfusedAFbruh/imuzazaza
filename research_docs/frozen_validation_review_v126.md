# v126 independent review closure

15 October 2026. One frozen v125 comparison, reporting and independent review
are complete. The comparison rejects v125; retain the unchanged v121 model.

## Result and decision

All71 previously exposed validation records/four participants/105821 scored
frames are retained. Equal-person XY ATE is v34100.702119399mm,
v12199.303735166mm and v12599.700352275mm. V125 is.396617109mm /.399398%
worse than v121. Its OS/v121 ratio1.0527649671060733 exceeds the unchanged1.05
guard, and its mean is not lower. Both failures reject the model despite all
guards passing against historical v34. All four participants slightly worsen.

V125's TRAIN127.531627048mm gain and11/12 improving TRAIN people did not
transfer to this development-validation cohort. Better routeRMSE and10sRTE
do not override the original acceptance rule. The latter covers only4 records/
two people. Do not tune penalties, exclusions, clocks or maneuver-specific
selection from this comparison. No further candidate was evaluated.

## Execution and model identity

Nine synthetic contracts and independent source preflight passed. The guarded
runner completed exit0 in43.8248616s. Both public controls were reconstructed
on all71 before the sole v125 scoring loop. Original startup, clocks, crops,
reference arrays, initial pose and full finite/scored support were preserved.
V34 matches its saved motion/XY/headings exactly; v121 motion/XY differs by at
most2.220446049250313e-16 and heading exactly matches. These are inside the
original unchanged v123 tolerances. No tolerance or CPU setting was adjusted
after a mismatch. Original four Torch threads were used throughout.

- Retained v121 `models/reservoir_path_v121_completed/model.json` SHA256
  `6989346d9e4c2ec68ff7ce0c8ab49c219b13fb44d6881f032f7971df97c4af9b`.
- Rejected v125 `models/axis_prior_v125/model.json` SHA256
  `7a056e2ddc8ebec372a40be0e9a7d2b43088b745838c408643ddcadd749f2eb2`.

Both bundles remain unchanged. Their freeze-time validation flags describe
their creation; the separate sealed comparison records this later evaluation.
No fitting, retuning, alternative model, reserved-test use, deployment, commit
or push occurred. The contextual interpretation of the renewed user reply was
recorded before scoring in `frozen_validation_v126.md`; the earlier v125
decision proposal's prospective wording is historical and its input hash is
preserved. The single proposed comparison is consumed.

## Independent saved-output and report checks

`research_state/v126_independent_review.json`: PASS, guarded exit0.
Checker `research_state/review_frozen_validation_v126.py` SHA256
`f7d631c23682703cf465a643aa110afb80e53f5cbcef734a334335cc47882759`.

Verified156 output files,524 input pins and the source/model/report seals.
169 permitted input contents were independently rehashed.355 protected raw/
cache/older-v34-trajectory hash entries were compared to the sealed v123 pins
without reopening those contents. The executing runner had checked actual
input contents both before and after scoring. These two checks are distinct.

Independently integrated all213 saved motions and reconstructed ATE, P95,
last-supported endpoint, heading, masks,355 reference arrays,426 control-array
comparisons, all participant/maneuver tables and both guard decisions. Original
tolerances and the actual OS/mean rejection were verified. Report checks cover
all2556 grouped rows,15 recorded report inputs,3 report outputs and availability
denominators:48 groups lack values and162 are partially available. Report text
correctly retains v121. Secondary route/filter-derived values were aggregated
from sealed trial tables, without recomputing those diagnostics from raw signals.

The four participant benefits over v121 are[-.218739572,-.352377454,-.707682285,
-.307669124]mm:0/4 improve. Independent seed1224096-draw bootstrap reproduces
the descriptive95 interval[-.607678995,-.252149043]mm and all16 exact signs give
2/16=.125. Omitting any person leaves negative mean benefit. This exposed,
small-cohort evidence does not establish independent significance.

## Remaining boundary

Do not repeat this comparison or develop a replacement by targeting its observed
validation failures. A future TRAIN hypothesis needs a distinct preregistration
that preserves the split/guard contract; independent final evaluation needs
new evidence and its frozen milestone. Original independent clocks, exact
firmware/runtime identity, physical geometry and final acquisition remain
unresolved. Inherited266 parent training records, offline context and optical
crops remain limitations. No blind final generalization is established.
