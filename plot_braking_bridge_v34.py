"""Visual diagnostics for the rejected short braking bridge."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import ROOT, digest, save_json, runs

out=ROOT/'outputs_braking_bridge_v34'
run=json.loads((out/'run.json').read_text())
selection=json.loads((out/'selection.json').read_text())
blends=[q['blend'] for q in selection['candidates']]
train=[q['score']*1000 for q in selection['candidates']]
validation=[run['summary']['bridge_'+str(b).replace('.','p')]['equal_participant_mean_position_rmse_m']*1000 for b in blends]
det=pd.read_csv(out/'validation_detection.csv')
acc=pd.read_csv(out/'validation_acceleration_diagnostics.csv')
fig,axes=plt.subplots(2,3,figsize=(15.5,10.1))
fig.suptitle('Short braking bridge rejected: wheel/body disagreement also fires in ordinary motion',fontsize=15)
ax=axes[0,0]
ax.plot(blends,train,'o-',label='Conditional training fold',color='#225ea8')
ax.plot(blends,validation,'o-',label='Observed validation',color='#d95f0e')
ax.set_xlabel('Bridge blend');ax.set_ylabel('Trajectory RMSE (mm)');ax.set_title('Zero bridge is selected on training')
ax.legend(fontsize=9);ax.grid(alpha=.2)
count=det.groupby('condition').events.sum()
axes[0,1].bar(count.index,count.values,color='#225ea8');axes[0,1].set_title('597 candidate events across71 validation cases')
axes[0,1].set_ylabel('Detected bridge events');axes[0,1].grid(axis='y',alpha=.2)
ar=acc.groupby('condition').acceleration_rmse_mps2.mean()
axes[0,2].bar(ar.index,ar.values,color='#d95f0e');axes[0,2].set_title('Center acceleration remains least reliable on ST')
axes[0,2].set_ylabel('Mean trial acceleration RMSE (m/s²)');axes[0,2].grid(axis='y',alpha=.2)
examples=['2026-09-25__PS__PS_Trial2_No.18','2026-09-25__PS__PS_Trial2_No.14','2026-09-25__ST__ST_Trial1_No.14']
trials={b:pd.read_csv(out/('bridge_'+str(b).replace('.','p')+'_trials.csv')).set_index('id') for b in (0.,.25)}
for ax,rid in zip(axes[1],examples):
    with np.load(out/'trajectories'/(rid+'.npz'),allow_pickle=False) as z:
        t=z['time_s']-z['time_s'][0]
        old=np.linalg.norm(z['bridge_0p0_xy_m']-z['reference_xy_m'],axis=1)*1000
        new=np.linalg.norm(z['bridge_0p25_xy_m']-z['reference_xy_m'],axis=1)*1000
        old[~z['reference_valid']]=np.nan;new[~z['reference_valid']]=np.nan
        ax.plot(t,old,color='#9aa8b5',linestyle='--',linewidth=1.5,label='Originalv21')
        ax.plot(t,new,color='#d95f0e',linewidth=1.5,label='Bridge blend0.25')
        for a,b in runs(z['bridge_active']):
            ax.axvspan(t[a],t[b-1],color='#225ea8',alpha=.10)
    rmse0=trials[0.].loc[rid,'position_rmse_m']*1000;rmse1=trials[.25].loc[rid,'position_rmse_m']*1000
    short=rid.split('__')[-1].replace('_',' / ')
    ax.set_title(f'{short}\nObserved RMSE{rmse0:.1f}→{rmse1:.1f}mm',fontsize=11)
    ax.set_xlabel('Time from beginning (s)');ax.set_ylabel('Observed-frame position error (mm)');ax.grid(alpha=.2)
axes[1,0].legend(fontsize=8,loc='best')
fig.text(.5,.012,'Yaw/lateral unchanged. V21 correction refitted inside training fold; inherited base/calibration conditional limitation remains. Test untouched.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.04,1,.96))
(out/'figures').mkdir(exist_ok=True)
fig.savefig(out/'figures/braking_bridge_diagnostics.png',dpi=150)
plt.close(fig)
save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}))
print(out/'figures/braking_bridge_diagnostics.png')
