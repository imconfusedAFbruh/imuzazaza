"""Versioned metric extension. Historical evaluators and scores stay unchanged."""
import numpy as np
from scipy import signal
import pipeline as p
from research_metrics_v59 import trajectory_metrics
from route_metrics_audit_v36 import pieces, length

MIN_PATH_M=1.


def agreement(pred,ref,prefix):
    good=np.isfinite(pred)&np.isfinite(ref); pred,ref=pred[good],ref[good]
    out={prefix+'_samples':len(ref)}
    keys=('RMSE','Bias','LoA_low','LoA_high','R2','Pearson')
    if len(ref)<2:
        return dict(out,**{prefix+'_'+k:None for k in keys},**{prefix+'_missing_reason':'insufficient paired samples'})
    error=pred-ref; bias=float(error.mean()); sd=float(error.std(ddof=1)); variance=float(np.sum((ref-ref.mean())**2))
    out.update({prefix+'_RMSE':float(np.sqrt(np.mean(error**2))),prefix+'_Bias':bias,prefix+'_LoA_low':bias-1.96*sd,prefix+'_LoA_high':bias+1.96*sd,
        prefix+'_R2':float(1-np.sum(error**2)/variance) if variance>1e-12 else None,
        prefix+'_Pearson':float(np.corrcoef(pred,ref)[0,1]) if pred.std()>1e-12 and ref.std()>1e-12 else None,
        prefix+'_missing_reason':'R2/Pearson undefined for constant signals' if variance<=1e-12 or pred.std()<=1e-12 else ''})
    return out


def derivatives(t,xy,h,valid):
    v=np.full_like(xy,np.nan); omega=np.full(len(t),np.nan); mask=np.zeros(len(t),bool)
    hz=1/np.median(np.diff(t)); cutoff=min(6.,.4*hz); sos=signal.butter(2,cutoff,fs=hz,output='sos')
    edge=max(2,int(.15*hz))
    for a,b in p.runs(valid & np.isfinite(h)):
        if b-a<max(20,int(.4*hz)):continue
        # Differentiate first so filtering preserves constant velocity exactly.
        v[a:b]=signal.sosfiltfilt(sos,np.gradient(xy[a:b],t[a:b],axis=0),axis=0)
        omega[a:b]=signal.sosfiltfilt(sos,np.gradient(np.unwrap(h[a:b]),t[a:b]))
        mask[a+edge:b-edge]=True
    return v,omega,mask,cutoff


def arc_rmse(ref,pred):
    numerator=0.; count=0
    for a,b in zip(ref,pred):
        n=max(2,int(np.ceil(max(length(a),length(b))/.01))+1)
        def sample(x):
            s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(x,axis=0),axis=1))]
            if s[-1]<=1e-12:return np.repeat(x[:1],n,axis=0)
            keep=np.r_[True,np.diff(s)>1e-12]; q=np.linspace(0,s[-1],n)
            return np.c_[np.interp(q,s[keep],x[keep,0]),np.interp(q,s[keep],x[keep,1])]
        numerator+=np.sum((sample(a)-sample(b))**2); count+=n
    return float(np.sqrt(numerator/count))


