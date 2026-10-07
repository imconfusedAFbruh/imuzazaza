# Synchronization, generalization, and the next wheelchair evaluation

Research date: 2026-10-03 (Asia/Bangkok). Scope: investigate defensible next steps after the existing final test. This note changes no estimator, calibration, split, weights, frozen reports, or evaluation. Recommendations below are proposals, not verified fixes.

## What the existing experiment establishes

The selected TCN improved validation participant-mean position RMSE from 0.5156 to 0.4524 m, but worsened the accepted test-subset result from 0.5020 to 0.6139 m. Test QC accepted 32/84 trials, all from No.2 and No.9. Neither No.11 nor No.12 contributed a score. These are observed results; they establish neither learned-model improvement nor performance on the planned two-date test population. See [validation report](C:/Users/poon1/Desktop/kight_recover/outputs/validation_report.md:7) and [final report](C:/Users/poon1/Desktop/kight_recover/outputs/final_test_report.md:7).

The exact No.11 exclusions are one device/PC clock-scale rejection and 20 generic synchronization rejections; No.12 has 21 generic synchronization rejections. No.2 has one non-monotonic clock rejection and four synchronization rejections; No.9 has five synchronization rejections. This is a direct grouping of [qc_test.csv](C:/Users/poon1/Desktop/kight_recover/outputs/qc_test.csv:1). The rejection text does **not** establish that every generic rejection is caused by clock offset or peak matching.

## Reference quality must be diagnosed before peak matching

The reference accepts a frame only if both hub markers have nonnegative residuals, finite nonzero coordinates, and separation within 0.08 m of the configured 0.652 m marker separation. It then derives speed and yaw only inside sufficiently long valid segments, excluding boundary samples. See [reference construction](C:/Users/poon1/Desktop/kight_recover/pipeline.py:169), [geometry calculation](C:/Users/poon1/Desktop/kight_recover/pipeline.py:95), and [configuration](C:/Users/poon1/Desktop/kight_recover/config/default.yaml:28).

The synchronizer silently skips a channel when fewer than 100 derivative-valid reference frames exist or reference motion has insufficient variance. All failed paths then produce the same generic exception. Thus absent reference labels, low motion, too few peaks, poor correlation, and offset ambiguity are observationally conflated. See [synchronize](C:/Users/poon1/Desktop/kight_recover/pipeline.py:267). An acquisition-wide marker/geometry problem can look like a synchronization problem through this code path; the audit below reproduces that mechanism for No.11/12 reference construction.

A read-only audit during this research reproduced a concrete geometry-gate failure: each of No.11, No.12, and training participant No.20 has 21 September 25 C3Ds, stored in mm. Their median trial marker separations are respectively 0.74758, 0.74710, and 0.74641 m; median residual-valid fraction is 1.0, yet median final reference-valid fraction is 0.0. The configured gate accepts only 0.572–0.732 m. Thus these stable wider marker pairs are rejected before reference derivatives become available. This establishes a reference-construction failure mechanism for these records; it does not establish physical hub width, prove a different wheelchair, explain No.11's separate clock rejection, or prove that any amended synchronization would succeed. No.20 supplies training-only evidence of the same mismatch, so diagnosing it need not depend exclusively on test outcomes.

The audit read all 210 files under `c3d/2026-09-25`, computed per-trial separation medians, and then participant medians. A reproducible minimal version (read-only; does not call synchronization or evaluate models) is:

