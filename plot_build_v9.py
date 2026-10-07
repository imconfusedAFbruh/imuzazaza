"""Paired v7 trajectories and error diagnostics for an explicitly named loader."""
import argparse
import csv
import importlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

from pipeline import ROOT, digest, metrics, summarize, save_json, write_csv
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from planar_experiment import integrate_planar


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loader', required=True, help='module:function returning predict(data)')
    parser.add_argument('--label', default='Long-horizon ensemble')
    parser.add_argument('--out', default='outputs_build_trajectories_v9')
    parser.add_argument('--expected', help='Sealed candidate trial CSV, relative to workspace')
    args=parser.parse_args()
    out=ROOT/args.out
    if out.exists(): raise RuntimeError('Preserve prior plot/diagnostic run')
    module,function=args.loader.split(':',1)
    predictor=getattr(importlib.import_module(module),function)()
    control=load_observed_ridge(); torch.set_num_threads(4)
    source=ROOT/'outputs_observed_reference_v7'
    expected={}
    for name,path in [('Current ridge',ROOT/'outputs_observed_ridge_v8/selected_trials.csv'),
                       (args.label,ROOT/args.expected if args.expected else None)]:
        if path:
            with path.open(newline='',encoding='utf-8') as stream:
                expected[name]={r['id']:float(r['position_rmse_m']) for r in csv.DictReader(stream)}
    cfg=json.loads((source/'run.json').read_text())['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    records={'Current ridge':[],args.label:[]}; details=[]; panels={}; bounds=[]
    for row,data,_ in observed_rows(source,cfg,'validation',manifest):
        paths={}
        # Strip all reference fields before either predictor sees a recording.
        sensor={key:data[key] for key in ('setup','t','raw','imu_valid')}
        for name,predict in (('Current ridge',control),(args.label,predictor)):
            motion=predict(sensor)
            xy,heading=integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
            result=metrics(data,xy,heading,cfg)
            if name in expected and abs(result['position_rmse_m']-expected[name][row['id']])>1e-8:
                raise RuntimeError('Inference does not reproduce sealed trial metrics: '+name+'/'+row['id'])
            records[name].append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],**result))
            valid=data['gt_valid']&np.isfinite(xy).all(axis=1)
            observed=np.flatnonzero(valid)
            labels=valid&data['label_valid']&np.isfinite(data['gt_yaw'])
            errors=np.linalg.norm(xy-data['gt_xy'],axis=1)
            details.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],model=name,
                last_observed_position_error_m=float(errors[observed[-1]]),last_observed_time_s=float(data['t'][observed[-1]]),
                last_observed_heading_error_deg=float(np.rad2deg(np.arctan2(np.sin(heading[observed[-1]]-data['gt_heading'][observed[-1]]),np.cos(heading[observed[-1]]-data['gt_heading'][observed[-1]])))),
                turn_frame_rmse_m=float(np.sqrt(np.mean(errors[labels&(np.abs(data['gt_yaw'])>=.25)]**2))) if np.any(labels&(np.abs(data['gt_yaw'])>=.25)) else '',
                straight_frame_rmse_m=float(np.sqrt(np.mean(errors[labels&(np.abs(data['gt_yaw'])<.25)]**2))) if np.any(labels&(np.abs(data['gt_yaw'])<.25)) else '',
                turn_frames=int(np.sum(labels&(np.abs(data['gt_yaw'])>=.25))),straight_frames=int(np.sum(labels&(np.abs(data['gt_yaw'])<.25)))))
            paths[name]=xy-data['gt_xy'][0]
        if row['condition']=='SL':
            truth=data['gt_xy'].copy()-data['gt_xy'][0]; truth[~data['gt_valid']]=np.nan
            panels[(row['participant'],int(row['repetition']))]=(truth,paths,{name:records[name][-1] for name in records})
            bounds.extend([truth,*paths.values()])
    if len(panels)!=12: raise RuntimeError('Changed SL cohort')
    out.mkdir()
    summary={}
    for index,(name,rows) in enumerate(records.items()):
        summary[name],people,conditions=summarize(rows)
        for suffix,values in (('trials',rows),('participants',people),('maneuvers',conditions)):
            write_csv(out/f'model_{index}_{suffix}.csv',values)
    write_csv(out/'drift_turn_straight.csv',details)
    combined=np.concatenate(bounds);lo=np.nanmin(combined,axis=0)-.25;hi=np.nanmax(combined,axis=0)+.25
    fig,axes=plt.subplots(4,3,figsize=(16,13),layout='constrained')
    for i,person in enumerate(('No.5','No.10','No.14','No.18')):
        for j in range(3):
            truth,paths,result=panels[(person,j+1)];ax=axes[i,j]
            ax.plot(*truth.T,color='#222222',lw=1.8,label='Observed reference')
            ax.plot(*paths['Current ridge'].T,'--',color='#8491a3',lw=1.2,label='Current ridge')
            ax.plot(*paths[args.label].T,color='#007f85',lw=1.3,label=args.label)
            old,new=[result[k]['position_rmse_m']*1000 for k in ('Current ridge',args.label)]
            ax.set(title=f'{person} · Trial {j+1} · {old:.1f} → {new:.1f} mm',xlabel='X (m)',ylabel='Y (m)',xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]))
            ax.set_aspect('equal',adjustable='box'); ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('SL · same observed frames and initial pose · no reference resets',fontsize=15)
    for suffix in ('png','svg'):fig.savefig(out/f'sl_comparison.{suffix}',dpi=170)
    plt.close(fig)
    save_json(out/'summary.json',dict(summary=summary,loader=args.loader,expected_table=args.expected,test_evaluated=False,
        turn_definition='Evaluation only: absolute observed yaw rate >=0.25rad/s; derivative-invalid frames excluded from turn/straight breakdown, retained in overall observed-pose score.',
        initial_pose='One observed initial pose; no later reference feedback.',
        provenance={str(Path(__file__).relative_to(ROOT)):digest(Path(__file__)),str(source.relative_to(ROOT)/'artifact_manifest.json'):digest(source/'artifact_manifest.json'),
                    module+'.py':digest(ROOT/(module+'.py'))}))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
