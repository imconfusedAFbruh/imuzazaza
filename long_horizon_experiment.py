"""Matched short-loss versus multi-horizon observed endpoint loss, three seeds.

Inner neural fold selection is conditional on a fixed pretrained TCN/calibration.
Final validation is scored only after all epochs/gains are selected and refitted.
"""
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset,DataLoader,WeightedRandomSampler
from pipeline import ROOT,digest,save_json,write_csv,velocities,metrics,summarize
from learning import load_predictor,training_group
from planar_experiment import verify_parent,lateral_labels,planar_features
from planar_neural_experiment import PlanarResNet,predict_windows,planar_loss
from observed_training_experiment import observed_rows

INNER=('No.3','No.8','No.15','No.20')
SEEDS=(42,43,44)
HORIZONS=(100,300,500,1000)
N=1025


def normalize(entries):
    sx=[];sy=[];sg=[]
    for e in entries:
        m=e['valid'];x=e['x'][m][::10];y=e['target'][m][::10]
        if len(x):sx.append(x);sy.append(y);sg.extend([e['group']]*len(x))
    x=np.concatenate(sx);y=np.concatenate(sy);counts=Counter(sg)
    w=np.array([1/counts[g] for g in sg]);mean=np.average(x,axis=0,weights=w)
    std=np.maximum(np.sqrt(np.average((x-mean)**2,axis=0,weights=w)),1e-5)
    ym=np.average(y,axis=0,weights=w)
    scale=np.maximum(np.sqrt(np.average((y-ym)**2,axis=0,weights=w)),.01)
    cap=np.maximum(np.quantile(np.abs(y),.995,axis=0),.03)
    return dict(mean=mean.astype(np.float32).tolist(),std=std.astype(np.float32).tolist(),
      target_scale=scale.astype(np.float32).tolist(),residual_cap=cap.astype(np.float32).tolist(),
      training_ids=[e['row']['id'] for e in entries],groups=dict(counts),source='New parameters training-only; equal participant/date group weighting')


class EndpointWindows(Dataset):
    """Five exact 512 contexts emit 1025 stitched outputs, matching full inference."""
    def __init__(self,entries,norm):
        self.entries=entries;self.index=[];self.groups=[];self.arrays=[]
        mean,std,scale=[np.array(norm[k],np.float32) for k in ('mean','std','target_scale')]
        for i,e in enumerate(entries):
            d=e['data'];x=(e['x']-mean)/std;y=np.nan_to_num(e['target'])/scale
            self.arrays.append((np.pad(x,((128,1536),(0,0))),np.pad(y,((128,1536),(0,0))),np.pad(e['valid'],(128,1536))))
            for start in range(0,len(x),1024):
                if not d['imu_valid'][start:start+N].all() or not e['valid'][start:start+N].any():continue
                if not d['imu_valid'][max(0,start-128):min(len(x),start+1408)].all():continue
                if not d['gt_valid'][start]:continue
                if not any(start+h<len(x) and d['gt_valid'][start+h] for h in HORIZONS):continue
                self.index.append((i,start));self.groups.append(e['group'])
        if not self.index:raise RuntimeError('No observed-endpoint windows')

    def __len__(self):return len(self.index)

    def __getitem__(self,index):
        i,start=self.index[index];e=self.entries[i];d=e['data'];px,py,pm=self.arrays[i]
        xx=np.stack([px[start+k:start+k+512].T for k in range(0,N,256)])
        yy=np.stack([py[start+k:start+k+512].T for k in range(0,N,256)])
        masks=np.stack([pm[start+k:start+k+512] for k in range(0,N,256)])
        active=np.array([start+k<len(d['t']) for k in range(0,N,256)],bool)
        h=d['gt_heading'][start];c,s=np.cos(h),np.sin(h);targets=[];valid=[]
        for horizon in HORIZONS:
            end=start+horizon
            if end>=len(d['t']):targets.append([0.,0.,0.]);valid.append(False);continue
            delta=d['gt_xy'][end]-d['gt_xy'][start]
            angle=d['gt_heading'][end]-h
            targets.append([c*delta[0]+s*delta[1],-s*delta[0]+c*delta[1],np.arctan2(np.sin(angle),np.cos(angle))])
            valid.append(bool(d['gt_valid'][end] and np.isfinite(targets[-1]).all()))
        motion=e['tcn'][start:start+N]
        base=np.c_[motion[:,0],np.zeros(len(motion)),motion[:,1]]
        base=np.pad(base,((0,N-len(base)),(0,0)))
        return (xx.astype(np.float32),yy.astype(np.float32),masks,base.astype(np.float32),
          np.nan_to_num(np.array(targets,np.float32)),np.array(valid,bool),active)


