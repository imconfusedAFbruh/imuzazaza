"""Audit response, reproducible development freeze, and PDF supplement."""
from pathlib import Path
import json,hashlib
from reportlab.platypus import Image

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs_frozen_error_budget'
PROTOCOL='''# Frozen next-experiment protocol - 4 October 2026

## Decision and status
Stop additional fitting or candidate selection against the reused 71 recordings. Freeze v21, v24, v25 and all completed v26-v31 candidates. v21 remains the lowest observed overall RMSE comparator; v31 is a stricter conditional pivot candidate, not a new blind best model. No final test data were accessed during this diagnostic update. Prior historical test exposure remains disclosed and cannot be undone by a new split label.

## Physical acquisition gates before another model sweep
1. Archive the actual acquisition firmware and CSV receiver/packing source, versions, sensor range registers and timestamp definitions. Actual ranges reported by the user: +/-2 g and +/-2000 degrees/s. Integer CSV encoding remains unverified; do not substitute the older 16 g default.
2. Collect six-orientation stationary accelerometer measurements and controlled known-rate gyro rotations, including rest bias and saturation checks. Determine count-to-SI conversion from source and measurements; record uncertainty rather than inferring it solely from the approximately 8200 rest norm.
3. Measure full 3-D IMU lever-arm vectors and mounting rotation matrices. Wheel sensors are off-axis, outward and mirrored; the center faces backward. These descriptions alone do not define numeric transforms. Use gravity and controlled wheel rotation to constrain independent axes, document signs and residuals.
4. Add a uniquely identifiable physical-front marker or calibrated rigid 3-4-marker cluster; validate hub-midpoint geometry and global coordinate convention against an independent measurement. Quantify absolute reference uncertainty; camera reprojection residual is not that quantity.
5. Add common events observed by every IMU and Qualisys near the start and end; estimate offset and clock-rate drift. Save synchronization residuals and uncertainty. Do not choose alignment from the final trajectory error.
6. Start each recording with 5-10 s deliberate quiet rest. Collect balanced normal rolling, pivot, slalom and mild/medium/aggressive braking/coasting, with independent participant coverage and logged acquisition changes.

## Development participant nesting
Target training participants only: No.1,3,4,6,7,8,13,15,16,17,19,20. Keep every date/recording for a person together before windows. Outer folds: A=3,8,15,20; B=1,4,13,16; C=6,7,17,19. For each outer fold, use the other two groups as two inner participant folds. Refit the complete original neural stack, calibration, normalization, feature fitting and learned preprocessing in every inner fit and then on all eight outer-training participants. No inherited full-training weights or fitted calibration. Deterministic reference/QC rules are frozen; any data-derived choices are made only within the fitting partition. Optical initial pose and per-recording timing remain explicitly declared evaluation inputs; deployment needs independent pose/timing.

The 266 earlier recordings have unmapped identities. Exclude them entirely from nested CV rather than retaining them in every fit. Map identities before considering later use. The historical final population and all repeatedly inspected validation people are development/exposed data, not a fresh blind cohort.

## Finite objective ablation in training folds
A: only endpoint pairs wholly contained in continuously observed optical segments, including all interior frames; no interpolated gap heading.
B: A plus gap-spanning XY endpoint constraints as a separate objective; omit gap-spanning heading unless rotations are independently observed. Wrap observed endpoint angles where appropriate and do not infer hidden complete turns.
Use equal participant -> equal available maneuver -> equal recording -> normalized endpoint weighting. Record missing cells. Compare A/B with the same initialization, epochs, optimizer schedule and architecture. Freeze a finite hyperparameter list before inner runs; no adaptive sweeps against outer or existing validation scores.

## Next physical model
Calibrated wheel/body estimator with body forward/lateral velocity, yaw rate and gyro bias, and bounded wheel-slip states. A small temporal residual predicts constraint relaxation/slip and positive uncertainty; fuse via a consistent SE(2) filter or offline smoother. Handle wheel-stop/body-coast explicitly and require quiet-state evidence for bias updates. Do not manufacture XY corrections or use reference trajectory at inference. Compare physics-only, slip-only, yaw-bias-only, combined and combined-with-uncertainty additions under the same fully refitted nested protocol. Architecture and hyperparameters are selected in inner folds only.

## Predeclared reporting and selection
Primary: equal-participant mean recording XY Euclidean RMSE on observed frames. Also report equal-participant/equal-available-maneuver RMSE, trial P90, worst participant and worst maneuver, heading error, coverage, endpoint drift and uncertainty calibration. Do not score missing cells as zero. Require no more than 5% regression against the matched physics control for any outer held participant or participant-maneuver cell; a failed guard cannot be overridden by lower aggregate RMSE. Use participant bootstrap intervals as descriptive uncertainty, with limited participant count disclosed. Report every accepted recording and every QC exclusion by predeclared reason.

## Blind evaluation
Collect a new participant cohort with complete intended maneuver coverage after measurement gates pass. Freeze code/model hashes, QC thresholds, metrics, synchronization rules and selection decisions before opening that cohort. A custodian retains the data until one final evaluation. No post-evaluation hyperparameter changes or replacement of failures; any later development requires another independent evaluation cohort. Required participant count should be set prospectively from target precision and observed participant variance, not from achieving a desired score.

## Diagnostic limitations
Current official full-recording scores remain unchanged. Counterfactual integrations reset at each continuous observed segment after 0.2 s edge trimming, using segments at least 1 s long and a second-order 6 Hz XY lowpass for reference velocity. All substitutions within a recording share scored frames. The reference-all reconstruction floor describes numerical derivative/integration consistency, not absolute optical accuracy. Initial heading is already optical; there is no independent reference-initial-heading improvement. Yaw +/-0.1/0.5/1 degree, fixed motion time queries +/-10/25/50/100 ms, and forward/yaw motion scales +/-1% are sensitivity hypotheses only. Time queries outside the trace clamp to endpoint values; scoring excludes the first/last 0.1 s. Motion scales are surrogates, not measured geometric error. No best offset or pose is selected. Error components interact and cannot be summed as additive RMSE contributions.
'''

