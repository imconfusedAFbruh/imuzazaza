"""CPU reproduced observed-frame diagnostics for selected v14 paths."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json
import csv
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import ROOT,digest,save_json,metrics
from braking_context_inference_v17 import load_braking_context
from observed_ridge_inference import load_observed_ridge
from observed_training_experiment import observed_rows
from trajectory_calibration_v10 import integrate
def main():
    out=ROOT/'outputs_braking_context_diagnostic_plots_v17'
    if out.exists():raise RuntimeError('Preserve plot')
    out.mkdir();torch.set_num_threads(4);source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};baseline=load_observed_ridge();candidate=load_braking_context();expected={r['id']:float(r['position_rmse_m']) for r in csv.DictReader((ROOT/'outputs_braking_context_v17/forward_context_trials.csv').open())};ids={'2026-09-25__PS__PS_Trial2_No.18','2026-09-25__SL__SL_Trial1_No.14','2026-09-25__SL__SL_Trial1_No.18'};rows=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        if row['id'] not in ids:continue
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};sensor['initialization']=states[row['id']];motions={'CPU ridge':baseline(sensor),'v17':candidate(sensor)};fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained');truth=d['gt_xy']-d['gt_xy'][0];truth[~d['gt_valid']]=np.nan;axes[0,0].plot(*truth.T,'k',lw=2,label='Observed reference')
        for name,m in motions.items():
            xy,h=integrate(d,m);score=metrics(d,xy,h,cfg);rows.append(dict(id=row['id'],model=name,**score));axes[0,0].plot(*(xy-d['gt_xy'][0]).T,label=name);error=np.linalg.norm(xy-d['gt_xy'],axis=1);error[~d['gt_valid']]=np.nan;he=np.rad2deg(np.arctan2(np.sin(h-d['gt_heading']),np.cos(h-d['gt_heading'])));he[~d['gt_valid']]=np.nan;axes[0,1].plot(d['t'],error*1000,label=name);axes[1,0].plot(d['t'],he,label=name);axes[1,1].plot(d['t'],m[:,0],label=name)
            if name=='v17' and abs(score['position_rmse_m']-expected[row['id']])>1e-8:raise RuntimeError('Sealed metrics differ')
        axes[1,1].plot(d['t'],np.where(d['label_valid'],d['gt_v'],np.nan),'k',label='Observed speed');axes[0,0].set_aspect('equal');axes[0,0].set_title('2D hub midpoint, initial translation only');axes[0,1].set_title('Observed position error(mm)');axes[1,0].set_title('Observed heading error(deg)');axes[1,1].set_title('Forward speed(m/s)')
        # Give nearly straight paths enough empty Y space for readable ticks.
        from matplotlib.ticker import MaxNLocator
        ymin,ymax=axes[0,0].get_ylim()
        if ymax-ymin<1.:
            centre=(ymin+ymax)/2;axes[0,0].set_ylim(centre-.5,centre+.5);axes[0,0].yaxis.set_major_locator(MaxNLocator(3))
        for ax in axes.flat:ax.grid(alpha=.2);ax.legend(fontsize=8)
        fig.suptitle(row['id']);fig.savefig(out/(row['id']+'.png'),dpi=160);plt.close(fig)
    save_json(out/'scores.json',dict(rows=rows,test_evaluated=False,provenance={__file__:digest(__file__)}))
if __name__=='__main__':main()

