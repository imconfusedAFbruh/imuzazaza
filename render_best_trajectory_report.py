"""Reference, ridge and one current candidate from sealed prediction caches."""
import argparse,csv,html,json,re,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pipeline import ROOT,digest,save_json

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    source,out=ROOT/args.source,ROOT/args.out
    if out.exists():raise RuntimeError('Preserve previous rendered report')
    manifest=json.loads((source/'artifact_manifest.json').read_text())['sha256']
    for name,sha in manifest.items():
        if digest(source/name)!=sha:raise RuntimeError('Changed prediction cache '+name)
    summary=json.loads((source/'summary.json').read_text());names=list(summary['models']);candidate=names[2]
    out.mkdir();(out/'individual').mkdir();(out/'trajectories').mkdir()
    rows=list(csv.DictReader((source/'model_0_trials.csv').open(newline='')))
    selected=list(csv.DictReader((source/'model_2_trials.csv').open(newline='')));scores={r['id']:r for r in selected};trials=[]
    for row in rows:
        cache=source/'trajectories'/(row['id']+'.npz')
        with np.load(cache) as z:data={k:z[k].copy() for k in z.files}
        shutil.copy2(cache,out/'trajectories'/cache.name)
        origin=data['reference_xy_m'][0];truth=data['reference_xy_m']-origin;truth[~data['reference_valid']]=np.nan
        paths=[data['model_0_xy_m']-origin,data['model_2_xy_m']-origin]
        trials.append(dict(row=row,data=data,truth=truth,paths=paths,scores=[float(row['position_rmse_m'])*1000,float(scores[row['id']]['position_rmse_m'])*1000]))
    colors=['#8a96a6','#d45b26'];labels=['Original ridge',candidate]
    def paths_on(ax,trial,legend=False):
        ax.plot(*trial['truth'].T,color='#121212',lw=1.7,label='Observed reference')
        for index,(xy,color,label) in enumerate(zip(trial['paths'],colors,labels)):
            ax.plot(*xy.T,color=color,lw=1.1 if index==0 else 1.5,ls='--' if index==0 else '-',alpha=.65 if index==0 else 1,label=label)
        ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2)
        if legend:ax.legend(fontsize=7)
    with PdfPages(out/'all_71_trajectories.pdf') as pdf:
        for trial in trials:
            d=trial['data'];fig,axes=plt.subplots(1,3,figsize=(15,4.3),layout='constrained');paths_on(axes[0],trial,True)
            axes[0].set(xlabel='X from initial position (m)',ylabel='Y (m)',title='Trajectory; equal physical aspect')
            for index,color,label in zip((0,2),colors,labels):
                valid=d['reference_valid']&np.isfinite(d[f'model_{index}_xy_m']).all(axis=1)
                error=np.linalg.norm(d[f'model_{index}_xy_m']-d['reference_xy_m'],axis=1)*1000;error[~valid]=np.nan
                angle=np.rad2deg(np.arctan2(np.sin(d[f'model_{index}_heading_rad']-d['reference_heading_rad']),np.cos(d[f'model_{index}_heading_rad']-d['reference_heading_rad'])));angle[~valid]=np.nan
                axes[1].plot(d['time_s'],error,color=color,lw=1.2,label=label);axes[2].plot(d['time_s'],angle,color=color,lw=1.2)
            axes[1].set(xlabel='Time (s)',ylabel='Position error (mm)',title='Position drift; observed frames only');axes[2].set(xlabel='Time (s)',ylabel='Heading error (degrees)',title='Wrapped heading error')
            for ax in axes[1:]:ax.grid(alpha=.2)
            fig.suptitle(trial['row']['id']+' · RMSE '+ ' → '.join(f'{v:.1f}' for v in trial['scores'])+' mm',fontsize=10)
            fig.savefig(out/'individual'/(trial['row']['id']+'.png'),dpi=150);pdf.savefig(fig);plt.close(fig)
    conditions=sorted({r['condition'] for r in rows})
    for condition in conditions:
        ts=[t for t in trials if t['row']['condition']==condition];combined=np.concatenate([p for t in ts for p in (t['truth'],*t['paths'])]);lo=np.nanmin(combined,axis=0);hi=np.nanmax(combined,axis=0);pad=np.maximum((hi-lo)*.06,.15);lo-=pad;hi+=pad
        lookup={(t['row']['participant'],int(re.search(r'_Trial(\d+)_',t['row']['id'])[1])):t for t in ts};straight=condition in ('OS','PS','ST')
        fig,axes=plt.subplots(4,3,figsize=(16,6.5 if straight else 13),layout='constrained');handles=None
        for i,person in enumerate(('No.5','No.10','No.14','No.18')):
            for j in range(3):
                ax=axes[i,j];trial=lookup.get((person,j+1))
                if trial is None:ax.text(.5,.5,'No accepted recording\nSee synchronization/reference QC',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
                paths_on(ax,trial);ax.set_aspect('equal',adjustable='box');ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),xlabel='X (m)',ylabel='Y (m)',title=f'{person} · Trial{j+1} · '+ ' → '.join(f'{v:.0f}' for v in trial['scores'])+' mm')
                if handles is None:handles=ax.get_legend_handles_labels()
        fig.get_layout_engine().set(rect=(0,.03,1,.88 if straight else .92));fig.legend(*handles,loc='upper center',bbox_to_anchor=(.5,.957 if straight else .977),ncol=3,fontsize=8)
        fig.suptitle(condition+' · all accepted validation trajectories',y=.995,fontsize=15);fig.supxlabel('RMSE: original ridge → candidate. Initial pose only; identical axes within maneuver; reference gaps remain blank.',fontsize=9)
        for extension in ('png','svg'):fig.savefig(out/(condition+'_all.'+extension),dpi=155)
        plt.close(fig)
    cards=[]
    for t in trials:
        name=html.escape(t['row']['id']);cards.append(f'<article data-key="{name.lower()}"><h3>{name}</h3><img loading="lazy" src="individual/{name}.png"><p>RMSE: '+ ' → '.join(f'{v:.1f}' for v in t['scores'])+' mm</p></article>')
    page='<!doctype html><meta charset="utf-8"><title>Current trajectory candidate</title><style>body{font:16px system-ui;margin:24px;background:#f5f7f8}article{background:white;padding:16px;margin:20px 0;border-radius:8px}img{width:100%}input{padding:12px;width:80%;font-size:16px}nav a{margin-right:16px}</style><h1>All71 trajectories: current candidate</h1><p>'+html.escape(candidate)+'. Black: observed reference; gray dashed: original ridge; orange: candidate. No fitted trajectory alignment or later optical pose updates. Validation repeatedly inspected; exploratory, not final test results. 13 planned repetitions unaccepted.</p><nav><a href="all_71_trajectories.pdf">All71 pages PDF</a>'+''.join(f'<a href="{c}_all.png">{c}</a>' for c in conditions)+'</nav><p><input id="q" placeholder="Filter participant, maneuver, trial"></p>'+''.join(cards)+'<script>document.querySelector("#q").oninput=e=>document.querySelectorAll("article").forEach(a=>a.hidden=!a.dataset.key.includes(e.target.value.toLowerCase()))</script>'
    (out/'gallery.html').write_text(page,encoding='utf-8')
    for index,prefix in ((0,'ridge'),(2,'candidate')):
        for suffix in ('trials','participants','maneuvers'):shutil.copy2(source/f'model_{index}_{suffix}.csv',out/f'{prefix}_{suffix}.csv')
    save_json(out/'summary.json',dict(models={names[i]:summary['models'][names[i]] for i in (0,2)},records=71,source_manifest_sha256=digest(source/'artifact_manifest.json'),render_source_sha256=digest(Path(__file__)),test_evaluated=False,comparison='Only original ridge and current candidate shown; complete prior comparisons preserved separately. Optical gaps remain masked; identical prediction caches reused.'))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}))
    print(out/'gallery.html')

if __name__=='__main__':main()
