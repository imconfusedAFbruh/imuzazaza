"""Every observed validation trajectory, paired model errors, and local gallery."""
import argparse
import csv
import html
import importlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import torch

from pipeline import ROOT, digest, metrics, summarize, save_json, write_csv
from planar_experiment import integrate_planar
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from long_horizon_inference import load_endpoint_ensemble

COLORS=['#64748b','#008b8b','#d45b26']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',default='outputs_all_trajectories_review_v10')
    parser.add_argument('--extra-loader',help='module:function returning IMU-only predictor')
    parser.add_argument('--extra-label',default='Training-fitted correction')
    parser.add_argument('--extra-expected',help='Relative sealed trial CSV')
    args=parser.parse_args();out=ROOT/args.out
    if out.exists():raise RuntimeError('Preserve existing plot run')
    torch.set_num_threads(4)
    predictors={'Current ridge':load_observed_ridge(),'Endpoint ensemble':load_endpoint_ensemble()}
    expected_paths={'Current ridge':ROOT/'outputs_observed_ridge_v8/selected_trials.csv',
                    'Endpoint ensemble':ROOT/'outputs_long_horizon_v9/endpoint_ensemble_trials.csv'}
    if args.extra_loader:
        module,function=args.extra_loader.split(':',1)
        predictors[args.extra_label]=getattr(importlib.import_module(module),function)()
        if args.extra_expected:expected_paths[args.extra_label]=ROOT/args.extra_expected
    expected={}
    for name,path in expected_paths.items():
        with path.open(newline='',encoding='utf-8') as stream:
            expected[name]={r['id']:float(r['position_rmse_m']) for r in csv.DictReader(stream)}
    source=ROOT/'outputs_observed_reference_v7'
    cfg=json.loads((source/'run.json').read_text())['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    trials=[];records={name:[] for name in predictors};diagnostics=[]
    for row,data,_ in observed_rows(source,cfg,'validation',manifest):
        sensor={k:data[k] for k in ('setup','t','raw','imu_valid')}
        paths={};headings={};motions={};scores={};error={}
        for name,predict in predictors.items():
            motion=predict(sensor)
            xy,heading=integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
            score=metrics(data,xy,heading,cfg)
            if name in expected and abs(score['position_rmse_m']-expected[name][row['id']])>1e-8:
                raise RuntimeError('Sealed metrics differ: '+row['id']+'/'+name)
            record=dict(id=row['id'],participant=row['participant'],condition=row['condition'],**score)
            records[name].append(record);scores[name]=score
            valid=data['gt_valid']&np.isfinite(xy).all(axis=1)
            e=np.linalg.norm(xy-data['gt_xy'],axis=1);e[~valid]=np.nan
            h=np.rad2deg(np.arctan2(np.sin(heading-data['gt_heading']),np.cos(heading-data['gt_heading'])));h[~valid]=np.nan
            ids=np.flatnonzero(valid)
            diagnostics.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],model=name,
                position_rmse_m=score['position_rmse_m'],last_observed_position_error_m=float(e[ids[-1]]),
                last_observed_heading_error_deg=float(h[ids[-1]]),last_observed_time_s=float(data['t'][ids[-1]]),
                maximum_observed_error_m=float(np.nanmax(e)),observed_fraction=float(valid.mean())))
            paths[name]=xy-data['gt_xy'][0];headings[name]=heading;motions[name]=motion;error[name]=(e,h)
        truth=data['gt_xy']-data['gt_xy'][0];truth[~data['gt_valid']]=np.nan
        trials.append(dict(row=row,data=data,truth=truth,paths=paths,headings=headings,motions=motions,scores=scores,error=error))
    if len(trials)!=71:raise RuntimeError('Changed accepted validation cohort')
    out.mkdir();(out/'individual').mkdir();(out/'trajectories').mkdir()
    summary={}
    for index,(name,rows) in enumerate(records.items()):
        summary[name],people,conditions=summarize(rows)
        for suffix,values in [('trials',rows),('participants',people),('maneuvers',conditions)]:write_csv(out/f'model_{index}_{suffix}.csv',values)
    write_csv(out/'diagnostics.csv',diagnostics)
    with PdfPages(out/'all_71_trajectories.pdf') as pdf:
        for trial in trials:
            row,data=trial['row'],trial['data'];fig,axes=plt.subplots(1,3,figsize=(15,4.6),layout='constrained')
            axes[0].plot(*trial['truth'].T,color='#151515',lw=1.6,label='Observed reference')
            arrays=dict(time_s=data['t'],reference_xy_m=data['gt_xy'],reference_heading_rad=data['gt_heading'],reference_valid=data['gt_valid'],imu_valid=data['imu_valid'])
            for i,name in enumerate(predictors):
                xy=trial['paths'][name];e,h=trial['error'][name]
                axes[0].plot(*xy.T,color=COLORS[i],lw=1.2,ls='--' if i==0 else '-',label=f'{name}: {trial["scores"][name]["position_rmse_m"]*1000:.1f} mm')
                axes[1].plot(data['t'],e*1000,color=COLORS[i],lw=1,label=name)
                axes[2].plot(data['t'],h,color=COLORS[i],lw=1)
                arrays[f'model_{i}_xy_m']=xy+data['gt_xy'][0];arrays[f'model_{i}_heading_rad']=trial['headings'][name];arrays[f'model_{i}_motion']=trial['motions'][name]
            axes[0].scatter(0,0,color='#151515',s=14);axes[0].set_aspect('equal',adjustable='datalim')
            axes[0].set(xlabel='X from initial position (m)',ylabel='Y (m)',title='Trajectory; translation only');axes[0].legend(fontsize=7)
            axes[1].set(xlabel='Time (s)',ylabel='Observed position error (mm)',title='Position drift')
            axes[2].set(xlabel='Time (s)',ylabel='Wrapped heading error (degrees)',title='Heading error')
            for ax in axes:ax.grid(alpha=.2)
            fig.suptitle(row['id'],fontsize=11)
            fig.savefig(out/'individual'/(row['id']+'.png'),dpi=150);pdf.savefig(fig);plt.close(fig)
            np.savez_compressed(out/'trajectories'/(row['id']+'.npz'),**arrays)
    people=['No.5','No.10','No.14','No.18'];conditions=sorted({t['row']['condition'] for t in trials})
    for condition in conditions:
        selected=[t for t in trials if t['row']['condition']==condition]
        positions=np.concatenate([a for t in selected for a in [t['truth'],*t['paths'].values()]])
        lo=np.nanmin(positions,axis=0);hi=np.nanmax(positions,axis=0);pad=np.maximum((hi-lo)*.06,.15);lo-=pad;hi+=pad
        fig,axes=plt.subplots(4,3,figsize=(16,6.5 if condition in ('OS','PS','ST') else 13),layout='constrained')
        by_trial={(t['row']['participant'],int(t['row']['repetition'])):t for t in selected}
        for i,person in enumerate(people):
            for j in range(3):
                ax=axes[i,j];trial=by_trial.get((person,j+1))
                if trial is None:
                    ax.text(.5,.5,'No accepted recording\nSee synchronization/reference QC',ha='center',va='center',transform=ax.transAxes,fontsize=9);ax.set_axis_off();continue
                ax.plot(*trial['truth'].T,color='#151515',lw=1.6,label='Observed reference')
                values=[]
                for k,name in enumerate(predictors):
                    ax.plot(*trial['paths'][name].T,color=COLORS[k],lw=1.2,ls='--' if k==0 else '-',label=name)
                    values.append(f'{trial["scores"][name]["position_rmse_m"]*1000:.0f}')
                ax.set(title=f'{person} · Trial {j+1} · {" / ".join(values)} mm',xlabel='X (m)',ylabel='Y (m)',xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]))
                ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
        for ax in axes.flat:
            if ax.get_legend_handles_labels()[0]:
                ax.legend(fontsize=7,loc='best');break
        fig.suptitle(f'{condition} · all accepted validation trajectories',fontsize=15)
        fig.supxlabel('RMSE order: '+ ' / '.join(predictors)+' · same axes within maneuver; reference gaps remain blank',fontsize=9)
        fig.savefig(out/(condition+'_all.png'),dpi=155);fig.savefig(out/(condition+'_all.svg'));plt.close(fig)
    cards=[]
    for trial in trials:
        row=trial['row'];name=row['id'];rmse=trial['scores']['Current ridge']['position_rmse_m']*1000
        cards.append(f'<article data-key="{html.escape(name.lower())}"><h3>{html.escape(name)}</h3><a href="individual/{html.escape(name)}.png"><img loading="lazy" src="individual/{html.escape(name)}.png"></a><p>Current ridge: {rmse:.1f} mm</p></article>')
    page='<!doctype html><meta charset="utf-8"><title>All validation trajectories</title><style>body{font:16px system-ui;margin:24px;background:#f4f6f8;color:#15232f}input{padding:12px;width:80%;font-size:16px}article{background:white;padding:16px;margin:20px 0;border-radius:8px}img{width:100%}h3{font-size:14px}nav a{margin-right:18px}</style><h1>All 71 validation trajectories</h1><p>Initial pose only. No trajectory alignment, later reference resets, or test recordings. Black: observed reference; gray: current ridge; teal: endpoint ensemble; orange: training-fitted correction (candidate, not promoted).</p><nav><a href="all_71_trajectories.pdf">Download all 71 pages as PDF</a>'+''.join(f'<a href="{c}_all.png">{c}</a>' for c in conditions)+'</nav><p><input id="query" placeholder="Filter by participant, maneuver, or trial"></p>'+''.join(cards)+'<script>document.querySelector("#query").addEventListener("input",e=>{let q=e.target.value.toLowerCase();document.querySelectorAll("article").forEach(a=>a.hidden=!a.dataset.key.includes(q))})</script>'
    (out/'gallery.html').write_text(page,encoding='utf-8')
    save_json(out/'summary.json',dict(models=summary,recordings=71,conditions=conditions,test_evaluated=False,extra_loader=args.extra_loader,
        provenance={str(Path(__file__).relative_to(ROOT)):digest(Path(__file__)),str(source.relative_to(ROOT)/'artifact_manifest.json'):digest(source/'artifact_manifest.json')},
        semantics='Identical camera-observed score support and initial pose; IMU-only predictors; absolute global geometry translated for display only. Heading is not aligned by fitting.'))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
