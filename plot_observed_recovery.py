"""Plot the corrected selected estimator, with same-frame old reconstruction."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

from pipeline import ROOT, digest, save_json, metrics
from learning import load_predictor
from planar_experiment import integrate_planar
from observed_reference_experiment import load_planar
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge


def main():
    source,out=ROOT/'outputs_observed_reference_v7',ROOT/'outputs_reference_recovery_v8'
    if out.exists():raise RuntimeError('Preserve existing recovery report')
    torch.set_num_threads(4);out.mkdir();(out/'trajectories').mkdir()
    cfg=json.loads((source/'run.json').read_text())['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    selected=load_observed_ridge();parent=ROOT/'outputs_amended_v2'
    cal=json.loads((parent/'calibration.json').read_text());tcn=load_predictor(parent,'tcn32');champion=load_planar()
    with (ROOT/'outputs_observed_ridge_v8/selected_trials.csv').open(newline='') as file:
        expected={r['id']:r for r in csv.DictReader(file)}
    data_by_id={};records=[]
    for row,data,_ in observed_rows(source,cfg,'validation',manifest):
        motion=selected(data)
        xy,heading=integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
        result=metrics(data,xy,heading,cfg)
        if abs(result['position_rmse_m']-float(expected[row['id']]['position_rmse_m']))>1e-8:
            raise RuntimeError('Selected inference failed to reproduce saved trial')
        origin=data['gt_xy'][0];truth=data['gt_xy'].copy();truth[~data['gt_valid']]=np.nan
        fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
        ax.plot(*(truth-origin).T,color='#222222',linewidth=2,label='Camera-observed MoCap')
        ax.plot(*(xy-origin).T,'--',color='#1676b8',linewidth=1.7,label=f'Selected reconstruction ({result["position_rmse_m"]*1000:.1f} mm)')
        ax.scatter(0,0,s=30,color='#222222');ax.set(title=row['id'],xlabel='X relative to observed initial position (m)',ylabel='Y (m)')
        ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(fontsize=9)
        fig.savefig(out/'trajectories'/(row['id']+'.png'),dpi=160);plt.close(fig)
        data_by_id[row['id']]=(row,data,xy,result)
        records.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**result))
        if len(records)%20==0:print(f'{len(records)}/71 corrected trajectories plotted',flush=True)
    # Keep the same previously displayed failures, rather than selecting easier paths.
    examples=['2026-09-24__OS__OS_Trial3_No.10','2026-09-24__PS__PS_Trial2_No.10']
    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    for i,key in enumerate(examples):
        row,data,xy,result=data_by_id[key]
        with np.load(ROOT/'outputs_synchronization_v5/cache'/(key+'.npz')) as z:old={k:z[k] for k in z.files}
        old_motion=champion(old,cal,tcn)
        old_xy,old_h=integrate_planar(old['t'],old_motion,old['gt_xy'][0],old['gt_heading'][0],old['imu_valid'])
        shift=int(round((data['ref_t'][0]-old['ref_t'][0])*cfg['hz']))
        mask=np.zeros(len(old['t']),bool);mask[shift:]=data['gt_valid']
        old_rmse=metrics(dict(old,gt_valid=mask),old_xy,old_h,cfg)['position_rmse_m']
        origin=data['gt_xy'][0];truth=data['gt_xy'].copy();truth[~data['gt_valid']]=np.nan
        for j,(path,title,color,error) in enumerate([(old_xy[shift:],'Old initialization','#a34c36',old_rmse),
                                                    (xy,'Observed initialization + selected correction','#1676b8',result['position_rmse_m'])]):
            ax=axes[i,j];ax.plot(*(truth-origin).T,color='#222222',linewidth=2,label='Observed MoCap')
            ax.plot(*(path-origin).T,'--',color=color,linewidth=1.8,label='IMU reconstruction')
            ax.scatter(0,0,color='#222222',s=25)
            ax.set(title=f'{row["condition"]} · No.10 · {title}\nRMSE {error*1000:.1f} mm on the same observed frames',
                   xlabel='X relative to observed initial position (m)',ylabel='Y (m)')
            ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('The same failed recordings, before and after correcting reference validity',fontsize=14)
    fig.supxlabel('One initial observed pose; no subsequent reference corrections. Unsupported reference intervals are masked.',fontsize=10)
    for suffix in ('png','svg'):fig.savefig(out/('before_after.'+suffix),dpi=180)
    plt.close(fig)
    reference=json.loads((source/'comparison.json').read_text())['candidates']
    trained=json.loads((ROOT/'outputs_observed_training_v8/selection.json').read_text())
    ridge=json.loads((ROOT/'outputs_observed_ridge_v8/selection.json').read_text())
    values={'old_initialization_same_observed_frames':reference['old_same_observed_frames'],
            'observed_initialization_frozen_neural':reference['corrected_initialization_same_observed_frames'],
            'observed_reference_retrained_neural':trained['candidates']['retrained_planar'],
            'observed_reference_ridge':ridge['best']}
    lines=['# Reference validity recovery and estimator comparison','','The previous C3D reader accepted residual ==0. '
           'An audit of 646 readable training/validation recordings found processed coordinates with no camera support. '
           'Several leading coordinates are deterministic position/heading extrapolations, setting false initial headings. '
           'For PS Trial2 No.10, the old initial heading was -47.465 degrees; the first observed pose is approximately +1.37 degrees. '
           'The amended reader requires positive residuals and camera contributions when masks are populated, before filtering and differentiating.','',
           '| Candidate / protocol | Equal-participant RMSE (mm) |','|---|---:|']
    for name,value in values.items():lines.append(f'| {name} | {value["equal_participant_mean_position_rmse_m"]*1000:.3f} |')
    lines+=['','All entries use the same 71 validation recordings/four participants and camera-observed score frames. '
            'The old reconstruction is not reset, aligned or fitted for comparison; the corrected estimator initializes once '
            'from the first actually observed synchronized pose. The large reduction is chiefly a reference/initialization '
            'protocol correction, not a neural improvement on the old full-duration benchmark. Four training recordings and '
            'one validation recording are newly excluded for insufficient observed labels, leaving 473/477 and71/72 respectively. '
            'Processed prefixes/tails and interior reference gaps are masked; later reference return never resets the estimator.','',
            'Selected development candidate: frozen planar neural estimator plus training-fitted ridge residual (alpha0.1,gain0.25). '
            'It improves all four participant averages against the corrected frozen model, but PS and10x5 condition averages '
            'slightly worsen. Reused validation and one neural seed remain exploratory. Models use1.28s future IMU context. '
            'Clock mapping is inherited from v5; timing/geometry/CSV-unit uncertainties remain unresolved. '
            '116.9mm is not1–10mm accuracy. No test signals were opened.','',
            '[C3D residual specification](https://www.c3d.org/HTML/Documents/gloss_residual.htm). '
            'Source audit: `outputs_reference_support_audit_v7/`. Full exclusion and initialization changes: '
            '`outputs_observed_reference_v7/qc.csv`. Candidate results: `outputs_observed_training_v8/` and `outputs_observed_ridge_v8/`.','',
            '![Same failed recordings before/after](before_after.png)','']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    files=[Path(__file__),ROOT/'observed_training_inference.py',ROOT/'observed_ridge_inference.py',
           ROOT/'outputs_observed_training_v8/selection.json',ROOT/'outputs_observed_ridge_v8/selection.json',source/'artifact_manifest.json']
    save_json(out/'summary.json',dict(selected='observed_reference_ridge',candidates=values,examples=examples,
        recordings=records,test_evaluated=False,provenance={str(f.relative_to(ROOT)):digest(f) for f in files}))
    save_json(out/'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()}))
    print(str(out/'before_after.png'),flush=True)


if __name__=='__main__':main()
