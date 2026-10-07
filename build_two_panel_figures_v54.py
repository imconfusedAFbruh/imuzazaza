from pathlib import Path
import csv,json,hashlib,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path.cwd();out=root/'outputs_pdf_two_panel_v54';out.mkdir(exist_ok=True);(out/'figures').mkdir(exist_ok=True)
source=root/'outputs_clock_arbitrated_v42';manifest=json.loads((source/'artifact_manifest.json').read_text())['sha256']
rows=[r for r in csv.DictReader(open(root/'outputs_clock_routes_v44/trials.csv')) if r['model']=='new_clock_refit_blend']
for row in rows:
    path=source/'common_trajectories'/(row['id']+'.npz');assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[str(path.relative_to(source))]
    with np.load(path) as z:
        t=z['time_s'];ref=z['reference_xy_m'].copy();pred=z['new_clock_refit_blend_xy_m'];valid=z['reference_valid']&np.isfinite(ref).all(1);ref[~valid]=np.nan;origin=z['reference_xy_m'][0]
        radians=z['reference_heading_rad']-z['reference_heading_rad'][0];rh=np.rad2deg(np.arctan2(np.sin(radians),np.cos(radians)));radians=z['new_clock_refit_blend_heading_rad']-z['reference_heading_rad'][0];ph=np.rad2deg(np.arctan2(np.sin(radians),np.cos(radians)));rbreak=np.r_[False,np.abs(np.diff(rh))>180];pbreak=np.r_[False,np.abs(np.diff(ph))>180];rh[~valid|rbreak]=np.nan;ph[pbreak]=np.nan
        fig,axs=plt.subplots(1,2,figsize=(13,5.3),gridspec_kw={'width_ratios':[1,1.25]},layout='constrained')
        axs[0].plot(*(pred-origin).T,color='#d7191c',lw=1.4,label='IMU');axs[0].plot(*(ref-origin).T,color='black',lw=1.3,label='C3D')
        points=np.concatenate([pred[np.isfinite(pred).all(1)]-origin,ref[np.isfinite(ref).all(1)]-origin]);low=points.min(0);high=points.max(0);span=high-low;center=(low+high)/2;xs=max(span[0]*1.1,.1);ys=max(span[1]*1.1,xs*.65,.1);axs[0].set_xlim(center[0]-xs/2,center[0]+xs/2);axs[0].set_ylim(center[1]-ys/2,center[1]+ys/2);axs[0].set_aspect('equal',adjustable='box');axs[0].set(xlabel='X from initial position (m)',ylabel='Y from initial position (m)',title='Trajectory')
        axs[1].plot(t-t[0],ph,color='#d7191c',lw=1.4,label='IMU');axs[1].plot(t-t[0],rh,color='black',lw=1.3,label='C3D');axs[1].set(xlabel='Synchronized elapsed time (s)',ylabel='Yaw from initial heading (degrees, wrapped)',title='Yaw versus time')
        for ax in axs:ax.grid(alpha=.2);ax.legend(loc='best',fontsize=9)
        fig.suptitle(row['id'].replace('__',' | ')+'\nSynchronized 2D RMSE: '+f"{float(row['position_rmse_m'])*1000:.1f} mm",fontsize=11)
        fig.savefig(out/'figures'/(row['id']+'.png'),dpi=150);plt.close(fig)
backup=root/'output/pdf/history';backup.mkdir(exist_ok=True)
pdf=root/'output/pdf/trajectory_research_accuracy_audit.pdf';target=backup/'trajectory_research_accuracy_audit_before_two_panel.pdf'
if not target.exists():shutil.copy2(pdf,target)
s=(root/'report_research_window_v38.py').read_text()
s=s.replace("TMP=ROOT/'tmp/pdfs/research_window_v38'", "TMP=ROOT/'tmp/pdfs/two_panel_v54'").replace("OUT=ROOT/'outputs_research_report_v38'", "OUT=ROOT/'outputs_pdf_two_panel_v54'")
s=s.replace('All 71 accepted validation trajectories remain visible.', 'All 71 accepted validation trajectories remain visible. Plot revision: 5 October 2026; IMU red, C3D black.')
s=s.replace('all71 latest v44 three-panel common-native clock comparisons, with observed reference only and no stored-processed overlay. Along/cross errors are in millimeters.', 'all71 two-panel common-native comparisons: trajectory and yaw versus synchronized time. IMU is red and observed C3D is black; reference gaps stay disconnected. Yaw is shown relative to the shared initial heading and wrapped to -180/+180 degrees; wrap crossings are disconnected. No fitted heading correction is applied.')
s=s.replace('The current nativecommon clock atlas shows oldclockblend blue, newclockfrozen green, newclockrefit orange and nativeobserved reference black.', 'The current nativecommon atlas shows the same signal-arbitrated refit in red and native observed C3D in black. Each page has two panels: trajectory and yaw versus time.')
s=s.replace('Along/cross components use optical heading and are diagnostic, not geometric registration.', 'Yaw is relative to the shared original initial heading; no post-hoc heading correction or spatial registration is applied.')
s=s.replace("image_path=ROOT/(atlas_folder if latest else 'outputs_blend_audit_v36')/'figures'/(row['id']+'.png')", "image_path=OUT/'figures'/(row['id']+'.png')")
s=s.replace('Wheelchair accuracy research | exploratory validation | 2026-10-04', 'Wheelchair accuracy research | exploratory validation | revised 2026-10-05')
s=s.replace('common-native corrected-clock comparison', 'IMU red / C3D black | trajectory and yaw')
(root/'report_two_panel_v54.py').write_text(s,encoding='utf-8')
(out/'plot_provenance.json').write_text(json.dumps(dict(source=str(source),model='new_clock_refit_blend',status='Not promoted; unchanged from previous PDF',trials=71,colors=dict(IMU='red',C3D='black'),yaw='Angular heading relative to common initial heading, wrapped -180/+180 degrees; observed C3D gaps and wrap crossings disconnected',metrics_unchanged=True),indent=2))
print('Created71two-panel figures; previous PDF preserved')