def stitched_endpoint_loss(predictions,base,targets,valid,scale,cap):
    b=base.shape[0]
    pred=predictions.reshape(b,5,3,512)[:,:,:,128:384]
    correction=pred.permute(0,2,1,3).reshape(b,3,1280)[:,:,:N]*scale
    correction=torch.maximum(torch.minimum(correction,cap),-cap)
    motion=base.transpose(1,2)+correction
    middle=(motion[:,:,:-1]+motion[:,:,1:])/2
    angle=F.pad(torch.cumsum(middle[:,2]*.01,dim=1),(1,0))
    midangle=(angle[:,:-1]+angle[:,1:])/2
    delta=torch.stack([middle[:,0]*torch.cos(midangle)-middle[:,1]*torch.sin(midangle),
       middle[:,0]*torch.sin(midangle)+middle[:,1]*torch.cos(midangle)],dim=1)*.01
    position=F.pad(torch.cumsum(delta,dim=2),(1,0))
    indices=torch.tensor(HORIZONS,device=motion.device)
    endpoint=position[:,:,indices].transpose(1,2)
    heading=angle[:,indices]
    # Fixed scales and weights declared before results. Endpoint location does
    # not use intermediate optical poses; optical gaps may be traversed.
    posloss=F.smooth_l1_loss(endpoint[valid]/.10,targets[:,:,:2][valid]/.10)
    difference=heading-targets[:,:,2]
    angleloss=F.smooth_l1_loss(torch.sin(difference)[valid]/.05,torch.zeros_like(difference[valid]))
    angleloss+=F.smooth_l1_loss((1-torch.cos(difference))[valid]/.05,torch.zeros_like(difference[valid]))
    return .2*posloss+.1*angleloss


def integrate_fast(data,motion):
    t=data['t'];middle=(motion[:-1]+motion[1:])/2;dt=np.diff(t)
    heading=np.r_[0,np.cumsum(middle[:,2]*dt)]+data['gt_heading'][0]
    a=(heading[:-1]+heading[1:])/2
    delta=np.c_[middle[:,0]*np.cos(a)-middle[:,1]*np.sin(a),middle[:,0]*np.sin(a)+middle[:,1]*np.cos(a)]*dt[:,None]
    xy=np.vstack([np.zeros(2),np.cumsum(delta,axis=0)])+data['gt_xy'][0]
    iv=data['imu_valid'];bad=np.flatnonzero(~(iv[:-1]&iv[1:]))
    if len(bad):xy[bad[0]+1:]=np.nan;heading[bad[0]+1:]=np.nan
    return xy,heading


def predict_motion(model,e,norm,gain,device):
    mean,std,scale,cap=[np.array(norm[k],np.float32) for k in ('mean','std','target_scale','residual_cap')]
    correction=np.clip(predict_windows(model,(e['x']-mean)/std,device)*scale,-cap,cap)
    return np.c_[e['tcn'][:,0],np.zeros(len(e['tcn'])),e['tcn'][:,1]]+gain*correction


def inner_scores(model,entries,norm,device):
    motions={id(e):predict_motion(model,e,norm,1.,device) for e in entries}
    scores=[]
    for gain in (.25,.5,1.):
        people={}
        for e in entries:
            base=np.c_[e['tcn'][:,0],np.zeros(len(e['tcn'])),e['tcn'][:,1]]
            motion=base+gain*(motions[id(e)]-base)
            xy,_=integrate_fast(e['data'],motion);mask=e['data']['gt_valid']&np.isfinite(xy).all(axis=1)
            value=float(np.sqrt(np.mean(np.sum((xy[mask]-e['data']['gt_xy'][mask])**2,axis=1))))
            people.setdefault(e['row']['participant'],[]).append(value)
        scores.append(dict(gain=gain,rmse_m=float(np.mean([np.mean(v) for v in people.values()]))))
    return scores


