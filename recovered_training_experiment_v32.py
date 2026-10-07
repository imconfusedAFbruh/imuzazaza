"""Controlled v21 correction refits using stored processed TRAIN reference.

Frozen split, clocks, initialization, base model, geometry and validation masks.
No test signals. This refits the interval correction, not the inherited base.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time
from pathlib import Path
import numpy as np
import ezc3d
import torch
from scipy import signal
from pipeline import ROOT,digest,save_json,write_csv,masked_interp,runs,metrics,summarize
from nonlinear_endpoint_experiment_v21 import load_train,bounds,adapted,nonlinear_features,FOLD
from motion_endpoint_experiment_v16 import normal_system,fit,score
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix,correction
from trajectory_calibration_v10 import integrate

OUT=ROOT/'outputs_recovered_training_v32'
MODES=['stored_endpoints','stored_endpoints_and_rates']

def restored(row,d,cfg):
    path=ROOT/row['c3d'];meta=json.loads((ROOT/'outputs_observed_reference_v7/cache'/(row['id']+'.json')).read_text())
    if digest(path)!=meta['signature']['c3d_sha256']:raise RuntimeError('Changed source C3D')
    c=ezc3d.c3d(str(path));p=c['parameters']['POINT'];names=[s.strip() for s in p['LABELS']['value']];ids=[names.index(k) for k in ['L_FAL','R_FAL']]
    scale={'mm':.001,'cm':.01,'m':1}[p['UNITS']['value'][0].strip().lower()]
    xyz=c['data']['points'][:3,ids,:].transpose(2,1,0)*scale;res=c['data']['meta_points']['residuals'][0,ids,:].T
    available=(res>=0).all(1)&np.isfinite(xyz).all((1,2))&(np.linalg.norm(xyz,axis=2)>1e-8).all(1)
    observed=available&(res>0).all(1);masks=c['data']['meta_points'].get('camera_masks')
    if masks is not None:
        support=np.asarray(masks)[:,ids,:].any(0).T
        if support.any():observed&=support.all(1)
    sep=np.linalg.norm(xyz[:,0]-xyz[:,1],axis=1);policy=cfg['reference_geometry']['setups'][row['setup']];allowed=np.zeros(len(xyz),bool)
    for band in policy['bands']:allowed|=(sep>=band['lower_m'])&(sep<=band['upper_m'])
    valid=available&allowed&(np.abs(sep-np.median(sep[observed]))<=policy['rigidity_tolerance_m'])
    hz=float(c['header']['points']['frame_rate']);t=np.arange(len(xyz))/hz;query=d['ref_t'];xy=xyz[:,:,:2].mean(1);lat=xyz[:,0,:2]-xyz[:,1,:2]
    heading=np.arctan2(-lat[:,0],lat[:,1]);psi=heading.copy();v=np.full(len(t),np.nan);w=v.copy();deriv=np.zeros(len(t),bool)
    sos=signal.butter(2,min(cfg['derivative_hz'],.4*hz),fs=hz,output='sos')
    for a,b in runs(valid):
        psi[a:b]=np.unwrap(heading[a:b])
        if b-a<max(20,int(.4*hz)):continue
        smooth=signal.sosfiltfilt(sos,xy[a:b],axis=0);ph=signal.sosfiltfilt(sos,psi[a:b]);vel=np.gradient(smooth,1/hz,axis=0)
        v[a:b]=vel[:,0]*np.cos(ph)+vel[:,1]*np.sin(ph);w[a:b]=np.gradient(ph,1/hz);edge=max(2,int(.15*hz));deriv[a+edge:b-edge]=True
    gx,mx=masked_interp(query,t,xy[:,0],valid);gy,my=masked_interp(query,t,xy[:,1],valid);h,mh=masked_interp(query,t,psi,valid)
    vv,mv=masked_interp(query,t,v,deriv);ww,mw=masked_interp(query,t,w,deriv)
    mask=mx&my&mh&d['imu_valid'];label=mv&mw&mask
    # Retain exact previously observed positions/heading and rate labels.
    old=d['gt_valid'];h+=np.round((d['gt_heading'][0]-h[0])/(2*np.pi))*2*np.pi
    gx[old]=d['gt_xy'][old,0];gy[old]=d['gt_xy'][old,1];h[old]=d['gt_heading'][old];mask|=old
    oldlabel=d['label_valid'];vv[oldlabel]=d['gt_v'][oldlabel];ww[oldlabel]=d['gt_yaw'][oldlabel];label|=oldlabel
    audit=dict(id=row['id'],partition=row['partition'],participant=row['participant'],condition=row['condition'],native_frames=len(t),native_stored_frames=int(available.sum()),native_observed_frames=int(observed.sum()),native_processed_frames=int((available&~observed).sum()),native_unavailable_frames=int((~available).sum()),old_endpoint_frames=int(old.sum()),restored_endpoint_frames=int(mask.sum()),added_endpoint_frames=int((mask&~old).sum()),old_rate_frames=int(oldlabel.sum()),added_rate_frames=int((label&~oldlabel).sum()))
    return dict(d,gt_xy=np.c_[gx,gy],gt_heading=h,gt_valid=mask,gt_v=vv,gt_yaw=ww,label_valid=label),audit

def entry_mode(e,mode):
    d=e['restored'];rates=mode=='stored_endpoints_and_rates'
    return dict(e,data=d,target=np.c_[d['gt_v'],d['gt_yaw']]-e['motion'][:,[0,2]] if rates else e['target'],label=(d['label_valid']&d['imu_valid']&np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])) if rates else e['label'])

def main():
    start=time.perf_counter();torch.set_num_threads(4)
    if OUT.exists():raise RuntimeError('Preserve previous run')
    OUT.mkdir();(OUT/'training_reference').mkdir();(OUT/'trajectories').mkdir()
    source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];oldmodel=json.loads((ROOT/'outputs_nonlinear_endpoint_v21/model.json').read_text());candidate={k:oldmodel['candidate'][k] for k in ['basis','alpha','endpoint_weight','gain']}
    save_json(OUT/'protocol.json',dict(modes=MODES,parameters=candidate,training_trials=473,validation_trials=71,fold=sorted(FOLD),selection='Conditional training fold: lowest observed-frame equal-participant RMSE subject to <=5% worst-participant regression relative to v21. Frozen original remains eligible.',validation_score='Unchanged v7 observed frames and initial pose',base_model_refitted=False,calibration_refitted=False,normalization='Correction refitted on training only',stored_coordinates='Weak processed supervision; no new gap interpolation',test_accessed=False))
    train=load_train(ROOT/'outputs_motion_endpoint_v16');audits=[]
    for i,e in enumerate(train):
        if e['row']['partition']!='train':raise RuntimeError('Training leakage')
        e['restored'],a=restored(e['row'],e['data'],cfg);audits.append(a)
        d=e['restored'];np.savez_compressed(OUT/'training_reference'/(e['row']['id']+'.npz'),gt_xy=d['gt_xy'],gt_heading=d['gt_heading'],gt_valid=d['gt_valid'],gt_v=d['gt_v'],gt_yaw=d['gt_yaw'],label_valid=d['label_valid'],original_observed_valid=e['data']['gt_valid'],original_label_valid=e['data']['label_valid'])
        if (i+1)%50==0:print('Restored training',i+1,flush=True)
    write_csv(OUT/'training_recovery_audit.csv',audits)
    inner=[e for e in train if e['row']['participant'] in FOLD];fitting=[e for e in train if e['row']['participant'] not in FOLD]
    # Same inherited base: this is conditional correction selection, not nested evaluation.
    innerclips=bounds(fitting);original_fit=fit(normal_system(adapted(fitting,candidate['basis'],innerclips)),candidate['alpha'],candidate['endpoint_weight'])
    (innerbase,people,_),_=score(adapted(inner,candidate['basis'],innerclips),original_fit,candidate,cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in people}
    selection=[dict(mode='original_v21',score=innerbase['equal_participant_mean_position_rmse_m'],worst_person_ratio=1.)]
    models={}
    for mode in MODES:
        es=[entry_mode(e,mode) for e in fitting];clips=bounds(es);fits=fit(normal_system(adapted(es,candidate['basis'],clips)),candidate['alpha'],candidate['endpoint_weight'])
        (summary,people,_),_=score(adapted(inner,candidate['basis'],clips),fits,candidate,cfg)
        result=dict(mode=mode,score=summary['equal_participant_mean_position_rmse_m'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/basepeople[p['participant']] for p in people));selection.append(result);print('Conditional training fold',result,flush=True)
        es=[entry_mode(e,mode) for e in train];clips=bounds(es);fits=fit(normal_system(adapted(es,candidate['basis'],clips)),candidate['alpha'],candidate['endpoint_weight'])
        model=dict(candidate=candidate,fits=fits,feature_clip=clips,training_ids=[e['row']['id'] for e in train],mode=mode);models[mode]=model;save_json(OUT/(mode+'_model.json'),model)
    selected=min([q for q in selection if q['worst_person_ratio']<=1.05],key=lambda q:q['score'])
    save_json(OUT/'selection.json',dict(selected=selected,candidates=selection,caveat='Inherited calibration/base saw inner participants. Conditional correction selection only; reused validation exploratory.'))
    trainpeople={e['row']['participant'] for e in train};del train,inner,fitting,es
    manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());states={q['id']:q for q in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};ridge=load_observed_ridge();records={k:[] for k in ['original_v21',*MODES]}
    validation_audits=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        if row['participant'] in trainpeople:raise RuntimeError('Participant leakage')
        full,a=restored(row,d,cfg);validation_audits.append(a)
        sensor={k:d[k] for k in ('setup','t','raw','imu_valid')};motion=ridge(sensor);x=feature_matrix(sensor,motion,cal[row['setup']],states[row['id']],'gravity_rotation');e=dict(row=row,data=d,motion=motion,linear=x,nonlinear=nonlinear_features(x),setup=row['setup'])
        arrays=dict(time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],stored_reference_xy_m=full['gt_xy'],stored_reference_valid=full['gt_valid'],stored_processed_valid=full['gt_valid']&~d['gt_valid'],imu_valid=d['imu_valid'])
        for name,model in [('original_v21',oldmodel),*models.items()]:
            ee=adapted([e],candidate['basis'],model['feature_clip'])[0];m=correction(dict(ee,x={'gravity_rotation':ee['x']}),model['fits'],dict(candidate,mode='gravity_rotation'));xy,h=integrate(d,m)
            record=dict(id=row['id'],participant=row['participant'],condition=row['condition'],**metrics(d,xy,h,cfg));records[name].append(record);arrays[name+'_xy_m']=xy;arrays[name+'_heading_rad']=h;arrays[name+'_motion']=m
        np.savez_compressed(OUT/'trajectories'/(row['id']+'.npz'),**arrays)
    write_csv(OUT/'validation_display_audit.csv',validation_audits);summary={}
    for name,rows in records.items():
        summary[name],people,conditions=summarize(rows)
        for suffix,values in [('trials',rows),('participants',people),('maneuvers',conditions)]:write_csv(OUT/(name+'_'+suffix+'.csv'),values)
    expected=json.loads((ROOT/'outputs_trajectory_best_v21/summary.json').read_text())['models']['Nonlinear interval correction v21']['equal_participant_mean_position_rmse_m']
    if abs(summary['original_v21']['equal_participant_mean_position_rmse_m']-expected)>1e-8:raise RuntimeError('Original validation reproduction failed')
    save_json(OUT/'run.json',dict(summary=summary,selected=selected,training_trials=473,earlier_training_trials=sum(a['id'][:10] not in ('2026-09-24','2026-09-25') for a in audits),target_training_trials=sum(a['id'][:10] in ('2026-09-24','2026-09-25') for a in audits),validation_trials=71,validation_participants=4,added_training_endpoint_frames=sum(a['added_endpoint_frames'] for a in audits),added_training_rate_frames=sum(a['added_rate_frames'] for a in audits),base_model_refitted=False,test_accessed=False,runtime_seconds=time.perf_counter()-start,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'outputs_nonlinear_endpoint_v21/model.json',ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/split.json']}))
    save_json(OUT/'artifact_manifest.json',dict(sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
