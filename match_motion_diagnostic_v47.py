from pathlib import Path
import csv,json
import numpy as np
root=Path.cwd();source=root/'outputs_dynamic_blend_v34';out=root/'outputs_match_motion_v47';out.mkdir(exist_ok=False)
rows=[];thresholds=[10,20,50,100,200]
for row in csv.DictReader((source/'selected_blend_trials.csv').open()):
    with np.load(source/'trajectories'/(row['id']+'.npz')) as z:
        ref=z['reference_xy_m'];pred=z['selected_blend_xy_m'];t=z['time_s'];heading=z['reference_heading_rad'];valid=z['reference_valid']&np.isfinite(ref).all(1)&np.isfinite(pred).all(1)
        dt=np.diff(t);edges=valid[:-1]&valid[1:]&(dt>0)
        speed=np.full(len(t),np.nan);yaw=np.full(len(t),np.nan)
        speed[1:]=np.where(edges,np.linalg.norm(np.diff(ref,axis=0),axis=1)/dt,np.nan)
        yaw[1:]=np.where(edges,np.abs(np.arctan2(np.sin(np.diff(heading)),np.cos(np.diff(heading))))/dt,np.nan)
        error=np.linalg.norm(pred-ref,axis=1);supported=valid&np.isfinite(speed)&np.isfinite(yaw)
        for name,mask in [('all_observed',valid),('translating',supported&(speed>.05)),('near_quiet',supported&(speed<=.05)&(yaw<=.15)),('pivot_low_translation',supported&(speed<=.05)&(yaw>.15)),('after_first_second',valid&((t-t[0])>1))]:
            if not mask.any():continue
            r=dict(id=row['id'],participant=row['participant'],condition=row['condition'],stratum=name,frames=int(mask.sum()),fraction_of_observed=float(mask.sum()/valid.sum()),rmse_mm=float(np.sqrt(np.mean(error[mask]**2))*1000))
            for mm in thresholds:r[f'within_{mm}mm_pct']=float(100*np.mean(error[mask]<=mm/1000))
            rows.append(r)
fields=['fraction_of_observed','rmse_mm']+[f'within_{mm}mm_pct' for mm in thresholds];summary=[]
for group in sorted({r['stratum'] for r in rows}):
    subset=[r for r in rows if r['stratum']==group];people=sorted({r['participant'] for r in subset});s=dict(stratum=group,trials=len(subset),participants=len(people))
    for f in fields:s[f]=float(np.mean([np.mean([r[f] for r in subset if r['participant']==p]) for p in people]))
    summary.append(s)
with (out/'trials.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
result=dict(summary=summary,interpretation='Diagnostic reference-motion strata, not a classifier or model update. Near-quiet can include optical noise; simple adjacent observed derivative; no bridging gaps.',thresholds=dict(speed_m_s=.05,yaw_rad_s=.15),aggregation='Equal trials within participant then equal participants for each available stratum',test_accessed=False)
(out/'run.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
