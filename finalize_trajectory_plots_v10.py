"""Finalize contact sheets from sealed prediction caches; no acquisitions read."""
import csv
import json
import re
import shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pipeline import ROOT,digest,save_json


def main():
    source=ROOT/'outputs_all_trajectories_review_v10';out=ROOT/'outputs_trajectory_report_v10'
    if out.exists():raise RuntimeError('Preserve final artifact')
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    for name,sha in manifest['sha256'].items():
        if digest(source/name)!=sha:raise RuntimeError('Changed plot input: '+name)
    shutil.copytree(source,out)
    models=['Current ridge','Endpoint ensemble','Training-fitted correction'];colors=['#64748b','#008b8b','#d45b26']
    records=[];scores=[]
    for index in range(3):
        with (source/f'model_{index}_trials.csv').open(newline='') as file:
            rows=list(csv.DictReader(file))
        scores.append({r['id']:float(r['position_rmse_m'])*1000 for r in rows})
        if index==0:records=rows
    for condition in sorted({r['condition'] for r in records}):
        selected=[r for r in records if r['condition']==condition];paths={};positions=[]
        for row in selected:
            with np.load(source/'trajectories'/(row['id']+'.npz')) as z:
                origin=z['reference_xy_m'][0];truth=z['reference_xy_m'].copy()-origin;truth[~z['reference_valid']]=np.nan
                estimates=[z[f'model_{i}_xy_m']-origin for i in range(3)]
            repetition=int(re.search(r'_Trial(\d+)_',row['id']).group(1))
            paths[(row['participant'],repetition)]=(row,truth,estimates);positions.extend([truth,*estimates])
        combined=np.concatenate(positions);lo=np.nanmin(combined,axis=0);hi=np.nanmax(combined,axis=0)
        pad=np.maximum((hi-lo)*.06,.15);lo-=pad;hi+=pad
        straight=condition in ('OS','PS','ST')
        fig,axes=plt.subplots(4,3,figsize=(16,6.5 if straight else 13),layout='constrained');handles=None
        for i,person in enumerate(('No.5','No.10','No.14','No.18')):
            for j in range(3):
                ax=axes[i,j];item=paths.get((person,j+1))
                if item is None:
                    ax.text(.5,.5,'No accepted recording\nSee synchronization/reference QC',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
                row,truth,estimates=item;ax.plot(*truth.T,color='#151515',lw=1.6,label='Observed reference')
                for k,(name,xy) in enumerate(zip(models,estimates)):
                    ax.plot(*xy.T,color=colors[k],ls='--' if k==0 else '-',lw=1.2,label=name)
                values=' / '.join(f'{s[row["id"]]:.0f}' for s in scores)
                ax.set(title=f'{person} · Trial {j+1} · {values} mm',xlabel='X (m)',ylabel='Y (m)',xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]))
                ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
                if handles is None:handles=ax.get_legend_handles_labels()
        if straight:
            fig.get_layout_engine().set(rect=(0,.03,1,.88))
            fig.legend(*handles,loc='upper center',bbox_to_anchor=(.5,.958),ncol=4,fontsize=8)
        else:
            for ax in axes.flat:
                if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=7,loc='best');break
        fig.suptitle(f'{condition} · all accepted validation trajectories',fontsize=15,y=.995)
        fig.supxlabel('RMSE order: current ridge / endpoint ensemble / training-fitted correction. Identical axes within maneuver; no fitted trajectory alignment.',fontsize=9)
        for extension in ('png','svg'):fig.savefig(out/f'{condition}_all.{extension}',dpi=155)
        plt.close(fig)
    save_json(out/'render_provenance.json',dict(source_manifest_sha256=digest(source/'artifact_manifest.json'),executed_source_sha256=digest(Path(__file__)),
        changes='Straight-maneuver legends moved outside the thin trajectory axes; compact sheets retain equal physical aspect ratio. Missing recordings are not assigned invented exclusion reasons.',test_evaluated=False))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}))
    print(str(out/'all_71_trajectories.pdf'))


if __name__=='__main__':main()