def metrics(d,xy,h,motion=None):
    t,gt=d['t'],d['gt_xy']; valid=d['gt_valid']&np.isfinite(gt).all(1)&np.isfinite(xy).all(1)
    if not valid.any():raise ValueError('No matched position samples')
    error=xy[valid]-gt[valid]; magnitude=np.linalg.norm(error,axis=1)
    heading_valid=valid&np.isfinite(h)&np.isfinite(d['gt_heading'])
    out=dict(ATE_RMSE_m=float(np.sqrt(np.mean(magnitude**2))),ATE_RMSE_mm=float(1000*np.sqrt(np.mean(magnitude**2))),
        Position_MAE_mm=float(1000*magnitude.mean()),RMSE_X_mm=float(1000*np.sqrt(np.mean(error[:,0]**2))),
        RMSE_Y_mm=float(1000*np.sqrt(np.mean(error[:,1]**2))),Position_P95_mm=float(1000*np.percentile(magnitude,95)),
        Valid_Frame_Count=int(valid.sum()),C3D_Coverage_pct=float(100*d['gt_valid'].mean()),Scored_Coverage_pct=float(100*valid.mean()),
        Valid_Supported_Run_Count=len(p.runs(valid)))
    assert abs(out['ATE_RMSE_mm']**2-out['RMSE_X_mm']**2-out['RMSE_Y_mm']**2)<1e-5
    theta=d['gt_heading'][heading_valid]; e=xy[heading_valid]-gt[heading_valid]
    longitudinal=e[:,0]*np.cos(theta)+e[:,1]*np.sin(theta); lateral=-e[:,0]*np.sin(theta)+e[:,1]*np.cos(theta)
    out.update(agreement(longitudinal*1000,np.zeros(len(longitudinal)),'Longitudinal_Position_mm'))
    out.update(agreement(lateral*1000,np.zeros(len(lateral)),'Lateral_Position_mm'))
    diff=np.angle(np.exp(1j*(h[heading_valid]-theta)))
    out['Yaw_RMSE_deg']=float(np.rad2deg(np.sqrt(np.mean(diff**2)))) if len(diff) else None
    out['Yaw_Frame_Count']=int(heading_valid.sum())
    last=np.flatnonzero(valid)[-1]; endpoint=float(np.linalg.norm(xy[last]-gt[last])*1000)
    genuine=bool(d.get('recording_endpoint_included',False) and valid[-1])
    out.update(Endpoint_Supported=genuine,Endpoint_Error_mm=endpoint if genuine else None,
        Last_Supported_Endpoint_Error_mm=endpoint,Endpoint_Missing_Reason='' if genuine else 'genuine acquisition endpoint outside crop or unsupported',
        Last_Supported_Time_s=float(t[last]))
    ref,pred=pieces(gt,valid),pieces(xy,valid); path=sum(map(length,ref))
    eligible=path>=MIN_PATH_M
    out.update(Reference_Supported_Path_m=path,Path_Length_Error_mm=1000*abs(sum(map(length,pred))-path),
        Endpoint_Drift_pct=100*(endpoint/1000)/path if genuine and eligible else None,
        Last_Supported_Normalized_Endpoint_pct=100*(endpoint/1000)/path if eligible else None,
        Drift_Missing_Reason='' if genuine and eligible else ('supported path below1m' if not eligible else 'genuine endpoint unavailable'),
        Drift_Denominator_Has_Gaps=len(ref)>1)
    spatial=dict(d,gt_valid=valid,gt_heading=np.zeros(len(t)))
    routes=trajectory_metrics(spatial,xy,np.zeros(len(t)))
    out.update(Route_RMSE_mm=1000*routes['route_rmse_m'],Route_P95_mm=1000*routes['route_p95_m'],
        Sampled_Hausdorff_mm=1000*routes['sampled_hausdorff_m'],Maximum_Run_Frechet_mm=1000*routes['supported_run_frechet_max_m'],
        Within_Run_Arc_Length_RMSE_mm=1000*arc_rmse(ref,pred))
    stride=max(1,round(1/np.median(np.diff(t)))); bad=np.r_[0,np.cumsum(~valid)]
    for duration in (1,5,10):
        errs=[]; possible=0
        for i in range(0,len(t),stride):
            j=int(np.searchsorted(t,t[i]+duration-1e-9))
            if j>=len(t):continue
            possible+=1
            if bad[j+1]!=bad[i] or not heading_valid[i]:continue
            delta=(xy[j]-xy[i])-(gt[j]-gt[i]); angle=d['gt_heading'][i]
            local=np.array([[np.cos(angle),np.sin(angle)],[-np.sin(angle),np.cos(angle)]])@delta
            errs.append(np.linalg.norm(local))
        out[f'RTE_{duration}s_mm']=float(1000*np.sqrt(np.mean(np.square(errs)))) if errs else None
        out[f'RTE_{duration}s_Windows']=len(errs); out[f'RTE_{duration}s_Coverage_pct']=100*len(errs)/possible if possible else None
        out[f'RTE_{duration}s_Missing_Reason']='' if errs else 'no contiguous eligible windows'
    velocity,omega,dm,cutoff=derivatives(t,gt,d['gt_heading'],d['gt_valid']&np.isfinite(gt).all(1))
    dm &= valid
    out.update(Reference_Derivative_Filter=f'native time gradient then offline Butterworth order2 cutoff{cutoff:g}Hz;0.15s run-edge exclusion; new diagnostic differs from legacy filter-then-gradient',Reference_Velocity_Frames=int(dm.sum()))
    if motion is None:
        speed=np.full(len(t),np.nan); yaw=np.full(len(t),np.nan)
    else:
        speed=np.linalg.norm(motion[:,:2],axis=1); yaw=np.rad2deg(motion[:,2])
    out.update(agreement(speed[dm],np.linalg.norm(velocity[dm],axis=1),'Speed_mps'))
    out.update(agreement(yaw[dm],np.rad2deg(omega[dm]),'Body_Yaw_Rate_degps'))
    out['Speed_RMSE_mps']=out['Speed_mps_RMSE'];out['Angular_Velocity_RMSE_degps']=out['Body_Yaw_Rate_degps_RMSE']
    out['Failure_Flags']=';'.join(flag for flag,condition in [('partial_endpoint',not genuine),('fragmented_reference',len(ref)>1),('missing_motion',motion is None)] if condition)
    return out


