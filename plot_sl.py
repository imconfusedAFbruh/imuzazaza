"""SL trajectories: all 12 validation recordings, corrected selected estimator."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

from pipeline import ROOT, metrics, digest, save_json
from planar_experiment import integrate_planar
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge


def main():
    source,out=ROOT/'outputs_observed_reference_v7',ROOT/'outputs_sl_v8'
    torch.set_num_threads(4)
    cfg=json.loads((source/'run.json').read_text())['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    predict=load_observed_ridge()
    with (ROOT/'outputs_observed_ridge_v8/selected_trials.csv').open(newline='') as file:
        expected={r['id']:r for r in csv.DictReader(file) if r['condition']=='SL'}
    panels={};bounds=[]
    for row,data,_ in observed_rows(source,cfg,'validation',manifest):
        if row['condition']!='SL':continue
        motion=predict(data)
        xy,heading=integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
        result=metrics(data,xy,heading,cfg)
        if abs(result['position_rmse_m']-float(expected[row['id']]['position_rmse_m']))>1e-8:
            raise RuntimeError('Selected SL result differs from sealed metrics')
        origin=data['gt_xy'][0];truth=data['gt_xy'].copy();truth[~data['gt_valid']]=np.nan
        truth-=origin;xy-=origin
        panels[(row['participant'],int(row['repetition']))]=(truth,xy,result)
        bounds.extend([truth,xy])
    if len(panels)!=12:raise RuntimeError('Expected all 12 SL validation recordings')
    combined=np.concatenate(bounds);lo=np.nanmin(combined,axis=0)-.25;hi=np.nanmax(combined,axis=0)+.25
    fig,axes=plt.subplots(4,3,figsize=(15,13),layout='constrained')
    people=['No.5','No.10','No.14','No.18']
    for i,person in enumerate(people):
        for j in range(3):
            truth,xy,result=panels[(person,j+1)];ax=axes[i,j]
            ax.plot(*truth.T,color='#222222',linewidth=1.8,label='Camera-observed MoCap')
            ax.plot(*xy.T,'--',color='#1676b8',linewidth=1.5,label='Selected IMU reconstruction')
            ax.scatter(0,0,color='#222222',s=20)
            ax.set(title=f'{person} · Trial {j+1} · RMSE {result["position_rmse_m"]*1000:.1f} mm',
                   xlabel='X from observed initial position (m)',ylabel='Y (m)',xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]))
            ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
    axes[0,0].legend(loc='upper right',fontsize=7,frameon=True)
    fig.suptitle('SL validation trajectories · all participants and repetitions',fontsize=15)
    fig.supxlabel('Common axis limits; translation to the initial position only. Reference gaps remain masked.',fontsize=10)
    out.mkdir(exist_ok=True)
    for suffix in ('png','svg'):fig.savefig(out/('sl_trajectories.'+suffix),dpi=180)
    plt.close(fig)
    save_json(out/'provenance.json',dict(recordings=sorted(expected),test_evaluated=False,
             model='observed-reference planar champion + selected ridge correction',
             source_sha256=digest(Path(__file__)),selection_sha256=digest(ROOT/'outputs_observed_ridge_v8/selection.json')))
    print(str(out/'sl_trajectories.png'),flush=True)


if __name__=='__main__':main()
