"""Read-only diagnostics of frozen validation predictions; no fitting or selection."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from scipy.signal import butter,sosfiltfilt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs_frozen_error_budget';OUT.mkdir(exist_ok=True)
PEOPLE=['No.5','No.10','No.14','No.18'];CONDS=['10x5','AR','CR','OS','PS','SL','ST']
def read(p):return list(csv.DictReader(p.open(encoding='utf-8',newline='')))
def write(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def runs(mask):
    ix=np.flatnonzero(np.diff(np.r_[False,mask,False].astype(int)));return zip(ix[::2],ix[1::2])
def integrate(t,m,h0,xy0,heading=None):
    dt=np.diff(t);avg=(m[1:]+m[:-1])/2
    h=np.r_[h0,h0+np.cumsum(dt*avg[:,2])] if heading is None else heading
    mid=(h[1:]+h[:-1])/2;c,s=np.cos(mid),np.sin(mid)
    delta=dt[:,None]*np.c_[avg[:,0]*c-avg[:,1]*s,avg[:,0]*s+avg[:,1]*c]
    return xy0+np.vstack([np.zeros(2),np.cumsum(delta,axis=0)])
def aggregates(rows,key):
    cells={(p,c):np.mean([float(r[key]) for r in rows if r['participant']==p and r['condition']==c]) for p in PEOPLE for c in CONDS if any(r['participant']==p and r['condition']==c for r in rows)}
    people={p:float(np.mean([float(r[key]) for r in rows if r['participant']==p])) for p in PEOPLE}
    maneuvers={c:float(np.mean([cells[p,c] for p in PEOPLE if (p,c) in cells])) for c in CONDS}
    return dict(equal_participant_mm=float(np.mean(list(people.values()))),equal_participant_equal_available_maneuver_mm=float(np.mean([np.mean([v for (pp,c),v in cells.items() if pp==p]) for p in PEOPLE])),trial_p90_mm=float(np.percentile([float(r[key]) for r in rows],90)),worst_maneuver_mm=max(maneuvers.values()),maneuvers_mm=maneuvers,people_mm=people)

old=ROOT/'outputs_trajectory_best_v21';current=ROOT/'outputs_directional_pivot_v31';parent=ROOT/'outputs_controlled_motion_v25'
tables={k:{r['id']:r for r in read(p)} for k,p in [('v21',old/'candidate_trials.csv'),('v25',parent/'selected_trials.csv'),('v31',current/'selected_trials.csv')]}
trials=list(tables['v31'].values());official=[];segments=[];sensitivity=[];sources={}
for row in trials:
    id=row['id'];p=old/'trajectories'/(id+'.npz');q=current/'selected/trajectories'/(id+'.npz')
    sources[str(p.relative_to(ROOT))]=digest(p);sources[str(q.relative_to(ROOT))]=digest(q)
    with np.load(p) as f:z=dict(f)
    with np.load(q) as f:new=dict(f)
    t=z['time_s'];ref=z['reference_xy_m'];rh=z['reference_heading_rad'];valid=z['reference_valid']&z['imu_valid']&np.isfinite(ref).all(1)&np.isfinite(rh)
    motions={'v21':z['model_2_motion'],'v31':new['motion']}
    r=dict(id=id,participant=row['participant'],condition=row['condition'],ridge_mm=float(np.sqrt(np.nanmean(np.sum((z['model_0_xy_m'][valid]-ref[valid])**2,axis=1))))*1000)
    for k in tables:r[k+'_mm']=float(tables[k][id]['position_rmse_m'])*1000
    official.append(r)
    for version,m in motions.items():
        accum={k:[] for k in ['segment_prediction','reference_yaw','reference_forward','reference_lateral','reference_translation','reference_all_floor']};lengths=[]
        for a,b in runs(valid&np.isfinite(m).all(1)):
            if b-a<100:continue
            tt=t[a:b];hz=1/np.median(np.diff(tt));sos=butter(2,6,fs=hz,output='sos')
            smooth=sosfiltfilt(sos,ref[a:b],axis=0);h=np.unwrap(rh[a:b]);world=np.gradient(smooth,tt,axis=0)
            body=np.c_[world[:,0]*np.cos(h)+world[:,1]*np.sin(h),-world[:,0]*np.sin(h)+world[:,1]*np.cos(h)]
            trim=int(np.ceil(.2*hz));sl=slice(trim,len(tt)-trim);ts=tt[sl];truth=ref[a:b][sl];hs=h[sl];mm=m[a:b][sl];body=body[sl]
            if len(ts)<2:continue
            variants={}
            variants['segment_prediction']=integrate(ts,mm,hs[0],truth[0])
            variants['reference_yaw']=integrate(ts,mm,hs[0],truth[0],hs)
            for key,channels in [('reference_forward',[0]),('reference_lateral',[1]),('reference_translation',[0,1])]:
                alt=mm.copy();alt[:,channels]=body[:,channels];variants[key]=integrate(ts,alt,hs[0],truth[0])
            alt=mm.copy();alt[:,:2]=body;variants['reference_all_floor']=integrate(ts,alt,hs[0],truth[0],hs)
            for key,xy in variants.items():accum[key].extend(np.sum((xy-truth)**2,axis=1))
            lengths.append(float(ts[-1]-ts[0]))
        if not lengths:raise RuntimeError('No observed diagnostic segment '+id)
        segments.append(dict(id=id,participant=row['participant'],condition=row['condition'],version=version,segment_count=len(lengths),scored_frames=len(accum['segment_prediction']),max_segment_s=max(lengths),**{k+'_mm':float(np.sqrt(np.mean(v))*1000) for k,v in accum.items()}))
        # Same interior support for all clock offsets. Fixed hypotheses; never choose the best.
        clockmask=valid&(t>=t[0]+.1)&(t<=t[-1]-.1)
        for shift in [-.1,-.05,-.025,-.01,0,.01,.025,.05,.1]:
            alt=np.column_stack([np.interp(t+shift,t,m[:,j]) for j in range(3)])
            xy=integrate(t,alt,rh[0],ref[0]);score=np.sqrt(np.mean(np.sum((xy[clockmask]-ref[clockmask])**2,axis=1)))*1000
            sensitivity.append(dict(id=id,participant=row['participant'],condition=row['condition'],version=version,type='motion_clock_shift_ms',value=shift*1000,rmse_mm=float(score),support='fixed interior observed frames'))
        base=integrate(t,m,rh[0],ref[0])
        for degrees in [-1,-.5,-.1,0,.1,.5,1]:
            theta=np.deg2rad(degrees);R=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
            xy=ref[0]+(base-ref[0])@R.T;score=np.sqrt(np.mean(np.sum((xy[valid]-ref[valid])**2,axis=1)))*1000
            sensitivity.append(dict(id=id,participant=row['participant'],condition=row['condition'],version=version,type='initial_heading_degrees',value=degrees,rmse_mm=float(score),support='official observed frames'))
        for channel in [0,2]:
            for scale in [.99,1,1.01]:
                alt=m.copy();alt[:,channel]*=scale;xy=integrate(t,alt,rh[0],ref[0]);score=np.sqrt(np.mean(np.sum((xy[valid]-ref[valid])**2,axis=1)))*1000
                sensitivity.append(dict(id=id,participant=row['participant'],condition=row['condition'],version=version,type=('forward' if channel==0 else 'yaw')+'_scale_surrogate_percent',value=(scale-1)*100,rmse_mm=float(score),support='official observed frames; not measured geometry uncertainty'))
write('official_scores.csv',official);write('segment_counterfactuals.csv',segments);write('fixed_sensitivities.csv',sensitivity)
summary={'official':{k:aggregates(official,k+'_mm') for k in ['ridge','v21','v25','v31']},'segments':{},'sensitivities':{},'coverage':{'trials':len(trials),'participants':4,'accepted_by_maneuver':{c:sum(r['condition']==c for r in trials) for c in CONDS}},'no_fit':True,'no_test_access':True}
for v in motions:
    rr=[r for r in segments if r['version']==v];summary['segments'][v]={k:aggregates(rr,k+'_mm') for k in accum}
    summary['sensitivities'][v]={typ:{str(value):aggregates([r for r in sensitivity if r['version']==v and r['type']==typ and r['value']==value],'rmse_mm')['equal_participant_mm'] for value in sorted({r['value'] for r in sensitivity if r['type']==typ})} for typ in sorted({r['type'] for r in sensitivity})}
summary['v21_vs_ridge']={'improve':sum(r['v21_mm']<r['ridge_mm'] for r in official),'regress':sum(r['v21_mm']>r['ridge_mm'] for r in official),'regress_by_maneuver':{c:sum(r['condition']==c and r['v21_mm']>r['ridge_mm'] for r in official) for c in CONDS}}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
fig,axs=plt.subplots(1,2,figsize=(14,5),layout='constrained')
for ax,(left,right,title) in zip(axs,[('v21','ridge','Original v21 minus ridge'),('v31','v25','Directional pivot v31 minus braking v25')]):
    matrix=np.full((4,7),np.nan);labels=np.empty((4,7),dtype=object)
    for i,p in enumerate(PEOPLE):
        for j,c in enumerate(CONDS):
            cell=[r for r in official if r['participant']==p and r['condition']==c]
            matrix[i,j]=np.mean([r[left+'_mm']-r[right+'_mm'] for r in cell]) if cell else np.nan
            labels[i,j]=(f'{matrix[i,j]:+.1f}\nn={len(cell)}' if cell else 'missing')
    im=ax.imshow(matrix,cmap='RdBu_r',vmin=-35,vmax=35,aspect='auto');ax.set(xticks=range(7),xticklabels=CONDS,yticks=range(4),yticklabels=PEOPLE,title=title)
    for (i,j),label in np.ndenumerate(labels):ax.text(j,i,label,ha='center',va='center',fontsize=10,color='white' if abs(matrix[i,j])>23 else 'black')
    fig.colorbar(im,ax=ax,label='Mean trial RMSE change (mm); red = worse')
fig.suptitle('Frozen regression map; missing recordings are not zero error');fig.savefig(OUT/'regression_heatmap.png',dpi=165);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(13,4.5),layout='constrained')
keys=['segment_prediction','reference_yaw','reference_forward','reference_lateral','reference_translation','reference_all_floor'];names=['Segment reset\nprediction','Reference yaw','Reference\nforward','Reference\nlateral','Reference\ntranslation','Reference all\nnumerical floor']
for i,v in enumerate(['v21','v31']):
    vals=[summary['segments'][v][k]['equal_participant_mm'] for k in keys];axs[i].bar(range(6),vals,color=['#506779','#bf722d','#748e83','#a69bb0','#3e8979','#b6c1c7']);axs[i].set(xticks=range(6),xticklabels=names,ylabel='Segment reset RMSE (mm)',title=v+' / shared observed segments')
    for j,val in enumerate(vals):axs[i].text(j,val+1,f'{val:.1f}',ha='center',fontsize=9)
    axs[i].tick_params(axis='x',labelsize=8);axs[i].grid(axis='y',alpha=.2)
fig.suptitle('Counterfactual diagnosis only: replacements are not deployed improvements');fig.savefig(OUT/'counterfactual_budget.png',dpi=165);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for v,col in [('v21','#71849c'),('v31','#d65d24')]:
    for ax,typ,label in [(axs[0],'motion_clock_shift_ms','Motion query shift (ms)'),(axs[1],'initial_heading_degrees','Initial heading perturbation (degrees)')]:
        items=summary['sensitivities'][v][typ];pairs=sorted((float(k),value) for k,value in items.items());xx,yy=zip(*pairs);ax.plot(xx,yy,'o-',label=v,color=col);ax.set(xlabel=label,ylabel='Equal-participant RMSE (mm)');ax.grid(alpha=.2);ax.legend()
fig.suptitle('Fixed sensitivity hypotheses: alignment and starting pose remain unchanged');fig.savefig(OUT/'fixed_sensitivities.png',dpi=165);plt.close(fig)
(OUT/'source_hashes.json').write_text(json.dumps(sources,indent=2))
print(json.dumps({'official':summary['official'],'v21_vs_ridge':summary['v21_vs_ridge'],'segment_means':{v:{k:d['equal_participant_mm'] for k,d in dd.items()} for v,dd in summary['segments'].items()}},indent=2))