def balanced(rows,key):
    people=sorted({r['participant_id'] for r in rows}); values=[]
    for person in people:
        available=[r[key] for r in rows if r['participant_id']==person and isinstance(r.get(key),(float,int)) and not isinstance(r[key],bool)]
        if available:values.append(float(np.mean(available)))
    return float(np.mean(values)) if values else None


def self_check():
    t=np.arange(0,12.01,.01); xy=np.c_[t,np.zeros(len(t))]; h=np.zeros(len(t)); m=np.c_[np.ones(len(t)),np.zeros((len(t),2))]
    d=dict(t=t,gt_xy=xy,gt_heading=h,gt_valid=np.ones(len(t),bool),recording_endpoint_included=True)
    z=metrics(d,xy,h,m); assert z['ATE_RMSE_mm']==0 and z['RTE_5s_mm']==0 and z['Yaw_RMSE_deg']==0
    assert z['Speed_RMSE_mps']<1e-8 and z['Angular_Velocity_RMSE_degps']==0
    z=metrics(d,xy+[.003,.004],h,m); assert abs(z['ATE_RMSE_mm']-5)<1e-9 and abs(z['Endpoint_Error_mm']-5)<1e-9 and z['RTE_5s_mm']<1e-9
    assert abs(z['Position_MAE_mm']-5)<1e-9
    assert abs(z['RMSE_X_mm']-3)<1e-9 and abs(z['RMSE_Y_mm']-4)<1e-9
    z=metrics(d,2*xy,h,2*m); assert abs(z['ATE_RMSE_mm']-1000*np.sqrt(np.mean(t*t)))<1e-8 and abs(z['RTE_1s_mm']-1000)<1e-8
    z=metrics(dict(d,gt_heading=h+np.deg2rad(179)),xy,h+np.deg2rad(-179),m); assert abs(z['Yaw_RMSE_deg']-2)<1e-10
    mask=np.ones(len(t),bool); mask[200]=False;mask[-1]=False
    z=metrics(dict(d,gt_valid=mask),xy,h,m);assert z['RTE_5s_Windows']<metrics(d,xy,h,m)['RTE_5s_Windows'] and z['Endpoint_Error_mm'] is None
    z=metrics(dict(d,recording_endpoint_included=False),xy,h,m);assert z['Endpoint_Error_mm'] is None and z['Last_Supported_Endpoint_Error_mm']==0
    broken=np.ones(len(t),bool);broken[::100]=False
    z=metrics(dict(d,gt_valid=broken),xy,h,m);assert z['RTE_1s_mm'] is None and z['RTE_1s_Windows']==0
    v,w,vm,_=derivatives(t,xy,.2*t,broken);assert not vm[~broken].any() and np.max(np.abs(w[vm]-.2))<1e-8
    z=metrics(dict(d,gt_xy=xy*0),xy*0,h,m*0);assert z['Endpoint_Drift_pct'] is None
    rows=[dict(participant_id='A',score=1.)]*100+[dict(participant_id='B',score=9.)]; assert balanced(rows,'score')==5 and np.mean([r['score'] for r in rows])!=5
    z=agreement(2*t,t,'x');assert abs(z['x_Pearson']-1)<1e-12 and z['x_R2']<0
    z=agreement(t+2,t,'x');assert abs(z['x_Bias']-2)<1e-12 and abs(z['x_LoA_low']-2)<1e-12
    print('Metric contract synthetic checks passed')


if __name__=='__main__':self_check()
