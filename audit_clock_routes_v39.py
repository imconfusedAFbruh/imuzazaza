"""Independent geometric/visual audit of sealed common-native clock refit."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,csv,time
from pathlib import Path
import numpy as np
from pipeline import ROOT,digest,save_json,write_csv,runs
from route_metrics_audit_v36 import pieces,route,length,aggregates,METRICS
from stored_route_audit_v37 import ordered
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=ROOT/'outputs_clock_routes_v39';SOURCE=ROOT/'outputs_clock_refit_v38'
MODELS=('old_clock_blend','new_clock_frozen_blend','new_clock_refit_blend')
COLORS=('#889db6','#79a74c','#e77535')

def independent_integrate(t,m,initial_xy,initial_heading,valid):
    xy=np.full((len(t),2),np.nan);h=np.full(len(t),np.nan);xy[0]=initial_xy;h[0]=initial_heading
    for i in range(1,len(t)):
        if not valid[i-1:i+1].all() or not np.isfinite(xy[i-1]).all():break
        step=.5*(m[i-1]+m[i]);dt=t[i]-t[i-1];h[i]=h[i-1]+step[2]*dt;mid=.5*(h[i]+h[i-1]);co=np.cos(mid);si=np.sin(mid)
        xy[i]=xy[i-1]+dt*np.array([co*step[0]-si*step[1],si*step[0]+co*step[1]])
    return xy,h

def plot(row,z,mask,records):
    t=z['time_s'];ref=z['reference_xy_m'];start=ref[0];fig,axs=plt.subplots(1,3,figsize=(13,4.2));r=ref.copy();r[~mask]=np.nan
    axs[0].plot(*(r-start).T,color='black',lw=1.5,label='Native observed reference')
    for model,color in zip(MODELS,COLORS):
        xy=z[model+'_xy_m'];axs[0].plot(*(xy-start).T,lw=1,color=color,label=model.replace('_',' '));err=np.linalg.norm(xy-ref,axis=1)*1000;err[~mask]=np.nan;axs[1].plot(t,err,color=color,lw=1)
        if model==MODELS[-1]:
            h=z['reference_heading_rad'];delta=xy-ref;along=delta[:,0]*np.cos(h)+delta[:,1]*np.sin(h);cross=-delta[:,0]*np.sin(h)+delta[:,1]*np.cos(h);along[~mask]=np.nan;cross[~mask]=np.nan;axs[2].plot(t,along*1000,label='Along optical heading');axs[2].plot(t,cross*1000,label='Across optical heading')
    axs[0].set_aspect('equal',adjustable='datalim');axs[0].set(xlabel='X from shared initial pose (m)',ylabel='Y (m)',title='Same native support; no fitted alignment');axs[0].legend(fontsize=6)
    axs[1].set(xlabel='Native elapsed time (s)',ylabel='Synchronized error (mm)',title='Direct observed common frames')
    axs[2].set(xlabel='Native elapsed time (s)',ylabel='Refit signed error (mm)',title='Optical heading frame');axs[2].legend(fontsize=7)
    score=' | '.join(f"{r['model'].replace('new_clock_','').replace('old_clock_','old ')} {1000*r['position_rmse_m']:.1f}mm" for r in records)
    fig.suptitle(row['id']+'\n'+score,fontsize=10)
    for ax in axs:ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'figures'/(row['id']+'.png'),dpi=120);plt.close(fig)

def main():
    if OUT.exists():raise RuntimeError('Preserve immutable audit output')
    OUT.mkdir();(OUT/'figures').mkdir();started=time.perf_counter();manifest=json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256'];reported=list(csv.DictReader((SOURCE/'common_native_trials.csv').open()));meta=[r for r in reported if r['method']==MODELS[0]];rows=[];checks=[]
    for i,row in enumerate(meta):
        path=SOURCE/'common_trajectories'/(row['id']+'.npz')
        if digest(path)!=manifest[str(path.relative_to(SOURCE))]:raise RuntimeError('Changed common cache')
        with np.load(path) as zz:z={k:zz[k] for k in zz.files}
        t=z['time_s'];native=z['native_c3d_time_s'];ref=z['reference_xy_m'];valid=z['reference_valid'];imu=z['imu_valid']
        if not np.all(np.diff(t)>0) or not np.array_equal(t,native-native[0]):raise RuntimeError('Invalid native time')
        if not valid[0] or not imu[0]:raise RuntimeError('Initial observed pose unsupported')
        supports=[];errmax=[];hmax=[]
        for model in MODELS:
            xy=z[model+'_xy_m'];h=z[model+'_heading_rad'];supports.append(valid&np.isfinite(xy).all(1))
            if not np.array_equal(xy[0],ref[0]) or h[0]!=z['reference_heading_rad'][0]:raise RuntimeError('Shared pose differs')
            pred,hh=independent_integrate(t,z[model+'_motion'],ref[0],z['reference_heading_rad'][0],imu)
            if not np.array_equal(np.isfinite(pred),np.isfinite(xy)):raise RuntimeError('Integration support differs')
            errmax.append(float(np.nanmax(np.abs(pred-xy))));hmax.append(float(np.nanmax(np.abs(hh-h))))
            if errmax[-1]>1e-10 or hmax[-1]>1e-10:raise RuntimeError('Independent integration differs')
        if not all(np.array_equal(supports[0],s) for s in supports):raise RuntimeError('Common score masks differ')
        mask=supports[0]
        checks.append(dict(id=row['id'],native_frames=len(t),scored_frames=int(mask.sum()),reference_valid_frames=int(valid.sum()),imu_supported_frames=int(imu.sum()),max_position_reintegration_delta_m=max(errmax),max_heading_reintegration_delta_rad=max(hmax),shared_pose=True,native_step_min_s=float(np.min(np.diff(t))),native_step_max_s=float(np.max(np.diff(t)))))
        rr=[];rp=pieces(ref,mask);rl=sum(map(length,rp))
        for model in MODELS:
            xy=z[model+'_xy_m'];pp=pieces(xy,mask);v=route(rp,pp,.01);o=ordered(rp,pp);pl=sum(map(length,pp));r=dict(id=row['id'],participant=row['participant'],condition=row['condition'],model=model,
                position_rmse_m=float(np.sqrt(np.mean(np.sum((xy[mask]-ref[mask])**2,axis=1)))),heading_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(np.arctan2(np.sin(z[model+'_heading_rad'][mask]-z['reference_heading_rad'][mask]),np.cos(z[model+'_heading_rad'][mask]-z['reference_heading_rad'][mask]))**2)))),
                observed_frames=int(mask.sum()),observed_fraction=float(mask.mean()),supported_reference_path_m=rl,supported_prediction_path_m=pl,supported_pathlength_signed_error_m=pl-rl,supported_pathlength_absolute_error_m=abs(pl-rl),supported_last_endpoint_error_m=float(np.linalg.norm(xy[mask][-1]-ref[mask][-1])),true_recording_endpoint_supported=bool(mask[-1]),**v,**o)
            official=next(q for q in reported if q['id']==row['id'] and q['method']==model)
            if abs(r['position_rmse_m']-float(official['position_rmse_m']))>1e-12 or abs(r['heading_rmse_deg']-float(official['heading_rmse_deg']))>1e-12 or r['observed_frames']!=int(official['scored_frames']):raise RuntimeError('Reported trial metric differs')
            rows.append(r);rr.append(r)
        plot(row,z,mask,rr);print(i+1,row['id'],flush=True)
    write_csv(OUT/'trials.csv',rows);write_csv(OUT/'cache_audit.csv',checks)
    summary=aggregates(rows,['model']);write_csv(OUT/'summary.csv',summary);write_csv(OUT/'participants.csv',aggregates(rows,['model','participant']));write_csv(OUT/'maneuvers.csv',aggregates(rows,['model','condition']))
    expected=json.loads((SOURCE/'run.json').read_text())['summary']['common_native']
    for s in summary:
        if abs(s['position_rmse_m']-expected[s['model']]['equal_participant_mean_position_rmse_m'])>1e-12:raise RuntimeError('Aggregate metric mismatch')
    pairs=[]
    for row in meta:
        old=next(r for r in rows if r['id']==row['id'] and r['model']==MODELS[0]);new=next(r for r in rows if r['id']==row['id'] and r['model']==MODELS[-1]);r=dict(id=row['id'],participant=row['participant'],condition=row['condition'])
        for k in METRICS:r[k+'_old']=old[k];r[k+'_new']=new[k];r[k+'_change']=new[k]-old[k]
        pairs.append(r)
    write_csv(OUT/'paired_changes.csv',pairs)
    save_json(OUT/'run.json',dict(summary=summary,models_fixed=True,test_accessed=False,source_script_sha256=digest(Path(__file__)),source_models_sha256={k:digest(SOURCE/k) for k in ['blend_model.json','v21_model.json','tilt_model.json']},runtime_seconds=time.perf_counter()-started,
        independent_checks='Hash verified all71 caches; shared observed initial pose/heading; native time exact; all3 support masks equal; re-integrated each3channel motion using independently written trapezoidal midpoint SE2 routine; reproduced213 reported native trial localization/heading metrics and equalparticipant means.',
        route_convention='Same v36 exact pointtopolyline union,10mm spatial queries, equalbidirectional means; sampledHausdorff;25/50mm perrun discreteFrechet via verifiedreachability. Original native observed mask; no edges across gaps; not fullrouteordered accuracy.',
        regressions={k:sum(r[k+'_change']>0 for r in pairs) for k in METRICS},max_reintegration_position_delta_m=max(r['max_position_reintegration_delta_m'] for r in checks),max_reintegration_heading_delta_rad=max(r['max_heading_reintegration_delta_rad'] for r in checks)))
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