def freeze():
    protocol=ROOT/'research_docs/frozen-next-experiment-protocol.md';protocol.write_text(PROTOCOL,encoding='utf-8')
    folders=['outputs_nonlinear_endpoint_v21','outputs_trajectory_best_v21','outputs_participant_folds_v24','outputs_trajectory_conservative_v24','outputs_controlled_motion_v25','outputs_controlled_refit_v26','outputs_matched_motion_v27','outputs_best_base_braking_v28','outputs_rotation_motion_v29','outputs_pivot_channels_v30','outputs_directional_pivot_v31']
    paths={protocol,ROOT/'frozen_error_budget.py',ROOT/'audit_freeze_report.py',ROOT/'build_rotation_update_v31.py',ROOT/'pipeline.py',ROOT/'learning.py'}
    paths.update(p for p in OUT.glob('*') if p.is_file() and p.name!='development_freeze.json')
    final=ROOT/'output/pdf/trajectory_directional_pivot_report.pdf'
    if final.is_file():paths.add(final)
    for folder in folders:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix.lower() in {'.json','.csv','.pt','.pth','.npz'}:paths.add(p)
    for p in ROOT.glob('*.py'):
        if any(x in p.name for x in ('inference','experiment','selection')):paths.add(p)
    sources=json.loads((OUT/'source_hashes.json').read_text());hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)};hashes.update(sources)
    manifest=dict(date='2026-10-04',status='development frozen; no further reused-validation tuning',scope='candidate artifacts, inference/experiment sources and diagnostic prediction inputs; preserves inherited artifact manifests',sha256=hashes,existing_validation_exposed=True,historical_test_exposure=True,new_test_access=False,full_nested_original_stack_refit_completed=False,physical_conversion_verified=False)
    (OUT/'development_freeze.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def append_audit(story,p,title,table,styles):
    summary=json.loads((OUT/'summary.json').read_text())
    def image(name,maxheight=240):
        im=Image(str(OUT/name));scale=min(475/im.imageWidth,maxheight/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;story.append(im)
    title('Audit response / development is frozen')
    p('The supplied audit reviewed the earlier 109-page report. v29-v31 had already completed before it arrived. All completed candidates are now frozen; no additional model fitting or selection used the 71 repeatedly inspected recordings in this update.')
    p('<b>Model status:</b> v21 is the minimum observed overall-error comparator. v25 is a conservative braking candidate. v31 adds a training-selected pivot correction to v25, with stricter conditional participant-maneuver guards; it does not beat v21 overall. None is a new blind generalization result.')
    data=[['Frozen model','Primary mm','Balanced mm','Trial P90 mm','Worst maneuver mm']]
    for v in ['ridge','v21','v25','v31']:
        r=summary['official'][v];data.append([v]+[f"{r[k]:.3f}" for k in ['equal_participant_mm','equal_participant_equal_available_maneuver_mm','trial_p90_mm','worst_maneuver_mm']])
    table(data,[75,100,100,95,105])
    p('Balanced score first averages recordings within participant-maneuver cells, then available maneuvers within each participant, then participants. Coverage is incomplete: OS has 3 recordings from only two people, PS has 8, and other maneuvers have 12 each. Missing cells are omitted, not zero; this does not establish a complete seven-maneuver population estimate.')
    p('The added freeze manifest hashes model artifacts, experiment/inference sources and all cached predictions used here. It records historical exposure, unverified physical conversion and the fact that a complete nested refit of the original neural stack has not yet been performed.','TinyX')
    title('Regressions / the gains are not uniform')
    image('regression_heatmap.png',240)
    p('Independent recomputation confirms v21 versus ridge improves 59/71 recordings and regresses 12/71: 4 SL, 3 PS, 2 AR and one each 10x5, OS, ST. All 12 CR recordings improve. Colors show average trial RMSE change for each participant-maneuver cell; individual failures can be hidden by a favorable cell mean.')
    p('The v31-v25 improvement is concentrated in AR and No.5. PS, SL, OS and ST remain effectively unchanged. The pivot addition does not address the approximately 0.5 m braking/coasting mismatch identified in No.18 PS2. It also does not settle the physical-front ambiguity in AR2/AR3.')
    p('The next model should explicitly estimate body-wheel disagreement/slip and yaw bias. A larger generic network or longer training is not justified by these results. A participant-maneuver guard is useful, but current folds are conditional on inherited learned parameters and cannot prove independent participant generalization.')
    title('Formal error budget / reference substitutions')
    image('counterfactual_budget.png',200)
    data=[['Segment diagnostic','v21 mm','v31 mm']]
    names={'segment_prediction':'Reset segment prediction','reference_yaw':'Predicted translation + reference yaw','reference_forward':'Reference forward + predicted lateral/yaw','reference_lateral':'Reference lateral + predicted forward/yaw','reference_translation':'Reference translation + predicted yaw','reference_all_floor':'Reference all: numerical consistency floor'}
    for k,name in names.items():data.append([name]+[f"{summary['segments'][v][k]['equal_participant_mm']:.3f}" for v in ['v21','v31']])
    table(data,[305,85,85])
    p('Every one of the 71 recordings contributes. Segment prediction and every substitution use identical frames within each recording. Forward-velocity replacement gives the largest single-channel local reduction. This supports investigating translation/slip; it does not remove evidence of long-horizon yaw drift.','TinyX')
    p('<b>These are diagnostics, not deployed improvements.</b> Each continuously observed segment is reset at its optical position and heading; the smaller baseline is not comparable to official whole-recording RMSE. Reference substitutions have unavailable deployment information. Components interact, so differences are not additive error contributions.','TinyX')
    title('Which failure deserves the next experiment?')
    data=[['v21 observed-segment diagnostic','Prediction mm','Reference yaw mm','Reference forward mm']]
    for c in ['10x5','AR','CR','OS','PS','SL','ST']:
        data.append([c]+[f"{summary['segments']['v21'][k]['maneuvers_mm'][c]:.2f}" for k in ['segment_prediction','reference_yaw','reference_forward']])
    table(data,[190,95,95,95])
    p('PS segment error falls from 176.01 to 51.94 mm when forward velocity is replaced, versus 169.49 mm when only yaw is replaced. This is stronger evidence for a body-translation/braking failure than for a pure yaw failure in PS. The optical substitutions are unavailable at deployment.')
    p('AR also responds strongly to forward replacement. This cannot establish that slip is the cause: uncertain sensor scaling, mounting/sign conventions and the unresolved physical-front ambiguity can produce translation disagreement. Establish the measurement chain before fitting a correction to this pattern.')
    p('SL segment resets deliberately remove the accumulated error before each observed segment. Its 30.38 mm segment diagnostic is much lower than its 122.94 mm official full-recording RMSE. Therefore these local numbers cannot dismiss long-horizon heading or gap-propagation failures. Retain full-recording yaw plots and endpoint diagnostics when designing the next model.')
    p('A replacement can worsen error when channels compensate one another; for example, reference lateral alone increases ST segment error. These comparisons are sensitivities of the coupled integrator, not independent causal shares of total error.')
    title('Error-budget assumptions / pose and timing')
    p('Use contiguous optical/IMU-valid runs of at least 1 s, trim 0.2 s at each edge, and differentiate XY after a second-order 6 Hz lowpass applied inside each observed segment. Reference body translation uses the observed reference heading. Do not propagate reference heading, derivatives or hidden full rotations through gaps. Whole-recording reconstructions and scores remain unchanged.')
    p('The reference-all result near 0.35 mm measures numerical reconstruction consistency after smoothing, not absolute MoCap uncertainty. The original initialization already uses optical heading; replacing it with reference initial heading provides no independent experiment. Physical-front identity is still unresolved for No.5 AR2/AR3.')
    image('fixed_sensitivities.png',190)
    p('Fixed motion query shifts +/-10, 25, 50 and 100 ms use the same observed interior scoring frames; queries outside the trace clamp to endpoint motion. Initial heading hypotheses +/-0.1, 0.5 and 1 degree use unchanged observed frames. No best shift or pose is selected and no clock or reference is rewritten. Separate forward/yaw +/-1% scale sensitivities are motion surrogates, not a quantified geometry uncertainty. Per-recording results are supplied as CSV.','TinyX')
    title('Next experiment / measurement gates first')
    p('<b>Before more tuning:</b> archive actual firmware and receiver encoding; verify count-to-SI conversion with six-orientation rest and known-rate rotations; measure full mounting matrices and 3-D lever arms; validate reference uncertainty and global axes. Actual acceleration range is +/-2 g, not the older 16 g default. Outward mirrored wheel IMUs and backward-facing center are qualitative descriptions, not numeric transforms.')
    p('Add an identifiable front marker or calibrated rigid marker cluster. Add common start/end synchronization events to estimate both offset and rate drift. Deliberately collect 5-10 s initial quiet rest and balanced rolling, pivot, slalom, and graded braking/coasting. The current files cannot supply these missing measurements.')
    p('<b>Full participant nesting:</b> outer groups A=3/8/15/20, B=1/4/13/16, C=6/7/17/19; the other two groups form inner folds. Refit the entire original stack, including calibration, normalization and learned preprocessing, from scratch in every fitting partition. Exclude all 266 earlier unmapped recordings from nested CV until identities are established. Deterministic reference/QC rules stay predeclared; train-derived choices must be nested.')
    p('Clean objective ablation: A uses endpoint pairs wholly inside continuously observed optical segments. B adds gap-spanning XY constraints separately, without assuming unobserved unwrapped heading. Weight participant then maneuver then recording; use matched architecture and training schedule. Freeze finite hyperparameter lists before inner runs.')
    title('Next experiment / frozen evaluation contract')
    p('The proposed model is a calibrated wheel/body estimator with body forward/lateral velocity, yaw rate/bias and bounded wheel-slip states. A small temporal model predicts slip or uncertainty to relax physical constraints, fused through a consistent SE(2) filter or offline smoother. Compare physics-only, slip-only, yaw-bias-only, combined and uncertainty additions under complete nested refits.')
    p('Select only within inner participant folds. Preserve primary equal-participant RMSE; also report the balanced maneuver score, trial P90, worst participant/maneuver, heading, coverage, endpoint drift and uncertainty calibration. Require at most 5% regression for any held participant or participant-maneuver cell versus the matched physics control. Report all accepted recordings and predeclared QC failures.')
    p('For a defensible final claim, collect new participants after measurement gates pass. Freeze code, model hashes, QC, timing and metrics before the cohort is opened; evaluate once. Previously inspected validation and historical exposed test participants cannot serve as a new blind test. Set new cohort size prospectively from target precision and participant variance.')
    p('This update implements the computable error budget, heatmap, additional metrics and version freeze. Physical calibration data collection and full nested neural refits remain pending. No improved blind accuracy or 1-10 mm capability is claimed.')
    p('Reproducible files: frozen_error_budget.py; outputs_frozen_error_budget/summary.json, segment_counterfactuals.csv, fixed_sensitivities.csv, development_freeze.json; research_docs/frozen-next-experiment-protocol.md.','TinyX')

if __name__=='__main__':
    m=freeze();print('Frozen artifacts:',len(m['sha256']))