def train(entries,norm,seed,method,epochs,device,inner=None):
    torch.manual_seed(seed);np.random.seed(seed)
    dataset=EndpointWindows(entries,norm);counts=Counter(dataset.groups)
    sampler=WeightedRandomSampler([1/counts[g] for g in dataset.groups],len(dataset),generator=torch.Generator().manual_seed(seed))
    loader=DataLoader(dataset,batch_size=16,sampler=sampler)
    model=PlanarResNet().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.001)
    mean,std,scale,cap=[torch.tensor(norm[k],device=device)[None,:,None] for k in ('mean','std','target_scale','residual_cap')]
    best=None;history=[]
    for epoch in range(1,epochs+1):
        model.train();losses=[]
        for x,y,mask,base,gt,ev,active in loader:
            x,y,mask,base,gt,ev,active=[z.to(device) for z in (x,y,mask,base,gt,ev,active)]
            b=x.shape[0];flat=x.reshape(b*5,28,512);active=active.reshape(b*5)
            indices=torch.nonzero(active,as_tuple=False).flatten()
            values=model(flat[active])
            pred=values.new_zeros((b*5,3,512)).index_copy(0,indices,values)
            physical=flat*std+mean
            base_windows=torch.stack([physical[:,26],torch.zeros_like(physical[:,26]),physical[:,27]],dim=1)
            flatmask=mask.reshape(b*5,512);validwindows=flatmask[:,128:384].any(dim=1)&active
            loss=planar_loss(pred[validwindows],y.reshape(b*5,3,512)[validwindows],base_windows[validwindows],flatmask[validwindows],scale)
            if method=='endpoint':loss+=stitched_endpoint_loss(pred,base,gt,ev,scale,cap)
            if not torch.isfinite(loss):raise RuntimeError('Non-finite training loss')
            optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step();losses.append(float(loss.detach()))
        model.eval();record=dict(epoch=epoch,loss=float(np.mean(losses)))
        if inner is not None:
            scores=inner_scores(model,inner,norm,device);choice=min(scores,key=lambda s:s['rmse_m']);record['scores']=scores
            if best is None or choice['rmse_m']<best['rmse_m']:best=dict(epoch=epoch,**choice)
        history.append(record)
        print(f'{method} seed{seed} {"inner" if inner is not None else "refit"} epoch{epoch}/{epochs} loss{record["loss"]:.4f}'+(f' inner{choice["rmse_m"]*1000:.2f}mm' if inner is not None else ''),flush=True)
    return model,best,history,len(dataset)


def final_score(entries,motions,cfg,out,label):
    rows=[]
    for e,motion in zip(entries,motions):
        xy,heading=integrate_fast(e['data'],motion)
        result=dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(e['data'],xy,heading,cfg))
        if not np.isfinite(result['position_rmse_m']):raise RuntimeError('Invalid final score')
        rows.append(result)
    summary,people,conditions=summarize(rows)
    for suffix,data in [('trials',rows),('participants',people),('maneuvers',conditions)]:write_csv(out/(label+'_'+suffix+'.csv'),data)
    return summary