```python
from pathlib import Path
from collections import defaultdict
import ezc3d
import numpy as np
from pipeline import reference, settings

cfg = settings(Path('.'))
audit = defaultdict(list)
for path in Path('c3d/2026-09-25').rglob('*.c3d'):
    c = ezc3d.c3d(str(path))
    p = c['parameters']['POINT']
    assert p['UNITS']['value'][0].strip() == 'mm'
    labels = [v.strip() for v in p['LABELS']['value']]
    ids = [labels.index(v) for v in ('L_FAL', 'R_FAL')]
    xyz = c['data']['points'][:3, ids].transpose(2, 1, 0) * .001
    sep = np.linalg.norm(xyz[:, 0] - xyz[:, 1], axis=1)
    residual = c['data']['meta_points']['residuals'][0, ids].T
    audit[path.stem.rsplit('No.', 1)[-1]].append([
        np.median(sep), np.mean((residual >= 0).all(axis=1)),
        np.mean(np.abs(sep - .652) <= .08),
        reference(path, cfg)['raw_coverage']])
for participant, rows in sorted(audit.items()):
    print(participant, len(rows), np.median(rows, axis=0))
```

The necessary amendment is to establish actual acquisition geometry from measured metadata and development recordings, make reference-quality rejection stage-specific, and freeze that revised protocol with an already-seen-test disclosure. Relaxing a tolerance solely to recover the final test remains unsupported.

