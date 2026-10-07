"""Read-only PS acceleration deficit and raw-extrema diagnostic."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import ROOT,save_json,digest,write_csv

def main():
    trial='2026-09-25__PS__PS_Trial2_No.18';source=ROOT/'outputs_observed_reference_v7';out=ROOT/'outputs_acceleration_diagnosis_v10'
    if out.exists():raise RuntimeError('Preserve diagnosis')
    out.mkdir();d=dict(np.load(source/'cache'/(trial+'.npz')));z=dict(np.load(ROOT/'outputs_all_trajectories_v10/trajectories'/(trial+'.npz')))
    cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text())['2026-09-25'];raw=d['raw'];t=d['t']
    wheels=np.c_[*[raw[:,term['column']]*term['scale']+term['intercept'] for term in cal['terms'][:2]]]
    acc=np.c_[*[np.linalg.norm(raw[:,i*6:i*6+3],axis=1)/cal['accel_counts_per_g'][i] for i in range(3)]]
    metrics=[]
    for start,end in [(0,1.5),(1.5,2.8),(2.8,5.8)]:
        mask=(t>=start)&(t<=end)&d['label_valid'];a,b=np.searchsorted(t,[start,end]);b=min(b,len(t)-1)
        for name,k in [('ridge',0),('endpoint',1)]:
            m=z[f'model_{k}_motion'];xy=z[f'model_{k}_xy_m'];h0=d['gt_heading'][0];direction=np.array([np.cos(h0),np.sin(h0)])
            delta_error=(xy[b]-d['gt_xy'][b])-(xy[a]-d['gt_xy'][a])
            metrics.append(dict(model=name,start_s=start,end_s=end,valid_labels=int(mask.sum()),mean_forward_error_mps=float(np.mean(m[mask,0]-d['gt_v'][mask])),
                forward_error_integral_on_adjacent_valid_labels_m=float(np.sum(np.diff(t[a:b+1])*((m[a:b,0]-d['gt_v'][a:b])+(m[a+1:b+1,0]-d['gt_v'][a+1:b+1]))/2,where=d['label_valid'][a:b]&d['label_valid'][a+1:b+1])),along_initial_direction_position_error_change_m=float(delta_error@direction),
                mean_wheel_midpoint_error_mps=float(np.mean(wheels[mask].mean(axis=1)-d['gt_v'][mask]))))
    csvpath=ROOT/'imu3/2026-09-25/imu/PS/PS_Trial2_No.18.csv';csv=pd.read_csv(csvpath);extrema=[]
    for sensor in ('L','R','C'):
        rows=csv[csv.wheel==sensor]
        for column in ('ax_raw','ay_raw','az_raw','gx_raw','gy_raw','gz_raw'):
            values=rows[column].to_numpy();lo,hi=int(values.min()),int(values.max());same=values[1:]==values[:-1]
            at_extreme=same&((values[1:]==lo)|(values[1:]==hi))
            edges=np.diff(np.r_[False,at_extreme,False].astype(int));lengths=np.flatnonzero(edges==-1)-np.flatnonzero(edges==1)
            extrema.append(dict(sensor=sensor,column=column,minimum=lo,maximum=hi,min_count=int(np.sum(values==lo)),max_count=int(np.sum(values==hi)),longest_repeated_extreme_samples=int(max(lengths,default=0)+1),boundary_16384_count=int(np.sum(np.abs(values)>=16383)),boundary_32768_count=int(np.sum(np.abs(values)>=32767))))
    fig,ax=plt.subplots(3,1,figsize=(12,9),sharex=True)
    ax[0].plot(t,np.where(d['label_valid'],d['gt_v'],np.nan),'k',label='Observed derivative forward speed')
    ax[0].plot(t,wheels.mean(axis=1),label='Empirical wheel midpoint')
    for name,k in [('Ridge',0),('Endpoint',1)]:ax[0].plot(t,z[f'model_{k}_motion'][:,0],label=name)
    ax[0].set_ylabel('Forward speed (m/s)');ax[0].legend()
    for i,name in enumerate(('L','R','C')):ax[1].plot(t,acc[:,i],label=name+' accel norm / training gravity norm')
    ax[1].set_ylabel('Empirical g equivalent');ax[1].legend()
    for i,name in enumerate(('L','R')):ax[2].plot(t,.04*(wheels[:,i]/.30)**2/9.80665,label=name+' centripetal estimate')
    ax[2].axhline(2,color='k',ls='--',label='2 g reference (not a norm limit)');ax[2].set_ylabel('Centripetal estimate (g)');ax[2].set_xlabel('Time (s)');ax[2].legend()
    for axis in ax:axis.grid(alpha=.2);axis.axvspan(1.5,2.8,color='red',alpha=.08)
    fig.suptitle('PS No.18 Trial 2: persistent acceleration displacement deficit');fig.tight_layout();fig.savefig(out/'acceleration_signals.png',dpi=160);plt.close(fig)
    write_csv(out/'intervals.csv',metrics);write_csv(out/'raw_extrema.csv',extrema)
    summary=dict(trial=trial,intervals=metrics,max_abs_empirical_wheel_speed_mps=float(np.max(np.abs(wheels))),max_estimated_centripetal_g=float(np.max(.04*(wheels/.30)**2/9.80665)),peak_empirical_acc_norm_g={s:float(acc[:,i].max()) for i,s in enumerate(('L','R','C'))},
        max_abs_accel_raw=int(csv[['ax_raw','ay_raw','az_raw']].abs().to_numpy().max()),max_abs_gyro_raw=int(csv[['gx_raw','gy_raw','gz_raw']].abs().to_numpy().max()),
        sync=json.loads((source/'cache'/(trial+'.json')).read_text())['synchronization'],test_evaluated=False,units='Acceleration norm normalized with frozen training gravity counts; wheel speed from frozen empirical wheel gyro calibration. No verified factory conversion.',provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),csvpath,source/'cache'/(trial+'.npz'),ROOT/'outputs_all_trajectories_v10/trajectories'/(trial+'.npz')]})
    save_json(out/'summary.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
