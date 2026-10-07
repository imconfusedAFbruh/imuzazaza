"""Native marker audit for image-selected rotational trials; no QC amendment."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ezc3d
from pipeline import ROOT,digest,save_json,write_csv,velocities
from observed_reference_experiment import observed_markers

def main():
    out=ROOT/'outputs_rotation_reference_diagnosis_v10'
    if out.exists():raise RuntimeError('Preserve diagnosis')
    out.mkdir();rows=json.loads((ROOT/'outputs_amended_v2/inventory.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())
    stats=[]
    for row in rows:
        if row['partition']!='validation' or row['participant'] not in ('No.5','No.10') or row['condition'] not in ('AR','CR'):continue
        cache=ROOT/'outputs_observed_reference_v7/cache'/(row['id']+'.npz')
        if not cache.exists():continue
        with np.load(cache) as z:data={k:z[k] for k in z.files}
        points,valid,hz=observed_markers(ROOT/row['c3d']);t=np.arange(len(points))/hz
        sep=np.linalg.norm(points[:,0]-points[:,1],axis=1);zheight=points[:,:,2];xy=points[:,:,:2].mean(1);lat=points[:,0,:2]-points[:,1,:2];psi=np.unwrap(np.arctan2(-lat[:,0],lat[:,1]));dpsi=np.diff(psi)*hz
        base=velocities(data,cal[row['setup']]);lab=data['label_valid'];pred=base[lab];gt=np.c_[data['gt_v'][lab],data['gt_yaw'][lab]]
        c=ezc3d.c3d(str(ROOT/row['c3d']));ids=[c['parameters']['POINT']['LABELS']['value'].index(x) for x in ('L_FAL','R_FAL')];res=c['data']['meta_points']['residuals'][0,ids,:].T
        stat=dict(id=row['id'],participant=row['participant'],condition=row['condition'],repetition=row['repetition'],native_duration_s=float(t[-1]),overlap_duration_s=float(data['t'][-1]),native_observed_fraction=float(valid.mean()),sep_median_m=float(np.median(sep[valid])),sep_std_mm=float(np.std(sep[valid])*1000),sep_range_mm=float(np.ptp(sep[valid])*1000),marker_height_std_mm=float(np.std(zheight[valid],axis=0).max()*1000),marker_height_range_mm=float(np.ptp(zheight[valid],axis=0).max()*1000),residual_median=float(np.median(res[valid])),heading_sweep_deg=float(np.rad2deg(np.ptp(psi[valid]))),heading_max_adjacent_deg=float(np.rad2deg(np.abs(np.diff(psi))[valid[:-1]&valid[1:]].max())),reference_xy_range_x_m=float(np.ptp(xy[valid,0])),reference_xy_range_y_m=float(np.ptp(xy[valid,1])),gt_speed_rms=float(np.sqrt(np.mean(gt[:,0]**2))),base_speed_rms=float(np.sqrt(np.mean(pred[:,0]**2))),gt_yaw_rms_deg_s=float(np.rad2deg(np.sqrt(np.mean(gt[:,1]**2)))),base_yaw_rms_deg_s=float(np.rad2deg(np.sqrt(np.mean(pred[:,1]**2)))),forward_corr=float(np.corrcoef(gt[:,0],pred[:,0])[0,1]),yaw_corr=float(np.corrcoef(gt[:,1],pred[:,1])[0,1]),initial_heading_deg=float(np.rad2deg(data['gt_heading'][0])),gt_forward_abs_mean=float(np.abs(gt[:,0]).mean()),base_forward_abs_mean=float(np.abs(pred[:,0]).mean()))
        stats.append(stat)
        if row['participant']!='No.5':continue
        fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
        for i,color in enumerate(('tab:blue','tab:orange')):
            path=points[:,i,:2].copy();path[~valid]=np.nan
            axes[0,0].plot(*path.T,color=color,label=('L','R')[i]);axes[0,2].plot(t,zheight[:,i]*1000,color=color)
        centre=xy.copy();centre[~valid]=np.nan;axes[0,0].plot(*centre.T,'k',label='midpoint');axes[0,0].set_aspect('equal');axes[0,0].legend();axes[0,0].set_title('Native observed marker paths (m)')
        axes[0,1].plot(t,sep*1000);axes[0,1].set_title('Marker separation (mm)');axes[0,2].set_title('Marker height (mm)')
        axes[1,0].plot(t,np.rad2deg(psi));axes[1,0].set_title('Unwrapped native heading (deg)')
        for j,ax in enumerate(axes[1,1:]):
            a=data['gt_v' if j==0 else 'gt_yaw'].copy();a[~lab]=np.nan
            ax.plot(data['t'],a,label='Observed GT');ax.plot(data['t'],base[:,j],label='Physical base');ax.set_title(('Forward speed (m/s)','Yaw rate (rad/s)')[j]);ax.legend()
        for ax in axes.flat:ax.grid(alpha=.2)
        fig.suptitle(row['id']);fig.savefig(out/(row['id']+'.png'),dpi=150);plt.close(fig)
    write_csv(out/'native_audit.csv',stats);save_json(out/'summary.json',dict(trials=stats,test_evaluated=False,provenance={str(__file__):digest(__file__)}));print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