C3D marks invalid 3D observations using negative residuals and declares coordinate units in POINT:UNITS. Units and point validity therefore need explicit inspection before differentiating positions. [C3D 3D point specification](https://www.c3d.org/HTML/Documents/3dpointdata.htm), [C3D technical user guide](https://www.c3d.org/docs/C3D_User_Guide.pdf).

Recommended first investigation: record each validity component separately, marker separation percentiles, label continuity, residual availability, marker naming, and derivative-valid seconds for every attempted trial. Check whether failures cluster by participant, date, marker assignment, and maneuver. Obtain the QTM acquisition calibration and marker placement record. Do not enlarge the geometry tolerance solely because doing so recovers inspected test trials. If true chair/marker geometry differed, document a physical measurement or acquisition record and evaluate that amended reference protocol separately.

XY is currently assumed horizontal and marker midpoint is assumed to represent the hub midpoint. QTM allows coordinate rotations/translations; its default wand-calibration XY plane follows the L-frame, and settings can change that convention. A floor-plane and marker-offset audit is therefore warranted before publication. [Qualisys wand calibration](https://docs.qualisys.com/qtm/content/running_the_system/wand_calibration_method.htm), [Qualisys transformation](https://docs.qualisys.com/qtm/content/project_options/transformation.htm). This is an acquisition check, not permission to align each estimated full trajectory to its reference.

## Clock and peak procedure: what to check next

Each device clock is currently mapped to PC packet times by a robust affine fit, with fitted slope required to lie between 0.995 and 1.005. The code treats device-clock non-monotonicity as an error. MoCap time starts at zero from frame rate, and synchronization estimates a **single offset**, not IMU–MoCap clock drift. See [IMU clocks](C:/Users/poon1/Desktop/kight_recover/pipeline.py:209) and [offset search](C:/Users/poon1/Desktop/kight_recover/pipeline.py:267). Whether packet arrival times reliably represent sampling times remains unverified; inspect firmware timestamp semantics, batching, resets, and counter width before altering these gates.

Qualisys explains that devices can have different clock speeds and recommends tracking clock rates as well as starting time. Its external periodic TTL timebase locks the camera capture frequency to the external source, providing a prospective acquisition option when the IMU logger can support a compatible timing link. [Qualisys synchronization options](https://docs.qualisys.com/getting-started/content/getting_started/getting_started_with_external_equipment/synchronization_options.htm), [external timebase](https://docs.qualisys.com/qtm/content/system_hardware/how_to_use_external_timebase.htm). This does not mean the existing recordings have a hardware synchronization channel.

Recommended diagnostic evidence is a peak-correspondence table across early, middle, and late recording segments; accepted candidate offsets; runner-up separation; overlap duration; correlation; and residual timing error. A time-varying peak residual would motivate an affine MoCap–IMU mapping, but drift must be demonstrated before adding it. Repeated maneuvers can generate multiple plausible lags; no specific ambiguity mechanism has yet been reproduced.

The current yaw feature is the raw center-gyro norm; the fallback speed feature sums raw wheel-gyro norms. Biases and out-of-plane rotation can affect these norms. The fallback also sums sensor channels before applying per-sensor calibration. This follows directly from [feature construction](C:/Users/poon1/Desktop/kight_recover/pipeline.py:269). A future development-only comparison can test signed, projected, calibrated yaw and wheel-speed channels, robust monotonic one-to-one peak correspondence, and fixed multichannel agreement. Current nearest-neighbor peak counting permits multiple reference peaks to share one IMU peak ([matching](C:/Users/poon1/Desktop/kight_recover/pipeline.py:304)); investigate whether this actually inflates acceptance before modifying it.

## Sensor encoding and physics baseline

The manufacturer specifies acceleration sensitivity of 0.061 mg/LSB at ±2 g and angular-rate sensitivity of 70 mdps/LSB at ±2000°/s. These apply to sensor register outputs. [ST LSM6DS3TR-C datasheet, Table 3](https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf). The Seeed library exposes distinct raw-register and floating-reading methods and converts counts in `calcAccel` and `calcGyro`. [Seeed library source](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/master/LSM6DS3.cpp). Consequently, neither the supplied full-scale ranges nor `_raw` column names determine this logger's integer encoding. Obtain the actual acquisition firmware, library revision, saved scale values, integer conversion, and sensor configuration readback. Manufacturer and current library sources are references, not proof of the firmware used in September.

The baseline currently fits an axis, sign, scale, and intercept independently for each sensor **by date** against training reference motion. Wheel targets use differential-drive kinematics, while yaw uses the center sensor only. It does not independently verify physical units, estimate online bias, or fuse wheel-derived yaw. See [calibrate](C:/Users/poon1/Desktop/kight_recover/pipeline.py:408) and [velocities](C:/Users/poon1/Desktop/kight_recover/pipeline.py:433). Date grouping assumes unchanged mounting and encoding within a day. Verify acquisition setup boundaries rather than treating that assumption as established.

Wheel-INS is an original wheel-mounted MEMS IMU dead-reckoning approach; it provides a relevant reference for evaluating a fuller inertial/wheel physical estimator. Its reported vehicle drift does not establish expected wheelchair performance. [Wheel-INS paper](https://arxiv.org/abs/1912.07805). A future baseline comparison should first verify wheel-axis projections, mirrored signs, radius, track width, camber, and observed wheel-versus-frame yaw consistency on development data. Wheel slip, remounting, bias changes, and geometry mismatch are competing hypotheses, not known causes here.

## Learned correction: defensible improvements

The TCN input concatenates 18 raw channels and baseline speed/yaw. It has a 125-sample receptive field (1 + 4×(1+2+4+8+16)), approximately 1.25 s at 100 Hz. Training minimizes pointwise speed/yaw residual Smooth L1 loss, whereas checkpoint selection minimizes integrated trajectory error. Normalization pools accepted training samples; windows are sampled uniformly from the window inventory rather than equally by participant. See [features/architecture](C:/Users/poon1/Desktop/kight_recover/learning.py:14), [windows](C:/Users/poon1/Desktop/kight_recover/learning.py:42), [normalization](C:/Users/poon1/Desktop/kight_recover/learning.py:118), and [loss/selection](C:/Users/poon1/Desktop/kight_recover/learning.py:149). These are plausible sources of sensitivity, not explanations proven by the final result.

The existing participant tables also caution against claiming yaw drift is the sole model failure: No.9's heading RMSE improves while position RMSE worsens. See [baseline participant table](C:/Users/poon1/Desktop/kight_recover/outputs/baseline/test_participants.csv:1) and [TCN participant table](C:/Users/poon1/Desktop/kight_recover/outputs/tcn32/test_participants.csv:1). Integrated yaw error, speed error, and their interaction need separate development-data analysis.

The largest accepted-subset maneuver increase is 10x5: participant-mean trial position RMSE rises from approximately 1.191 to 1.805 m across five accepted trials and two participants. PS and SL instead show small improvements, so degradation is not uniform across maneuvers. No OS trial is scored. See [baseline maneuver table](C:/Users/poon1/Desktop/kight_recover/outputs/baseline/test_maneuvers.csv:1) and [TCN maneuver table](C:/Users/poon1/Desktop/kight_recover/outputs/tcn32/test_maneuvers.csv:1). These small conditional samples cannot identify a general maneuver-specific cause.

RoNIN evaluates seen and unseen subjects and several neural architectures, including TCNs. Its pedestrian results support explicitly testing participant generalization; they do not transfer a winning architecture or error target to a wheelchair. [RoNIN original project and paper](https://ronin.cs.sfu.ca/).

WING learns wheel and IMU measurement corrections together with time-varying uncertainty and fuses them in a filter. Its hardware includes wheel encoders and its model addresses ground robots, so direct transplantation is not justified. It motivates a small uncertainty-aware residual model as a future comparator once sensor meaning and synchronization are verified. Its covariance ablation explicitly tunes a factor on a test set; that practice should not be copied for this project's independent evaluation. [WING original paper, Sections IV, VI and VII](https://arxiv.org/html/2407.10101v1).

TLIO likewise combines learned displacement and uncertainty with an EKF estimating pose, velocity, and sensor biases, using headset pedestrian data. It supports the general idea of learned observations with uncertainty, not a claim that the current three-IMU wheelchair must use its full estimator. [TLIO original paper](https://arxiv.org/abs/2007.01867).

Recommended development sequence: retain the original baseline as comparator; compare physically scaled/projected features against raw inputs; inspect speed and yaw residual biases by participant/setup/maneuver; balance sampling; test constrained residual magnitude and training-only motion-preserving augmentations; compare pointwise loss against a short integrated-motion loss; and only then compare learned uncertainty fusion or a longer-context model. Require ablations and improvement across development participants, not simply a lower pooled mean. A larger model alone has no demonstrated benefit here.

## Evaluation after this test has been seen

Preserve the current report and frozen artifacts as the first experiment. All changes motivated by its exclusions or scores constitute a protocol amendment. A recovery analysis on the same trials must be labeled post hoc and cannot restore untouched-test status. [Existing lock requirement](C:/Users/poon1/Desktop/kight_recover/outputs/final_test_report.md:35).

Preferred future confirmatory evaluation: collect genuinely new participants with documented firmware, mounting, marker geometry, and hardware synchronization where feasible. Freeze inclusion gates, calibration procedure, candidate search budget, alignment, metrics, and final estimator before opening that cohort. Retain participant grouping across all dates. Report attempted participants/trials, accepted/scored counts, reference and reconstruction coverage, each exclusion component, and paired baseline-versus-model differences. Keep primary absolute trajectory RMSE at known initial pose; label locally heading-aligned relative-distance errors separately ([relative metric](C:/Users/poon1/Desktop/kight_recover/pipeline.py:495)).

If new data are unavailable, grouped nested cross-validation can provide a disclosed retrospective estimate: outer folds group participants; every inner fit includes calibration, synchronization-setting selection, normalization, model choice, and checkpoint choice. Earlier sessions remain training only. Report per-date and per-maneuver coverage plus participant-level variability. Do not claim that resplitting already inspected data manufactures a new independent test. Varma and Simon show why tuning and performance estimation require separate nesting, but their numerical classification results are not wheelchair effect sizes. [Original model-selection bias paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC1397873/).

Priority order: reference validity and acquisition provenance; clock semantics and correspondence diagnostics; physically interpretable calibration; limited residual-model ablations; then an amended, independently evaluated estimator. None of these research suggestions has been implemented or trained in this note.
