"""Evaluate training-selected signal-only offset; paths never refitted/reset.

Reassign saved prediction timestamps relative to the fixed C3D clock. The full
predicted curve is unchanged. This is synchronization sensitivity, not a new
IMU estimator; production scores stay frozen.
"""
import json,csv,time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pipeline as p

OUT=p.ROOT/'outputs_signal_offset_v37';PARENT=p.ROOT/'outputs_dynamic_blend_v34';CLOCK=p.ROOT/'outputs_affine_clock_v36'

def record(row,xy,h,z,mask,name):
    error=np.linalg.norm(xy[mask]-z['reference_xy_m'][mask],axis=1)
    delta=h[mask]-z['reference_heading_rad'][mask];angle=np.arctan2(np.sin(delta),np.cos(delta))
    return dict(id=row['id'],participant=row['participant'],condition=row['condition'],method=name,
                position_rmse_m=float(np.sqrt(np.mean(error**2))),heading_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(angle**2)))),scored_frames=int(mask.sum()))

def main():
    started=time.perf_counter()
    if (OUT/'run.json').exists() or (OUT/'artifact_manifest.json').exists():raise RuntimeError('Preserve immutable experiment')
    OUT.mkdir(exist_ok=True);(OUT/'figures').mkdir(exist_ok=True);(OUT/'trajectories').mkdir(exist_ok=True)
    selection=json.loads((CLOCK/'selection.json').read_text())
    if not selection['selected_before_validation'] or selection['selected']!='offset':raise RuntimeError('Wrong training-selected protocol')
    clocks={q['id']:q for q in csv.DictReader((CLOCK/'clock_trials.csv').open(newline='')) if q['partition']=='validation' and q['method']=='offset'}
    rows={q['id']:q for q in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    manifests={source:json.loads((source/'artifact_manifest.json').read_text())['sha256'] for source in (PARENT,CLOCK)}
    for source,manifest in manifests.items():
        for name,sha in manifest.items():
            if p.digest(source/name)!=sha:raise RuntimeError(f'Parent changed:{source/name}')
    p.save_json(OUT/'protocol.json',dict(hypothesis='Residual signal-selected offset could explain synchronous position error without changing route shape',
          parent_clock='v36 training-selected median8s local signedyaw/calibratedspeed lag, ±100ms,2msgrid',
          eligibility='>=2 accepted nonoverlapping8s windows; otherwise inherited offset unchanged',
          transformation='prediction(t+delta) vs C3D(t); saved physical path and initial pose unchanged; no translation/rotation/scaling/reflection/reset',
          masks='One shared directly observed reference/finite motion interpolation/common-overlap mask for both controls/counterfactuals',
          selection_position_error=False,production_scores_changed=False,reference_assisted=True,deployable_without_C3D=False,test_accessed=False))
    records=[];coverage=[]
    for file in sorted((PARENT/'trajectories').glob('*.npz')):
        row=rows[file.stem];q=clocks[file.stem]
        if row['partition']!='validation':raise RuntimeError('Forbidden split')
        with np.load(file) as source:z={k:source[k] for k in source.files}
        t=z['time_s'];delta=float(q['residual_offset_ms'])/1000 if int(q['windows'])>=2 else 0.
        query=t+delta;common=z['reference_valid']&z['imu_valid'];paths={}
        for model in ('original_v21','selected_blend'):
            xy=z[model+'_xy_m'];heading=z[model+'_heading_rad'];support=z['imu_valid']&np.isfinite(xy).all(1)&np.isfinite(heading)
            channels=[];ok=support.copy()
            for j in range(2):
                values,valid=p.masked_interp(query,t,xy[:,j],support);channels.append(values);ok &= valid
            # Heading unwrapped within valid motion segments, never across gaps.
            unwrapped=heading.copy()
            for a,b in p.runs(support):unwrapped[a:b]=np.unwrap(heading[a:b])
            shifted_h,valid=p.masked_interp(query,t,unwrapped,support);ok &=valid
            shifted=np.column_stack(channels);paths[model]=(xy,heading,shifted,shifted_h);common &=ok
            original_mask=z['reference_valid']&support
            records.append(record(row,xy,heading,z,original_mask,model+'_untrimmed_original'))
        for model,(xy,h,shifted,shifted_h) in paths.items():
            records.extend([record(row,xy,h,z,common,model+'_matched_control'),record(row,shifted,shifted_h,z,common,model+'_signal_offset')])
        covered=int((z['reference_valid']&z['imu_valid']).sum());coverage.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],windows=int(q['windows']),applied_delta_ms=delta*1000,original_observed_frames=covered,common_frames=int(common.sum()),removed_frames=covered-int(common.sum())))
        np.savez_compressed(OUT/'trajectories'/file.name,time_s=t,reference_xy_m=z['reference_xy_m'],reference_valid=z['reference_valid'],common_mask=common,applied_delta_s=delta,
            original_v21_xy_m=paths['original_v21'][0],original_v21_shifted_xy_m=paths['original_v21'][2],selected_blend_xy_m=paths['selected_blend'][0],selected_blend_shifted_xy_m=paths['selected_blend'][2])
    p.write_csv(OUT/'trials.csv',records);p.write_csv(OUT/'coverage.csv',coverage);summary={}
    for method in sorted({r['method'] for r in records}):
        ss,people,maneuvers=p.summarize([r for r in records if r['method']==method]);summary[method]=ss
        p.write_csv(OUT/(method+'_participants.csv'),people);p.write_csv(OUT/(method+'_maneuvers.csv'),maneuvers)
    assert abs(summary['selected_blend_untrimmed_original']['equal_participant_mean_position_rmse_m']-.1007021193993738)<1e-8
    assert abs(summary['original_v21_untrimmed_original']['equal_participant_mean_position_rmse_m']-.10258517940337783)<1e-8
    p.save_json(OUT/'run.json',dict(summary=summary,trials=71,applied_trials=sum(q['windows']>=2 for q in coverage),removed_frames=sum(q['removed_frames'] for q in coverage),test_accessed=False,production_scores_changed=False,runtime_seconds=time.perf_counter()-started,source_sha256=p.digest(Path(__file__))))
    lookup={(q['id'],q['method']):q for q in records};paired=[]
    for q in coverage:
        a=lookup[q['id'],'selected_blend_matched_control'];b=lookup[q['id'],'selected_blend_signal_offset']
        paired.append(dict(q,control_rmse_mm=1000*a['position_rmse_m'],offset_rmse_mm=1000*b['position_rmse_m'],change_mm=1000*(b['position_rmse_m']-a['position_rmse_m'])))
    p.write_csv(OUT/'paired_blend.csv',paired)
    important=[q for q in paired if q['condition']=='10x5']
    fig,axes=plt.subplots(4,3,figsize=(15,14),constrained_layout=True)
    for ax,q in zip(axes.ravel(),important):
        id=q['id'];w=[r for r in csv.DictReader((CLOCK/'clock_windows.csv').open(newline='')) if r['id']==id]
        times=np.array([float(r['center_s']) for r in w]);lags=np.array([float(r['lag_s'])*1000 for r in w]);ax.scatter(times,lags,color='#0072B2',label='8s signal lag');ax.axhline(q['applied_delta_ms'],color='#D55E00',label='median offset');ax.axhline(0,color='grey',ls=':');ax.set_title(id.split('__')[-1]+f"\n{q['control_rmse_mm']:.1f} → {q['offset_rmse_mm']:.1f}mm");ax.set(xlabel='Time (s)',ylabel='Residual lag (ms)',ylim=(-105,105));ax.grid(alpha=.2)
    axes.ravel()[0].legend(fontsize=8);fig.suptitle('Reference-assisted signal timing diagnostic: geometry/model unchanged',fontsize=15);fig.savefig(OUT/'figures/long_10x5_clock.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,3,figsize=(15,11),constrained_layout=True)
    failures=sorted(important,key=lambda q:q['change_mm'])[:3]
    for row,q in enumerate(failures):
        with np.load(OUT/'trajectories'/f"{q['id']}.npz") as zz:z={k:zz[k] for k in zz.files}
        mask=z['common_mask'];t=z['time_s'];a=z['selected_blend_xy_m'];b=z['selected_blend_shifted_xy_m'];ref=z['reference_xy_m'];origin=ref[np.flatnonzero(mask)[0]]
        ax=axes[row,0];ax.plot(*(ref[mask]-origin).T,color='black',label='Observed C3D');ax.plot(*(a-origin).T,color='#0072B2',label='Frozen blend');ax.set_aspect('equal',adjustable='datalim');ax.set(xlabel='X (m)',ylabel='Y (m)',title=q['id'].split('__')[-1]);ax.legend(fontsize=8)
        ax=axes[row,1];ax.plot(t[mask],1000*np.linalg.norm(a[mask]-ref[mask],axis=1),label='Matched control');ax.plot(t[mask],1000*np.linalg.norm(b[mask]-ref[mask],axis=1),label='Signal-clock counterfactual');ax.set(xlabel='Time (s)',ylabel='Position error (mm)',title=f"Lag {q['applied_delta_ms']:.1f}ms: {q['control_rmse_mm']:.1f}→{q['offset_rmse_mm']:.1f}mm");ax.legend(fontsize=8)
        ax=axes[row,2];error=b[mask]-a[mask];ax.plot(t[mask],1000*np.linalg.norm(error,axis=1));ax.set(xlabel='Time (s)',ylabel='Timestamp displacement (mm)',title='Same physical curve, changed correspondence')
    fig.savefig(OUT/'figures/largest_clock_effects.png',dpi=150);plt.close(fig)
    lines=['# Signal-selected clock counterfactual v37','','This is a reference-assisted timestamp reassignment of already-integrated predictions. The route, original initial pose and model are unchanged. Position error never selects offsets. Production100.702119mm remains the model score. Changing training label clocks would require a new refit before attributing gains to an estimator.','', '| Method | RMSE (mm) |','|---|---:|']
    lines +=[f"| {method} | {s['equal_participant_mean_position_rmse_m']*1000:.6f} |" for method,s in summary.items()]
    lines +=['',f"All71 validation recordings retained. {sum(q['windows']>=2 for q in coverage)} have >=2 identifiable windows; others keep inherited clock. Common-overlap removes {sum(q['removed_frames'] for q in coverage)} observed samples, recorded per trial. No arbitrary geometric transform, endpoint snapping, reference reset, or new heading choice. The original initialization was tied to the original clock and is intentionally unchanged; moving-start trials may therefore retain a pose/timing inconsistency. This limits interpretation as fully reinitialized synchronization.",'','## Long10x5 effects','', '| Trial | Signal offset (ms) | Control (mm) | Counterfactual (mm) | Change (mm) |','|---|---:|---:|---:|---:|']
    lines +=[f"| {q['id']} | {q['applied_delta_ms']:.1f} | {q['control_rmse_mm']:.3f} | {q['offset_rmse_mm']:.3f} | {q['change_mm']:+.3f} |" for q in important]
    lines +=['','Short PS/braking records and No5AR2/3 do not support residual skew in the8s window protocol. Their unchanged scores cannot prove zero timing error. Clock data are reference-assisted and reused validation is exploratory.','']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
