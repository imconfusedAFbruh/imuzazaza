"""Independent cached-prediction audit; never loads test acquisitions or refits."""
import csv,json,itertools,hashlib,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageOps,ImageDraw
from pipeline import metrics,summarize,write_csv,save_json,digest
from trajectory_calibration_v10 import integrate
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'outputs_dynamic_blend_v34';OUT=ROOT/'outputs_blend_audit_v36'
def read(p):return json.loads(p.read_text())
def table(p):return list(csv.DictReader(p.open(newline='')))
def main():
    if OUT.exists() and '--replot' not in sys.argv:raise RuntimeError('Preserve prior audit; --replot refreshes this audit figure layout only')
    OUT.mkdir(exist_ok=True);figdir=OUT/'figures';figdir.mkdir(exist_ok=True);contacts=OUT/'contacts';contacts.mkdir(exist_ok=True)
    checks={};manifest=read(SRC/'artifact_manifest.json')['sha256']
    bad=[k for k,v in manifest.items() if digest(SRC/k)!=v];assert not bad
    checks['sealed_artifacts_verified']=len(manifest)
    q=read(SRC/'model.json');assert digest(ROOT/q['original_parent'])==q['original_sha256'];assert digest(ROOT/q['dynamic_parent'])==q['dynamic_sha256'];assert digest(ROOT/'dynamic_tilt_experiment_v33.py')==q['feature_source_sha256']
    checks['parent_and_feature_hashes']=True
    assert digest(ROOT/'dynamic_tilt_blend_v34.py')==read(SRC/'run.json')['source_sha256']
    split=read(ROOT/'outputs/split.json')['assignments'];trainids=set(q['training_ids']);assert len(trainids)==473
    original=read(ROOT/q['original_parent']);dynamic=read(ROOT/q['dynamic_parent']);assert set(original['training_ids'])==trainids==set(dynamic['training_ids'])
    rows=table(SRC/'original_v21_trials.csv');assert len(rows)==71
    valids={r['id'] for r in rows};assert not valids&trainids
    assert all(split[r['participant']]=='validation' for r in rows)
    for id in trainids:
        if '_No.' in id:assert split['No.'+id.split('_No.')[-1]]=='train'
    checks['split_and_473_training_ids']=True
    foldrows=table(SRC/'fold_trials.csv');weights=sorted({float(r['weight']) for r in foldrows});base={}
    from participant_folds_experiment_v24 import FOLDS
    def numeric(rr):return [dict(r,position_rmse_m=float(r['position_rmse_m']),heading_rmse_deg=float(r['heading_rmse_deg'])) for r in rr]
    base={p['participant']:p['mean_trial_position_rmse_m'] for p in summarize(numeric([r for r in foldrows if float(r['weight'])==0]))[1]}
    choice=[]
    for w in weights:
        s,pp,_=summarize(numeric([r for r in foldrows if float(r['weight'])==w]));choice.append(dict(weight=w,score=s['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/base[p['participant']] for p in pp)))
    selected=min((r for r in choice if r['worst_person_ratio']<=1.05),key=lambda r:r['score']);assert selected==read(SRC/'selection.json')['selected']
    for i,people in enumerate(FOLDS):
        f=read(SRC/f'fold_{i}_models.json');assert set(f['held_people'])==people
        heldids={r['id'] for r in foldrows if int(r['fold'])==i};assert not heldids&set(f['fit_ids']);assert set(f['fit_ids'])|heldids==trainids
    checks['three_fold_correction_exclusion_and_selection']=True
    cfg=read(ROOT/'outputs_observed_reference_v7/run.json')['settings'];records={n:[] for n in ('original_v21','selected_blend')};paired=[];maxdelta=0.;figs=[]
    for r in rows:
        id=r['id'];z=dict(np.load(SRC/'trajectories'/f'{id}.npz'));old=dict(np.load(ROOT/'outputs_recovered_training_v32/trajectories'/f'{id}.npz'));par=dict(np.load(ROOT/'outputs_dynamic_tilt_v33/trajectories'/f'{id}.npz'))
        for k in ('time_s','reference_xy_m','reference_heading_rad','reference_valid','imu_valid'):
            assert np.array_equal(z[k],old[k],equal_nan=True)
        expected=.25*par['original_v21_motion']+.75*par['tilt_0.3_motion'];assert np.array_equal(z['selected_blend_motion'],expected,equal_nan=True)
        d=dict(t=z['time_s'],gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'],imu_valid=z['imu_valid'])
        fig,axs=plt.subplots(2,3,figsize=(14,8),layout='constrained');origin=z['reference_xy_m'][0];ref=z['reference_xy_m']-origin;ref[~z['reference_valid']]=np.nan
        axs[0,0].plot(*ref.T,c='black',lw=1.3,label='Observed reference')
        processed=old['stored_processed_valid'];display=processed|np.r_[False,processed[:-1]]|np.r_[processed[1:],False];stored=old['stored_reference_xy_m']-origin;stored[~(display&old['stored_reference_valid'])]=np.nan
        axs[0,0].plot(*stored.T,c='#92713a',ls=':',lw=1.5,label='Stored processed (display only)')
        vals={}
        for name,c,ls in [('original_v21','#8d99a7','--'),('selected_blend','#d64c25','-')]:
            xy,h=integrate(d,z[name+'_motion']);assert np.array_equal(xy,z[name+'_xy_m'],equal_nan=True);assert np.array_equal(h,z[name+'_heading_rad'],equal_nan=True)
            result=metrics(d,xy,h,cfg);records[name].append(dict(id=id,participant=r['participant'],condition=r['condition'],**result));vals[name]=result
            axs[0,0].plot(*(xy-origin).T,c=c,ls=ls,lw=1.1,label=name)
            err=xy-z['reference_xy_m'];th=z['reference_heading_rad'];along=err[:,0]*np.cos(th)+err[:,1]*np.sin(th);cross=-err[:,0]*np.sin(th)+err[:,1]*np.cos(th);valid=z['reference_valid']&np.isfinite(xy).all(1)
            pos=np.linalg.norm(err,axis=1)*1000;hd=np.rad2deg(np.arctan2(np.sin(h-th),np.cos(h-th)))
            for ax,arr in [(axs[0,1],pos),(axs[0,2],hd),(axs[1,0],along*1000),(axs[1,1],cross*1000)]:
                arr=arr.copy();arr[~valid]=np.nan;ax.plot(z['time_s'],arr,c=c,ls=ls,lw=1.)
            axs[1,2].plot(z['time_s'],z[name+'_motion'][:,0],c=c,ls=ls,lw=1.)
        delta=(vals['selected_blend']['position_rmse_m']-vals['original_v21']['position_rmse_m'])*1000
        paired.append(dict(id=id,participant=r['participant'],condition=r['condition'],original_mm=vals['original_v21']['position_rmse_m']*1000,blend_mm=vals['selected_blend']['position_rmse_m']*1000,delta_mm=delta))
        axs[0,0].set(aspect='equal',xlabel='X from initial (m)',ylabel='Y (m)',title='Equal physical scale')
        lo,hi=axs[0,0].get_xlim();yl,yh=axs[0,0].get_ylim()
        if yh-yl<.5*(hi-lo):
            ym=(yl+yh)/2;axs[0,0].set_ylim(ym-.25*(hi-lo),ym+.25*(hi-lo))
        handles,labels=axs[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=4,fontsize=8,bbox_to_anchor=(.5,.004));fig.get_layout_engine().set(rect=(0,.06,1,.94))
        for ax,title,y in [(axs[0,1],'Synchronized position error','mm'),(axs[0,2],'Wrapped heading error','degrees'),(axs[1,0],'Along reference heading error','mm'),(axs[1,1],'Cross reference heading error','mm'),(axs[1,2],'Predicted forward velocity','m/s')]:ax.set(title=title,xlabel='Time (s)',ylabel=y)
        for ax in axs.flat:ax.grid(alpha=.2)
        fig.suptitle(f"{id} | {paired[-1]['original_mm']:.2f} → {paired[-1]['blend_mm']:.2f} mm ({delta:+.2f})",fontsize=11)
        path=figdir/f'{id}.png';fig.savefig(path,dpi=115);plt.close(fig);figs.append(path)
    sums={};persons={};conds={}
    for n,rr in records.items():
        sums[n],persons[n],conds[n]=summarize(rr)
        assert abs(sums[n]['equal_participant_mean_position_rmse_m']-read(SRC/'run.json')['summary'][n]['equal_participant_mean_position_rmse_m'])<1e-15
        for suffix,rrr in [('trials',rr),('participants',persons[n]),('maneuvers',conds[n])]:write_csv(OUT/f'{n}_{suffix}.csv',rrr)
    gains=np.array([(a['mean_trial_position_rmse_m']-b['mean_trial_position_rmse_m'])*1000 for a,b in zip(persons['original_v21'],persons['selected_blend'])])
    boot=np.array([np.mean(gains[list(ix)]) for ix in itertools.product(range(4),repeat=4)])
    robustness=dict(person_gain_mm=dict(zip([p['participant'] for p in persons['original_v21']],gains.tolist())),participant_bootstrap_95_percentile_mm=np.quantile(boot,[.025,.975]).tolist(),leave_one_participant_out_gain_mm={persons['original_v21'][i]['participant']:float(np.mean(np.delete(gains,i))) for i in range(4)},improved_trials=sum(p['delta_mm']<0 for p in paired),worsened_trials=sum(p['delta_mm']>0 for p in paired),median_trial_delta_mm=float(np.median([p['delta_mm'] for p in paired])),caution='Four repeatedly inspected participants; bootstrap is descriptive, not prospective confidence or model-selection adjusted evidence.')
    for start in range(0,len(figs),6):
        sheet=Image.new('RGB',(1800,1570),'white')
        for j,p in enumerate(figs[start:start+6]):
            im=Image.open(p);im.thumbnail((895,510));sheet.paste(im,((j%2)*900,(j//2)*520))
        sheet.save(contacts/f'contact_{start//6+1:02}.jpg',quality=95)
    write_csv(OUT/'paired_trials.csv',paired);save_json(OUT/'audit.json',dict(checks=checks,summary=sums,training_selection=selected,robustness=robustness,plots=71,source_hash=digest(Path(__file__)),caveats=['Cached integration/metric independently reproduced; feature/model coefficients not independently retrained.','Inherited base/calibration saw inner held participants; correction folds conditional.','Offline zero-phase filtering and future context are noncausal.','Empirical isotropic gyro scaling and acceleration gravity proxy are not physical SI attitude.','Startup reference position/heading allowed; no later optical pose feedback.']))
    print(json.dumps(dict(summary=sums,robustness=robustness),indent=2))
if __name__=='__main__':main()
