"""Refresh the active experiment journal and empirical epoch chart."""
import json,argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');args=parser.parse_args()
    folder=ROOT/'outputs_trajectory_loop';folder.mkdir(exist_ok=True)
    rows=[]
    specifications=[('Ridge','outputs_observed_ridge_v8/selection.json','best'),
       ('Yaw TCN v12','outputs_yaw_heading_v12/run.json','summary.selected'),
       ('Nonlinear v13','outputs_nonlinear_temporal_v13/run.json','summary.nonlinear'),
       ('Stationary/temporal v14','outputs_stationary_gravity_v14/run.json','summary.stationary_gravity'),
       ('Three-seed yaw v15','outputs_yaw_heading_ensemble_v15/run.json','summary.ensemble'),
       ('Observed endpoint v16','outputs_motion_endpoint_v16/run.json','summary.endpoint'),
       ('Forward context v17','outputs_braking_context_v17/run.json','summary.forward_context'),
       ('Iterative endpoint v19','outputs_motion_endpoint_iterative_v19/run.json','summary.iterative'),
       ('Channel blend v20','outputs_motion_blend_v20/run.json','summary.selected_blend'),
       ('Nonlinear endpoint v21','outputs_nonlinear_endpoint_v21/run.json','summary.selected'),
       ('Stronger endpoint fit v22','outputs_nonlinear_endpoint_tuning_v22/run.json','summary.selected'),
       ('Offline gravity state v23','outputs_adaptive_gravity_v23/run.json','summary.selected'),
       ('Three participant folds v24','outputs_participant_folds_v24/run.json','summary.selected')]
    for name,path,key in specifications:
        p=ROOT/path
        if not p.exists():continue
        value=json.loads(p.read_text(encoding='utf-8'))
        for part in key.split('.'):value=value[part]
        rows.append((name,1000*value['equal_participant_mean_position_rmse_m']))
    lines=['# Trajectory improvement loop','',('Status: completed requested loop; results and plots saved before the usage cutoff. No further fits queued.' if args.final else 'Status: active.')+' Training-fold settings precede final validation evaluation; validation is repeatedly reused and remains exploratory. Frozen test acquisitions are not read. All methods use the observed initial pose only.','', '| Experiment | Overall validation RMSE (mm) |','|---|---:|']
    lines += [f'| {name} | {value:.3f} |' for name,value in rows]
    lines += ['','## Findings driving the next fit','','v12 yaw-only supervision improves aggregate and SL, but worsens No.14 and10x5; no automatic deployment change. v13 nonlinear temporal fit improves the conditional training fold yet worsens validation overall, so it is rejected. v15 reduces seed variability and improves overall/SL but worsens both September25 SL participants.','', 'Images inspected: v12/v13/v14 all-SL contact sheets and v12 No.14 10x5 trial1 three-panel plot. The correction can reduce heading error on that trial while No.14 SL still develops a late bend. Shape overlap alone is insufficient.','', 'v14 improves all four participant averages and all seven maneuver averages, to112.622mm overall/136.853mm SL. Individual regressions remain; PS No18T2 still has433.2mm RMSE. Only one target validation recording has eligible initialstationaryIMU, so the gain is not established as predominantly a mounting correction. Most target acquisitions begin active; qualifying later quiet segments cannot be substituted for initialization-only history.','', 'v16 adds observed interval SE2 constraints to the v14 feature fit. v17 isolates forward velocity temporal context and braking failure. Both retain frozen clocks/reference/initial pose, trainfold selection, and untouched test acquisitions. Complete gyro/mount units remain unverified.','', '## Can more epochs help?','']
    selection=ROOT/'outputs_yaw_heading_v12/inner_selection.json'
    if selection.exists():
        candidates=json.loads(selection.read_text())['candidates'];chosen=[c for c in candidates if c['gain']==.5]
        fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
        ax.plot([c['epoch'] for c in chosen],[1000*c['score'] for c in chosen],'o-',label='Training participant fold; gain0.5')
        baseline=next(c['score'] for c in candidates if c['gain']==0)*1000
        ax.axhline(baseline,color='gray',ls='--',label='Unchanged ridge')
        ax.set(xlabel='Epoch',ylabel='Equal-participant trajectory RMSE (mm)',title='Longer training does not consistently improve trajectory')
        ax.grid(alpha=.2);ax.legend(fontsize=8);fig.savefig(folder/'epochs_vs_trajectory.png',dpi=160);plt.close(fig)
        lines+=['| Epoch | Fixed-fold trajectory RMSE (mm), gain0.5 |','|---:|---:|']+[f'| {c["epoch"]} | {c["score"]*1000:.3f} |' for c in chosen]
        lines+=['','These are training-participant selection results, not a validation-selected epoch sweep. The fold selected epoch12; loss continues falling after12 while trajectory error worsens. Inherited calibration/base previously saw fold participants, so this is conditional selection.']
    lines+=['','## Current strongest candidate','','v21 is the lowest overall error in the completed loop,102.585mm, versus116.899mm paired CPU ridge (12.24% improvement). v16 has a lower SL aggregate,119.725 versus v21 122.943mm. No per-maneuver model selection is used. v21 improves allfour participant and allseven maneuver means versusridge, but allthree No.14 SL trials and No.18 SL1 still regress. The benefit is not uniform.','', 'v19 iterations lower training objective but fail the fold and retainv16. v20 blend retainsv16. v22 stronger endpoint weighting improves training fold but fails validation,116.879mm, especiallyNo.14/18. These negative results remain preserved.','', 'The independent audit reproduces all71v16/v21 scores exactly and confirms predictions ignore supplied reference fields. No fullturn count across optical gaps is inferred; wrapped endpoints are proper orientation targets, and every raw residual beyondπ occurred across gaps. See `research_docs/trajectory-loop-audit.md`.','', '## Artifacts','','Current v21 gallery: `outputs_trajectory_best_v21/gallery.html`, all71 PDF, seven sheets and position/heading timelines. Earlier paired galleries under `outputs_trajectory_plots_v12/`, `outputs_trajectory_plots_v13/`, `outputs_trajectory_report_v14/`, `outputs_trajectory_report_v15/`, `outputs_trajectory_report_v16/` preserve full comparisons. These preserve failed/candidate results, not only favorable trajectories.','', 'The earlier v10 gallery and model remain preserved. All experimental sources, coefficients, epoch checkpoints, participant/maneuver CSVs and manifests remain available under their versioned folders.']
    (folder/'progress.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(f'{name}: {value:.3f}mm' for name,value in rows))

if __name__=='__main__':main()