def main():
    started=time.perf_counter();source=ROOT/'outputs_observed_reference_v7';parent=ROOT/'outputs_amended_v2';out=ROOT/'outputs_long_horizon_v9'
    if out.exists():raise RuntimeError('Preserve experiment')
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    provenance=verify_parent(parent);manifest=json.loads((source/'artifact_manifest.json').read_text())
    for name,sha in manifest['sha256'].items():
        if digest(source/name)!=sha:raise RuntimeError('Changed source artifact '+name)
    run=json.loads((source/'run.json').read_text());cfg=run['settings']
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed source dependency '+name)
    out.mkdir();torch.set_num_threads(4);device=torch.device('cuda')
    protocol=dict(seeds=SEEDS,epochs=12,gains=[.25,.5,1.],inner_participants=INNER,horizons_s=[1,3,5,10],
      long_core_samples=N,segment_stride=1024,window_context=512,central_outputs=256,future_imu_seconds=1.28,
      endpoint_weight_position=.2,endpoint_weight_heading=.1,position_scale_m=.10,heading_scale_rad=.05,
      selection='Each method/seed epoch+gain by conditional inner fold; all-train refit selected epoch; deployment method lowest median inner RMSE and seed median inner RMSE. Validation only final scoring. All seed motion mean ensembles predefined.',
      caveat='Inherited frozen TCN/calibration saw inner participants; only new normalization/caps/weights exclude inner fold. Not independent whole-pipeline evaluation.',
      control='Same long segments, model contexts, optimizer and seeds, short loss only. Test data forbidden.')
    protocol['boundary_and_dropout_rule']='Short recordings/output tails zero-padded with invalid rate/endpoint labels; endpoints beyond recording end excluded. Entire output-empty windows excluded from model forward/BatchNorm and scattered differentiably as zero corrections. All real samples in five512inputcontexts must have valid IMU support; boundary padding only is allowed.'
    save_json(out/'protocol.json',protocol)
    cal=json.loads((parent/'calibration.json').read_text());tcn=load_predictor(parent,'tcn32');entries=[]
    signatures=[]
    for row,data,meta in observed_rows(source,cfg,'train',manifest):
        if not np.allclose(np.diff(data['t']),.01,atol=1e-8,rtol=0):raise RuntimeError('Loss requires inherited fixed 100Hz resampled timing')
        base=velocities(data,cal[row['setup']]);motion=tcn(data,base);side,valid=lateral_labels(data)
        target=np.c_[data['gt_v']-motion[:,0],side,data['gt_yaw']-motion[:,1]];valid&=np.isfinite(target).all(axis=1)
        x=planar_features(data,base,motion,cal).astype(np.float32)
        entries.append(dict(row=row,data={k:v for k,v in data.items() if k!='raw'},x=x,tcn=motion,target=target.astype(np.float32),valid=valid,group=training_group(row)))
        signatures.append(dict(id=row['id'],partition='train',signature=meta['signature']))
    fit=[e for e in entries if e['row']['participant'] not in INNER];inner=[e for e in entries if e['row']['participant'] in INNER]
    if {e['row']['participant'] for e in inner}!=set(INNER):raise RuntimeError('Inner participants missing')
    inner_norm=normalize(fit);full_norm=normalize(entries)
    save_json(out/'inner_normalization.json',inner_norm);save_json(out/'normalization.json',full_norm)
    choices={};history={}
    for method in ('short','endpoint'):
        for seed in SEEDS:
            model,best,records,windows=train(fit,inner_norm,seed,method,12,device,inner)
            choices[f'{method}_{seed}']=dict(best,training_windows=windows);history[f'{method}_{seed}']=records
            del model;save_json(out/'inner_choices.json',choices);save_json(out/'inner_history.json',history)
    medians={m:float(np.median([choices[f'{m}_{s}']['rmse_m'] for s in SEEDS])) for m in ('short','endpoint')}
    deployment_method=min(medians,key=medians.get)
    ordered=sorted(SEEDS,key=lambda s:choices[f'{deployment_method}_{s}']['rmse_m']);deployment_seed=ordered[1]
    save_json(out/'deployment_choice.json',dict(method=deployment_method,seed=deployment_seed,median_inner_rmse_m=medians,
       selected_before_validation=True))
    refit_history={};counts={}
    for method in ('short','endpoint'):
        for seed in SEEDS:
            choice=choices[f'{method}_{seed}'];model,_,records,windows=train(entries,full_norm,seed,method,choice['epoch'],device)
            torch.save(dict(state={k:v.detach().cpu() for k,v in model.state_dict().items()},gain=choice['gain'],epoch=choice['epoch'],seed=seed,method=method),out/f'{method}_{seed}.pt')
            refit_history[f'{method}_{seed}']=records;counts[f'{method}_{seed}']=windows;del model
            save_json(out/'refit_history.json',refit_history)
    # First validation signal loading occurs only after all choices/refits freeze.
    validation=[];train_people={e['row']['participant'] for e in entries}
    for row,data,meta in observed_rows(source,cfg,'validation',manifest):
        if row['participant'] in train_people:raise RuntimeError('Participant leakage')
        base=velocities(data,cal[row['setup']]);motion=tcn(data,base)
        validation.append(dict(row=row,data={k:v for k,v in data.items() if k!='raw'},x=planar_features(data,base,motion,cal).astype(np.float32),tcn=motion))
        signatures.append(dict(id=row['id'],partition='validation',signature=meta['signature']))
    candidates={};spread={}
    for method in ('short','endpoint'):
        allmotions=[]
        for seed in SEEDS:
            state=torch.load(out/f'{method}_{seed}.pt',map_location='cpu',weights_only=True)
            model=PlanarResNet().to(device).eval();model.load_state_dict(state['state'])
            motions=[predict_motion(model,e,full_norm,state['gain'],device) for e in validation]
            label=f'{method}_{seed}';candidates[label]=final_score(validation,motions,cfg,out,label);allmotions.append(motions);del model
        ensemble=[np.mean([m[i] for m in allmotions],axis=0) for i in range(len(validation))]
        candidates[method+'_ensemble']=final_score(validation,ensemble,cfg,out,method+'_ensemble')
        values=[candidates[f'{method}_{s}']['equal_participant_mean_position_rmse_m'] for s in SEEDS]
        spread[method]=dict(median_rmse_m=float(np.median(values)),minimum_rmse_m=float(min(values)),maximum_rmse_m=float(max(values)),all_seed_rmse_m=values)
    ridge=json.loads((ROOT/'outputs_observed_ridge_v8/selection.json').read_text())
    save_json(out/'input_signatures.json',signatures)
    files=[Path(__file__),source/'artifact_manifest.json',source/'run.json',ROOT/'outputs_observed_ridge_v8/selection.json']
    files.extend(ROOT/n for n in ('pipeline.py','learning.py','planar_experiment.py','planar_neural_experiment.py','ronin_experiment.py','observed_training_experiment.py'))
    provenance.update({str(f.relative_to(ROOT)):digest(f) for f in files})
    selection=dict(candidates=candidates,spread=spread,selected=f'{deployment_method}_{deployment_seed}',selection_basis='Predeclared conditional-inner-fold median; not validation winner',
      deployment_method=deployment_method,deployment_seed=deployment_seed,inner_choices=choices,training_trials=len(entries),inner_fit_trials=len(fit),inner_selection_trials=len(inner),validation_trials=len(validation),
      settings=cfg,test_evaluated=False,protocol=protocol,training_windows=counts,runtime_seconds=time.perf_counter()-started,
      hardware=dict(gpu=torch.cuda.get_device_name(),torch=torch.__version__,cuda=torch.version.cuda),provenance=provenance,
      ridge_control=rigde_summary(ridge),warning='Validation repeatedly reused historically; no blind or millimeter accuracy claim; all methods evaluated on v7 observed reference and inherited clock mapping.')
    save_json(out/'selection.json',selection)
    lines=['# Multi-horizon endpoint loss v9','','Three predefined seeds, matched short-loss control and endpoint-loss model. Conditional inner participant fold selects epoch/gain; every model is then refitted on all training data before the final validation is opened. Inherited pretrained base/calibration previously saw inner participants, so this is not independent whole-pipeline selection.','',
      'Endpoint horizons 1/3/5/10 seconds use observed optical start/end poses and uninterrupted IMU samples. Intermediate optical gaps are allowed; intermediate optical positions never enter endpoint loss. Five exact 512-sample contexts emit central 256-sample outputs, stitched differentiably into 1025 outputs; inference retains the same 1.28-second future context. Short control sees identical segments/context.','',
      '| Candidate | Validation RMSE (mm) |','|---|---:|']
    for name,s in candidates.items():lines.append(f"| {name} | {s['equal_participant_mean_position_rmse_m']*1000:.3f} |")
    lines.extend(['',f"Preselected deployment: **{selection['selected']}**. Validation does not select a seed or method.",
      '',f"Short median/min/max: {spread['short']['median_rmse_m']*1000:.3f}/{spread['short']['minimum_rmse_m']*1000:.3f}/{spread['short']['maximum_rmse_m']*1000:.3f} mm.",
      f"Endpoint median/min/max: {spread['endpoint']['median_rmse_m']*1000:.3f}/{spread['endpoint']['minimum_rmse_m']*1000:.3f}/{spread['endpoint']['maximum_rmse_m']*1000:.3f} mm.",
      '',f"Training {len(entries)} recordings; conditional inner fit {len(fit)}, inner selection {len(inner)}; validation {len(validation)}. Ridge control remains preserved in outputs_observed_ridge_v8; this comparator cannot replace it merely by choosing its best seed.",
      '',selection['warning']])
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    save_json(out/'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()}))
    print(json.dumps(dict(selected=selection['selected'],spread=spread,candidates=candidates)),flush=True)


def rigde_summary(selection):
    return dict(source='outputs_observed_ridge_v8/selection.json',best=selection['best'],reference='Existing 116.898 mm candidate remains control; not refitted or selected by this experiment')


if __name__=='__main__':main()
