"""Frozen-cache geometric route audit, without fitted transforms or gap edges."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import csv,json,time
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import ROOT,runs,digest,save_json,write_csv

OUT=ROOT/'outputs_route_metrics_v36'
SOURCE=ROOT/'outputs_dynamic_blend_v34'
MODELS=('original_v21','selected_blend')

def pieces(xy,valid):
    return [xy[a:b] for a,b in runs(valid)]

def sample_piece(p,step):
    if len(p)<2:return p.copy()
    s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    keep=np.r_[True,np.diff(s)>1e-12];s=s[keep];p=p[keep]
    if s[-1]<1e-12:return p[:1].copy()
    q=np.linspace(0,s[-1],max(2,int(np.ceil(s[-1]/step))+1))
    return np.c_[np.interp(q,s,p[:,0]),np.interp(q,s,p[:,1])]

def point_to_pieces(query,target):
    """Exact nearest point on supplied closed segments or isolated vertices.

    KD-tree prunes segments provably: nearest vertex supplies an upper bound,
    and a closer segment's midpoint must lie within bound + max half-length.
    All candidates within that bound receive exact clamped projection.
    """
    vertices=np.concatenate(target);vertex_tree=cKDTree(vertices)
    best=vertex_tree.query(query)[0]
    starts=np.concatenate([p[:-1] for p in target if len(p)>1]) if any(len(p)>1 for p in target) else np.empty((0,2))
    ends=np.concatenate([p[1:] for p in target if len(p)>1]) if len(starts) else starts
    if not len(starts):return best
    delta=ends-starts;length2=np.sum(delta**2,axis=1)
    mid=(starts+ends)*.5;radius=.5*np.sqrt(length2).max()
    candidates=cKDTree(mid).query_ball_point(query,best+radius+1e-12)
    for i,idx in enumerate(candidates):
        if not idx:continue
        j=np.asarray(idx);v=delta[j];u=np.clip(np.sum((query[i]-starts[j])*v,axis=1)/np.maximum(length2[j],1e-30),0.,1.)
        best[i]=min(best[i],np.sqrt(np.sum((query[i]-starts[j]-u[:,None]*v)**2,axis=1)).min())
    return best

def weighted_quantile(values,weights,p):
    order=np.argsort(values);v=values[order];w=weights[order]
    return float(v[min(len(v)-1,np.searchsorted(np.cumsum(w)/w.sum(),p))])

def route(ref,pred,step):
    r=np.concatenate([sample_piece(p,step) for p in ref]);q=np.concatenate([sample_piece(p,step) for p in pred])
    d1=point_to_pieces(q,ref);d2=point_to_pieces(r,pred)
    weights=np.r_[np.full(len(d1),.5/len(d1)),np.full(len(d2),.5/len(d2))]
    all_d=np.r_[d1,d2]
    return dict(route_rmse_m=float(np.sqrt(.5*(np.mean(d1*d1)+np.mean(d2*d2)))),
                route_p95_m=weighted_quantile(all_d,weights,.95),sampled_hausdorff_m=float(all_d.max()),
                predicted_to_reference_rmse_m=float(np.sqrt(np.mean(d1*d1))),reference_to_predicted_rmse_m=float(np.sqrt(np.mean(d2*d2))),
                route_query_points_prediction=len(q),route_query_points_reference=len(r))

def frechet(p,q):
    d=cdist(p,q);previous=np.full(len(q),np.inf)
    for i,row in enumerate(d):
        current=np.empty(len(q));current[0]=row[0] if i==0 else max(row[0],previous[0])
        for j in range(1,len(q)):
            current[j]=max(row[j],min(previous[j],previous[j-1],current[j-1]))
        previous=current
    return float(previous[-1])

def length(p):return float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())

def restricted_ordered(ref,pred):
    coarse=[];fine=[];arc_num=0.;arc_den=0.
    for r,p in zip(ref,pred):
        coarse.append(frechet(sample_piece(r,.05),sample_piece(p,.05)))
        fine.append(frechet(sample_piece(r,.025),sample_piece(p,.025)))
        n=max(2,int(np.ceil(max(length(r),length(p))/.01))+1)
        def normalized(x):
            s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(x,axis=0),axis=1))]
            if s[-1]<=1e-12:return np.repeat(x[:1],n,axis=0)
            keep=np.r_[True,np.diff(s)>1e-12];q=np.linspace(0.,s[-1],n)
            return np.c_[np.interp(q,s[keep],x[keep,0]),np.interp(q,s[keep],x[keep,1])]
        e=np.linalg.norm(normalized(r)-normalized(p),axis=1)
        # Equal spatial query weight within each supported run, including run ends.
        arc_num+=float(np.sum(e*e));arc_den+=len(e)
    return dict(supported_run_frechet_max_m=max(fine),supported_run_frechet_coarse_max_m=max(coarse),
                supported_run_frechet_max_abs_refinement_m=float(np.max(np.abs(np.asarray(fine)-coarse))),
                supported_run_arc_correspondence_rmse_m=float(np.sqrt(arc_num/arc_den)),supported_runs=len(ref))

METRICS=('position_rmse_m','route_rmse_m','route_p95_m','sampled_hausdorff_m','supported_last_endpoint_error_m','supported_pathlength_absolute_error_m','supported_run_frechet_max_m','supported_run_arc_correspondence_rmse_m')

def aggregates(rows,groups):
    result=[]
    keys=sorted({tuple(r[g] for g in groups) for r in rows})
    for key in keys:
        subset=[r for r in rows if tuple(r[g] for g in groups)==key]
        people=sorted({r['participant'] for r in subset})
        item=dict(zip(groups,key));item.update(trials=len(subset),participants=len(people))
        for m in METRICS:item[m]=float(np.mean([np.mean([r[m] for r in subset if r['participant']==person]) for person in people]))
        result.append(item)
    return result

def plot_trial(row,z,valid,output):
    t=z['time_s'];ref=z['reference_xy_m'];start=z['original_v21_xy_m'][0]
    fig,axs=plt.subplots(1,3,figsize=(13,4.2));ax=axs[0]
    rr=ref.copy();rr[~valid]=np.nan;ax.plot(*(rr-start).T,color='black',lw=1.5,label='Observed reference')
    for model,color,label in [('original_v21','#809ab9','Original v21'),('selected_blend','#e77535','Tilt blend .75')]:
        p=z[model+'_xy_m'];ax.plot(*(p-start).T,color=color,lw=1,label=label)
        e=np.linalg.norm(p-ref,axis=1);e[~valid]=np.nan;axs[1].plot(t,1000*e,color=color,lw=1,label=label)
        heading=z['reference_heading_rad'];delta=p-ref
        along=delta[:,0]*np.cos(heading)+delta[:,1]*np.sin(heading)
        cross=-delta[:,0]*np.sin(heading)+delta[:,1]*np.cos(heading)
        if model=='selected_blend':
            along[~valid]=np.nan;cross[~valid]=np.nan
            axs[2].plot(t,along*1000,label='Along route');axs[2].plot(t,cross*1000,label='Across route')
    ax.set_aspect('equal',adjustable='datalim');ax.set(xlabel='X from initial position (m)',ylabel='Y (m)',title='Physical aspect; no fitted alignment');ax.legend(fontsize=7)
    axs[1].set(xlabel='Time (s)',ylabel='Synchronized position error (mm)',title='Observed frames only')
    axs[2].set(xlabel='Time (s)',ylabel='Signed component (mm)',title='Blend error in optical heading frame');axs[2].legend(fontsize=8)
    for a in axs:a.grid(alpha=.2)
    fig.suptitle(row['id']+'\nContinuous prediction shown; reference gaps remain disconnected',fontsize=10);fig.tight_layout();fig.savefig(output,dpi=120);plt.close(fig)

def main():
    started=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve sealed output; use next version')
    OUT.mkdir();(OUT/'figures').mkdir()
    manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    meta=list(csv.DictReader((SOURCE/'selected_blend_trials.csv').open()));rows=[]
    for i,row in enumerate(meta):
        path=SOURCE/'trajectories'/(row['id']+'.npz')
        if digest(path)!=manifest[str(path.relative_to(SOURCE))]:raise RuntimeError('Changed cache')
        with np.load(path) as zz:z={k:zz[k] for k in zz.files}
        valid=z['reference_valid'] & np.isfinite(z['reference_xy_m']).all(1)
        # Both models have the same support; explicit guard avoids mismatched scoring.
        valid&=np.isfinite(z['original_v21_xy_m']).all(1)&np.isfinite(z['selected_blend_xy_m']).all(1)
        ref=pieces(z['reference_xy_m'],valid);ref_length=sum(map(length,ref))
        for model in MODELS:
            xy=z[model+'_xy_m'];pred=pieces(xy,valid);v=route(ref,pred,.01);coarse=route(ref,pred,.02)
            record=dict(id=row['id'],participant=row['participant'],condition=row['condition'],model=model,
                position_rmse_m=float(np.sqrt(np.mean(np.sum((xy[valid]-z['reference_xy_m'][valid])**2,axis=1)))),
                observed_frames=int(valid.sum()),observed_fraction=float(valid.mean()),
                supported_reference_path_m=ref_length,supported_prediction_path_m=sum(map(length,pred)),
                supported_last_endpoint_error_m=float(np.linalg.norm(xy[valid][-1]-z['reference_xy_m'][valid][-1])),
                true_recording_endpoint_supported=bool(valid[-1]),
                supported_pathlength_signed_error_m=sum(map(length,pred))-ref_length,
                supported_pathlength_absolute_error_m=abs(sum(map(length,pred))-ref_length),
                route_rmse_refinement_abs_m=abs(v['route_rmse_m']-coarse['route_rmse_m']),
                route_p95_refinement_abs_m=abs(v['route_p95_m']-coarse['route_p95_m']),
                sampled_hausdorff_refinement_abs_m=abs(v['sampled_hausdorff_m']-coarse['sampled_hausdorff_m']),**v,**restricted_ordered(ref,pred))
            record['route_to_synchronized_ratio']=record['route_rmse_m']/record['position_rmse_m'];rows.append(record)
        plot_trial(row,z,valid,OUT/'figures'/(row['id']+'.png'))
        print(i+1,row['id'],flush=True)
    write_csv(OUT/'trials.csv',rows);overall=aggregates(rows,['model']);people=aggregates(rows,['model','participant']);maneuvers=aggregates(rows,['model','condition'])
    write_csv(OUT/'summary.csv',overall);write_csv(OUT/'participants.csv',people);write_csv(OUT/'maneuvers.csv',maneuvers)
    expected=json.loads((SOURCE/'run.json').read_text())['summary']
    for s in overall:
        if abs(s['position_rmse_m']-expected[s['model']]['equal_participant_mean_position_rmse_m'])>1e-12:raise RuntimeError('RMSE reproduction failed')
    paired=[]
    for ident in [r['id'] for r in meta]:
        a=next(r for r in rows if r['id']==ident and r['model']==MODELS[0]);b=next(r for r in rows if r['id']==ident and r['model']==MODELS[1]);p=dict(id=ident,participant=a['participant'],condition=a['condition'])
        for m in METRICS:p[m+'_change_m']=b[m]-a[m]
        paired.append(p)
    write_csv(OUT/'paired_changes.csv',paired)
    save_json(OUT/'run.json',dict(summary=overall,source=str(SOURCE),source_model_hash=digest(SOURCE/'model.json'),source_script_hash=digest(Path(__file__)),runtime_seconds=time.perf_counter()-started,test_accessed=False,
        transforms='None; identical frozen initial pose from original source',
        hypothesis='Some synchronized localization error may be timing or tangential travel mismatch while the geometric route remains close.',
        route_convention='10mm-spaced arc samples in each observed-supported run including endpoints; exact nearest point on union of closed supported polyline edges and isolated points. Direction means receive equal 1/2 weight. P95 is weighted bidirectional quantile. Hausdorff is sampled-point-to-exact-polyline maximum, not continuous exact Hausdorff. 20mm sampling comparison recorded.',
        missing_data='Both curves restricted to same original observed mask for fair geometry comparison; no edges between nonadjacent supported frames. These are partial-route metrics and may hide behavior inside gaps. Initial/last-supported endpoints distinguished from recording endpoint.',
        ordered_convention='Discrete Frechet separately per temporal supported run, maximum over runs, spatial resampling50/25mm with maximum refinement difference; not a full-trial continuous Frechet claim. Arc correspondence independently normalizes each same-support run by its own traveled distance; diagnostic only, no model fitting or pose reset.',
        aggregation='Equal trial mean within participant, then equal participant mean; maneuvers use same convention among available people.',
        regressions={m:sum(p[m+'_change_m']>0 for p in paired) for m in METRICS}))
    fig,axs=plt.subplots(1,2,figsize=(11,4.7))
    colors=plt.cm.tab10.colors
    for j,condition in enumerate(sorted({r['condition'] for r in rows})):
        rr=[r for r in rows if r['model']=='selected_blend' and r['condition']==condition]
        axs[0].scatter([1000*r['position_rmse_m'] for r in rr],[1000*r['route_rmse_m'] for r in rr],label=condition,color=colors[j])
    axs[0].plot([0,450],[0,450],'k:',lw=1);axs[0].set(xlabel='Synchronized RMSE (mm)',ylabel='Symmetric route RMSE (mm)',title='Timing-sensitive localization vs geometric route');axs[0].legend(fontsize=8)
    conditions=sorted({r['condition'] for r in rows});x=np.arange(len(conditions))
    for j,model in enumerate(MODELS):axs[1].bar(x+(j-.5)*.35,[1000*next(r['route_rmse_m'] for r in maneuvers if r['condition']==c and r['model']==model) for c in conditions],.35,label=model)
    axs[1].set(xticks=x,xticklabels=conditions,ylabel='Equal-participant route RMSE (mm)',title='Geometry change by maneuver');axs[1].legend(fontsize=8)
    for a in axs:a.grid(alpha=.15)
    fig.tight_layout();fig.savefig(OUT/'metric_overview.png',dpi=160);plt.close(fig)
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}))
    print(json.dumps(overall,indent=2),flush=True)

if __name__=='__main__':main()
