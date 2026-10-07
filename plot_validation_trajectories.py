"""Plot MoCap and both sealed planar models on refined validation recordings."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

from pipeline import ROOT, digest, save_json, velocities, metrics
from learning import load_predictor
from planar_experiment import planar_features, integrate_planar
from planar_neural_experiment import PlanarResNet, predict_windows
from refined_training_experiment import refined_rows


def read_metrics(path):
    with path.open(newline='') as file:
        return {r['id']:r for r in csv.DictReader(file)}


def path_panel(ax, row, data, paths, scores):
    origin = data['gt_xy'][0]
    truth = data['gt_xy'].copy(); truth[~data['gt_valid']] = np.nan
    ax.plot(*(truth - origin).T, color='#222222', linewidth=2.2, label='MoCap reference')
    for name, color, style in [('existing','#1676b8','--'),('retrained','#d36b16',':')]:
        ax.plot(*(paths[name] - origin).T, color=color, linestyle=style, linewidth=1.8,
                label=f'{name.capitalize()} ({scores[name]*1000:.1f} mm RMSE)')
    ax.scatter(0,0,s=35,color='#222222',zorder=5,marker='o',label='Initial position')
    ax.set(title=f"{row['participant']} · {row['condition']} · {row['id'].split('__')[-1]}",
           xlabel='X relative to initial position (m)', ylabel='Y relative to initial position (m)')
    ax.set_aspect('equal',adjustable='datalim'); ax.grid(alpha=.2); ax.legend(fontsize=8,loc='best')


def main():
    parent, source = ROOT / 'outputs_amended_v2', ROOT / 'outputs_synchronization_v5'
    trained, out = ROOT / 'outputs_refined_training_v6', ROOT / 'outputs_trajectory_plots_v6'
    if out.exists(): raise RuntimeError('Preserve existing trajectory plots')
    selection = json.loads((trained / 'selection.json').read_text())
    for name, sha in selection['provenance'].items():
        if digest(ROOT / name) != sha: raise RuntimeError(f'Model dependency changed: {name}')
    cfg = json.loads((source / 'run.json').read_text())['settings']
    manifest = json.loads((source / 'artifact_manifest.json').read_text())
    cal = json.loads((parent / 'calibration.json').read_text())
    expected = {'existing':read_metrics(trained / 'frozen_planar_reference/validation_metrics.csv'),
                'retrained':read_metrics(trained / 'all_three_trials.csv')}
    if set(expected['existing']) != set(expected['retrained']): raise RuntimeError('Comparison trial IDs differ')
    torch.set_num_threads(4); device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tcn_predict = load_predictor(parent, 'tcn32'); models = {}
    for name, folder in [('existing',ROOT / 'outputs_planar_neural_v4'),('retrained',trained)]:
        checkpoint = torch.load(folder / 'all_three.pt', map_location='cpu', weights_only=True)
        model = PlanarResNet().to(device).eval(); model.load_state_dict(checkpoint['state'])
        norm = json.loads((folder / 'normalization.json').read_text())
        arrays = [np.array(norm[k],np.float32) for k in ('mean','std','target_scale','residual_cap')]
        models[name] = (model,checkpoint['gain'],arrays)
    out.mkdir(); (out / 'recordings').mkdir()
    plt.rcParams.update({'font.size':10,'axes.titlesize':10,'figure.facecolor':'white'})
    plotted, index = {}, []
    for row,data,_ in refined_rows(source,cfg,'validation',manifest):
        base = velocities(data,cal[row['setup']]); tcn = tcn_predict(data,base)
        x = planar_features(data,base,tcn,cal).astype(np.float32)
        paths, scores = {}, {}
        for name,(model,gain,(mean,std,scale,cap)) in models.items():
            residual = gain * np.clip(predict_windows(model,(x-mean)/std,device)*scale,-cap,cap)
            motion = np.c_[tcn[:,0],np.zeros(len(tcn)),tcn[:,1]] + residual
            xy,heading = integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
            score = metrics(data,xy,heading,cfg)['position_rmse_m']
            if abs(score-float(expected[name][row['id']]['position_rmse_m'])) > 1e-8:
                raise RuntimeError(f'Plotted model did not reproduce: {row["id"]}, {name}')
            paths[name],scores[name] = xy,score
        fig,axes = plt.subplots(1,2,figsize=(12,5),layout='constrained')
        path_panel(axes[0],row,data,paths,scores)
        for name,color in [('existing','#1676b8'),('retrained','#d36b16')]:
            error = np.linalg.norm(paths[name]-data['gt_xy'],axis=1)*1000
            error[~data['gt_valid']] = np.nan
            axes[1].plot(data['t'],error,color=color,label=name.capitalize(),linewidth=1.2)
        axes[1].set(xlabel='Elapsed time (s)',ylabel='Position error (mm)',title='Error on valid reference frames')
        axes[1].grid(alpha=.2); axes[1].legend()
        fig.savefig(out / 'recordings' / (row['id']+'.png'),dpi=160); plt.close(fig)
        plotted[row['id']] = (row,data,paths,scores)
        index.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],
                          existing_rmse_mm=scores['existing']*1000,retrained_rmse_mm=scores['retrained']*1000,
                          plot='recordings/'+row['id']+'.png'))
        if len(index)%20==0: print(f'{len(index)}/72 trajectories plotted',flush=True)
    people = sorted({r['participant'] for r in index},key=lambda s:int(s.split('.')[-1]))
    typical = []
    for person in people:
        group = [r for r in index if r['participant']==person]
        median = np.median([r['existing_rmse_mm'] for r in group])
        typical.append(min(group,key=lambda r:abs(r['existing_rmse_mm']-median))['id'])
    hard = [max((r for r in index if r['condition']==condition),key=lambda r:r['existing_rmse_mm'])['id']
            for condition in ('OS','PS')]
    for name,ids,title in [('overview',typical,'Validation trajectories: one recording nearest each participant’s median RMSE'),
                         ('hard_cases',hard,'Validation trajectories: highest existing-model RMSE in OS and PS')]:
        fig,axes = plt.subplots(len(ids)//2,2,figsize=(13,5*len(ids)//2),squeeze=False,layout='constrained')
        for ax,key in zip(axes.flat,ids): path_panel(ax,*plotted[key])
        fig.suptitle(title,fontsize=14)
        fig.supxlabel('Initial reference pose only; identical origin translation for display. Gaps remain masked.',fontsize=10)
        for suffix in ('png','svg'): fig.savefig(out / (name+'.'+suffix),dpi=170)
        plt.close(fig)
    save_json(out / 'index.json',dict(recordings=index,overview_ids=typical,hard_case_ids=hard,
        semantics='Validation only. Existing selected model and best retrained checkpoint against MoCap. '
                  'Common initial-position translation for display; no fitted rotation, scale or trajectory alignment.',
        provenance={str(path.relative_to(ROOT)):digest(path) for path in
            [Path(__file__),trained / 'selection.json',source / 'artifact_manifest.json']},test_evaluated=False))
    save_json(out / 'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*')
                if f.is_file() and f.name!='artifact_manifest.json'}))
    print(str(out / 'overview.png'),flush=True)


if __name__ == '__main__': main()
