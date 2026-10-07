"""Read-only conditional TRAIN No.8 motion decomposition. No model fitting."""
import itertools,json,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pipeline as p
from planar_experiment import integrate_planar

OUT=p.ROOT/'outputs_no8_audit_v46'
SOURCE=p.ROOT/'outputs_clock_arbitrated_folds_v43'
DAMP=p.ROOT/'outputs_clock_damped_v40'

def main():
    if OUT.exists(): raise RuntimeError('Preserve output')
    OUT.mkdir(); (OUT/'plots').mkdir()
    inv={q['id']:q for q in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    seals={q:json.loads((q/'artifact_manifest.json').read_text())['sha256'] for q in (SOURCE,DAMP)}
    ids=sorted(q['id'] for q in inv.values() if q['participant']=='No.8' and (SOURCE/'common_trajectories'/(q['id']+'.npz')).exists())
    cfg=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())['old_clock_settings']
    records=[]; paired=[]; data=[]
    for id in ids:
        assert inv[id]['partition']=='train'
        path=SOURCE/'common_trajectories'/(id+'.npz'); assert p.digest(path)==seals[SOURCE][str(path.relative_to(SOURCE))]
        with np.load(path) as z:a={k:z[k] for k in z.files}
        path=DAMP/'fold_motion'/(id+'.npz'); assert p.digest(path)==seals[DAMP][str(path.relative_to(DAMP))]
        with np.load(path) as z:frozen=z['frozen_new_clock_motion']; assert np.array_equal(z['native_c3d_time_s'],a['native_c3d_time_s'])
        d=dict(t=a['time_s'],gt_xy=a['reference_xy_m'],gt_heading=a['reference_heading_rad'],gt_valid=a['reference_valid'],imu_valid=a['imu_valid'])
        old=a['old_clock_blend_motion']; new=a['new_clock_blend_motion']
        methods={'old':old,'frozen_new_clock':frozen,'new':new}
        for bits in itertools.product((0,1),repeat=3):
            methods['components_'+''.join(map(str,bits))]=np.column_stack([new[:,j] if bit else old[:,j] for j,bit in enumerate(bits)])
        scores={}; tracks={}
        for name,m in methods.items():
            xy,h=integrate_planar(d['t'],m,d['gt_xy'][0],d['gt_heading'][0],d['imu_valid'])
            r=p.metrics(d,xy,h,cfg); records.append(dict(id=id,participant='No.8',condition=inv[id]['condition'],method=name,**r));scores[name]=r;tracks[name]=(xy,h)
        assert np.max(np.abs(tracks['old'][0]-a['old_clock_blend_xy_m']))<1e-10
        assert np.max(np.abs(tracks['new'][0]-a['new_clock_blend_xy_m']))<1e-10
        # Three-component Shapley marginal RMSE contributions; nonlinear interactions distributed equally.
        shap=[]
        import math
        for j in range(3):
            value=0
            for bits in itertools.product((0,1),repeat=3):
                if bits[j]:continue
                n=sum(bits); changed=list(bits);changed[j]=1
                weight=math.factorial(n)*math.factorial(2-n)/math.factorial(3)
                value+=weight*(scores['components_'+''.join(map(str,changed))]['position_rmse_m']-scores['components_'+''.join(map(str,bits))]['position_rmse_m'])
            shap.append(value)
        paired.append(dict(id=id,condition=inv[id]['condition'],old_mm=scores['old']['position_rmse_m']*1000,frozen_mm=scores['frozen_new_clock']['position_rmse_m']*1000,new_mm=scores['new']['position_rmse_m']*1000,
            timing_mm=(scores['frozen_new_clock']['position_rmse_m']-scores['old']['position_rmse_m'])*1000,refit_mm=(scores['new']['position_rmse_m']-scores['frozen_new_clock']['position_rmse_m'])*1000,
            change_mm=(scores['new']['position_rmse_m']-scores['old']['position_rmse_m'])*1000,forward_shapley_mm=shap[0]*1000,lateral_shapley_mm=shap[1]*1000,yaw_shapley_mm=shap[2]*1000,
            old_heading_deg=scores['old']['heading_rmse_deg'],new_heading_deg=scores['new']['heading_rmse_deg'],observed_frames=int(d['gt_valid'].sum())))
        data.append((id,d,tracks))
    p.write_csv(OUT/'trials.csv',records);p.write_csv(OUT/'paired.csv',paired)
    summary={n:p.summarize([q for q in records if q['method']==n])[0] for n in methods}
    maneuver=[]
    for condition in sorted({q['condition'] for q in paired}):
        group=[q for q in paired if q['condition']==condition]
        maneuver.append(dict(condition=condition,trials=len(group),**{k:float(np.mean([q[k] for q in group])) for k in group[0] if k not in ('id','condition')}))
    p.write_csv(OUT/'maneuvers.csv',maneuver)
    ranked=sorted(paired,key=lambda r:r['change_mm'],reverse=True)
    for id,d,tracks in data:
        if id not in {r['id'] for r in ranked[:6]}:continue
        fig,axes=plt.subplots(1,3,figsize=(13,4))
        axes[0].plot(d['gt_xy'][d['gt_valid'],0],d['gt_xy'][d['gt_valid'],1],'k.',ms=.7,label='Observed C3D')
        for name in ('old','frozen_new_clock','new'):
            xy,h=tracks[name];axes[0].plot(xy[:,0],xy[:,1],label=name)
            err=np.linalg.norm(xy-d['gt_xy'],axis=1);err[~d['gt_valid']]=np.nan;axes[1].plot(d['t'],err*1000,label=name)
            hd=np.rad2deg(np.arctan2(np.sin(h-d['gt_heading']),np.cos(h-d['gt_heading'])));hd[~d['gt_valid']]=np.nan;axes[2].plot(d['t'],hd,label=name)
        axes[0].axis('equal');axes[0].legend(fontsize=6);axes[0].set_title('Shared pose, native common support');axes[1].set_title('Observed position error (mm)');axes[2].set_title('Observed heading error (deg)')
        for ax in axes:ax.grid(alpha=.2)
        fig.suptitle(id,fontsize=9);fig.tight_layout();fig.savefig(OUT/'plots'/(id+'.png'),dpi=140);plt.close(fig)
    run=dict(summary=summary,training_only=True,validation_accessed=False,test_accessed=False,trials=len(ids),top_regressions=ranked,mean_decomposition={k:float(np.mean([q[k] for q in paired])) for k in ('timing_mm','refit_mm','forward_shapley_mm','lateral_shapley_mm','yaw_shapley_mm')},source_sha256=p.digest(Path(__file__)))
    p.save_json(OUT/'run.json',run)
    lines=['# No.8 conditional guard audit v46','','Read-only TRAIN No.8 only. Exact v43 common native timestamps, observed support and shared initial pose. Sealed same-fit old fold controls. Frozen new-clock prediction from v40 separates correspondence change from residual refit. No new fit or alignment; inherited calibration/base remain.','',f'{len(ids)} recordings. Old/new mean RMSE: {summary["old"]["equal_participant_mean_position_rmse_m"]*1000:.6f}/{summary["new"]["equal_participant_mean_position_rmse_m"]*1000:.6f} mm.','',json.dumps(run['mean_decomposition'],indent=2),'','## Maneuvers','', '| Maneuver | N | Old mm | Frozen new-clock mm | New mm | Change mm |','|---|---:|---:|---:|---:|---:|']
    lines.extend(f'| {r["condition"]} | {r["trials"]} | {r["old_mm"]:.3f} | {r["frozen_mm"]:.3f} | {r["new_mm"]:.3f} | {r["change_mm"]:+.3f} |' for r in maneuver)
    lines.extend(['','Shapley components average marginal changes over all eight old/new forward/lateral/yaw motion combinations. These are diagnostic interventions, not deployable optical corrections; differences are not physical causal attribution. Timing term also includes timestamp-conditioned features/startup preparation, not pure lag.','', '## Largest regressions','']+[f'- {r["id"]}: {r["old_mm"]:.3f} -> {r["new_mm"]:.3f} mm; frozen {r["frozen_mm"]:.3f}; yaw contribution {r["yaw_shapley_mm"]:+.3f} mm.' for r in ranked[:6]])
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps(dict(mean=run['mean_decomposition'],maneuvers=maneuver,top=ranked[:6]),indent=2))

if __name__=='__main__':main()
