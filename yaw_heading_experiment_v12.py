"""Yaw-only causal correction with observed endpoint-heading supervision."""
import json,time
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset,DataLoader,WeightedRandomSampler
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize,velocities
from learning import features,training_group
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from trajectory_calibration_v10 import integrate

FOLD={'No.3','No.8','No.15','No.20'};HORIZONS=(50,100,300,500,1000);CHECKPOINTS=(3,6,12,24,36);CONTEXT=30

class YawTCN(nn.Module):
    def __init__(self):
        super().__init__();self.input=nn.Conv1d(29,16,1);self.blocks=nn.ModuleList([nn.Conv1d(16,16,3,dilation=d) for d in (1,2,4,8)]);self.output=nn.Conv1d(16,1,1)
        nn.init.zeros_(self.output.weight);nn.init.zeros_(self.output.bias)
    def forward(self,x):
        x=F.silu(self.input(x))
        for layer,dilation in zip(self.blocks,(1,2,4,8)):x=x+F.silu(layer(F.pad(x,(2*dilation,0))))
        return self.output(x)[:,0]

def imu_features(d,m,cal):
    imu={k:d[k] for k in ('setup','t','raw','imu_valid')};c=cal[str(imu['setup'])];base=velocities(imu,c)
    center=np.c_[imu['raw'][:,12:15]/c['accel_counts_per_g'][2],(imu['raw'][:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale'])]
    return np.c_[features(imu,base,cal),center,m].astype(np.float32)

def normalization(entries):
    counts=Counter(e['group'] for e in entries);xs=[];ys=[];ws=[]
    for e in entries:
        mask=e['data']['imu_valid'];ids=np.flatnonzero(mask)[::10];xs.append(e['x'][ids]);ws.extend([1/counts[e['group']]/max(len(ids),1)]*len(ids))
        valid=e['data']['label_valid']&np.isfinite(e['data']['gt_yaw']);ys.extend((e['data']['gt_yaw']-e['motion'][:,2])[valid][::10])
    x=np.concatenate(xs);w=np.array(ws);w/=w.sum();mean=np.sum(x*w[:,None],axis=0);std=np.maximum(np.sqrt(np.sum((x-mean)**2*w[:,None],axis=0)),1e-5);y=np.array(ys)
    return dict(mean=mean.tolist(),std=std.tolist(),scale=max(float(np.std(y)),.02),cap=max(float(np.quantile(np.abs(y),.995)),.05),training_ids=[e['row']['id'] for e in entries])

class Windows(Dataset):
    def __init__(self,entries,norm):
        self.entries=entries;self.norm=norm;self.samples=[];self.groups=[]
        for i,e in enumerate(entries):
            d=e['data'];e['normalized']=((e['x']-norm['mean'])/norm['std']).astype(np.float32)
            for a in range(0,len(e['x'])-50,200):
                b=min(a+1001,len(e['x']))
                if not d['gt_valid'][a] or not d['imu_valid'][max(0,a-CONTEXT):b].all():continue
                if not any(a+h<b and d['gt_valid'][a+h] for h in HORIZONS):continue
                self.samples.append((i,a,b));self.groups.append(e['group'])
    def __len__(self):return len(self.samples)
    def __getitem__(self,index):
        i,a,b=self.samples[index];e=self.entries[i];d=e['data'];n=b-a
        x=np.zeros((29,CONTEXT+1001),np.float32);left=max(0,a-CONTEXT);offset=CONTEXT-(a-left);x[:,offset:CONTEXT+n]=e['normalized'][left:b].T
        target=np.zeros(1001,np.float32);mask=np.zeros(1001,bool);err=d['gt_yaw'][a:b]-e['motion'][a:b,2];valid=d['label_valid'][a:b]&np.isfinite(err);target[:n]=np.where(valid,err/self.norm['scale'],0);mask[:n]=valid
        endpoint=np.zeros(len(HORIZONS),np.float32);ev=np.zeros(len(HORIZONS),bool)
        for j,h in enumerate(HORIZONS):
            if a+h>=b or not d['gt_valid'][a+h]:continue
            delta=d['gt_heading'][a+h]-d['gt_heading'][a]-np.trapezoid(e['motion'][a:a+h+1,2],d['t'][a:a+h+1]);endpoint[j]=np.arctan2(np.sin(delta),np.cos(delta));ev[j]=True
        return x,target,mask,endpoint,ev

def predict(model,x,norm,device):
    x=((x-norm['mean'])/norm['std']).astype(np.float32);pieces=[]
    with torch.no_grad():
        for a in range(0,len(x),2048):
            left=max(0,a-CONTEXT);chunk=x[left:min(a+2048,len(x))]
            if a<CONTEXT:chunk=np.pad(chunk,((CONTEXT-a,0),(0,0)))
            result=model(torch.from_numpy(chunk.T[None]).to(device)).cpu().numpy()[0,CONTEXT:]
            pieces.append(np.clip(result*norm['scale'],-norm['cap'],norm['cap']))
    return np.concatenate(pieces)

def score(entries,corrections,gain,cfg):
    records=[]
    for e,c in zip(entries,corrections):
        m=e['motion'].copy();m[:,2]+=gain*c;xy,h=integrate(e['data'],m)
        records.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],setup=str(e['data']['setup']),**metrics(e['data'],xy,h,cfg)))
    return summarize(records),records

def train(entries,norm,epochs,device,callback=None):
    torch.manual_seed(42);np.random.seed(42);model=YawTCN().to(device);dataset=Windows(entries,norm)
    if not len(dataset):raise RuntimeError('No endpoint supported training windows')
    counts=Counter(dataset.groups);sampler=WeightedRandomSampler([1/counts[g] for g in dataset.groups],len(dataset),replacement=True)
    loader=DataLoader(dataset,batch_size=32,sampler=sampler,num_workers=0);optim=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.01);history=[]
    for epoch in range(1,epochs+1):
        model.train();losses=[]
        for x,y,mask,target,valid in loader:
            x,y,mask,target,valid=[v.to(device) for v in (x,y,mask,target,valid)];pred=torch.clamp(model(x)[:,CONTEXT:],-norm['cap']/norm['scale'],norm['cap']/norm['scale'])
            loss=F.smooth_l1_loss(pred[mask],y[mask]) if mask.any() else pred.sum()*0
            for j,h in enumerate(HORIZONS):
                good=valid[:,j]
                if not good.any():continue
                integral=(pred[good,:h]+pred[good,1:h+1]).sum(dim=1)*.005*norm['scale'];error=integral-target[good,j];error=torch.atan2(torch.sin(error),torch.cos(error));scale=max(.03,.25*norm['scale']*(h/100))
                loss+=.2*F.smooth_l1_loss(error/scale,torch.zeros_like(error))
            loss+=.01*pred.mean(dim=1).square().mean()+.001*(pred[:,1:]-pred[:,:-1]).square().mean()
            optim.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optim.step();losses.append(float(loss.detach().cpu()))
        row=dict(epoch=epoch,mean_training_loss=float(np.mean(losses)),training_windows=len(dataset));history.append(row);print('Epoch',row,flush=True)
        if callback and epoch in CHECKPOINTS:callback(model,epoch)
    return model,history

def main():
    out=ROOT/'outputs_yaw_heading_v12'
    if out.exists():raise RuntimeError('Preserve experiment')
    out.mkdir();started=time.perf_counter();torch.set_num_threads(4);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge();entries=[]
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu);entries.append(dict(row=row,data=d,motion=m,x=imu_features(imu,m,cal),group=training_group(row)))
        if len(entries)%100==0:print('Prepared training',len(entries),flush=True)
    fitrows=[e for e in entries if e['row']['participant'] not in FOLD];inner=[e for e in entries if e['row']['participant'] in FOLD];norm=normalization(fitrows);save_json(out/'inner_normalization.json',norm)
    (baseline,ppl,_),_=score(inner,[np.zeros(len(e['x'])) for e in inner],0,cfg);basepeople={p['participant']:p['mean_trial_position_rmse_m'] for p in ppl};candidates=[dict(epoch=0,gain=0.,score=baseline['equal_participant_mean_position_rmse_m'],heading=baseline['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=1.)]
    def checkpoint(model,epoch):
        model.eval();corrections=[predict(model,e['x'],norm,device) for e in inner];torch.save(dict(state={k:v.detach().cpu() for k,v in model.state_dict().items()},epoch=epoch),out/f'inner_epoch_{epoch}.pt')
        for gain in (.1,.25,.5,1.):
            (s,p,_),_=score(inner,corrections,gain,cfg);candidate=dict(epoch=epoch,gain=gain,score=s['equal_participant_mean_position_rmse_m'],heading=s['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(q['mean_trial_position_rmse_m']/basepeople[q['participant']] for q in p));candidates.append(candidate);print('Fold',candidate,flush=True)
    _,history=train(fitrows,norm,36,device,checkpoint);write_csv(out/'inner_epoch_history.csv',history)
    eligible=[c for c in candidates if c['worst_person_ratio']<=1.05];selected=min(eligible,key=lambda c:c['score']);nonzero=[c for c in eligible if c['gain']];comparison=min(nonzero or [c for c in candidates if c['gain']],key=lambda c:c['score']);refit=selected if selected['gain'] else comparison
    save_json(out/'inner_selection.json',dict(selected=selected,comparison=comparison,candidates=candidates,fold=sorted(FOLD),rule='Minimum equal-participant path RMSE subject to <=5% worst-person regression; unchanged ridge eligible',caveat='Inherited predictor/calibration previously saw training fold; conditional correction selection.'))
    norm=normalization(entries);save_json(out/'normalization.json',norm);model,history=train(entries,norm,refit['epoch'],device);write_csv(out/'refit_epoch_history.csv',history);torch.save(dict(state={k:v.detach().cpu() for k,v in model.state_dict().items()},epoch=refit['epoch'],gain=selected['gain'],comparison_gain=refit['gain']),out/'yaw_tcn.pt');model.eval();validation=[];corrections=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu);e=dict(row=row,data=d,motion=m,x=imu_features(imu,m,cal));validation.append(e);corrections.append(predict(model,e['x'],norm,device))
    summaries={}
    for name,gain in [('ridge',0.),('selected',selected['gain']),('comparison',refit['gain'])]:
        (s,p,c),records=score(validation,corrections,gain,cfg);summaries[name]=s
        for suffix,rows in [('trials',records),('participants',p),('maneuvers',c)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    save_json(out/'run.json',dict(summary=summaries,selected=selected,refit=refit,training_trials=len(entries),validation_trials=len(validation),test_evaluated=False,device=str(device),runtime_seconds=time.perf_counter()-started,invariants='Forward/lateral exactly ridge; yaw-only bounded residual; zero initialized output; IMU-only inference; no pose reset; observed endpoints only; no optical gap filling.',provenance={str(f.relative_to(ROOT)):digest(f) for f in [Path(__file__),source/'artifact_manifest.json',ROOT/'observed_ridge_inference.py',ROOT/'outputs_observed_ridge_v8/artifact_manifest.json']}))
    report=['# Yaw-only endpoint TCN v12','','Masked yaw-rate residual and relative-heading integrals at0.5/1/3/5/10 seconds. Endpoints must be observed; IMU inputs uninterrupted. The output head starts at zero. Thirty-frame causal context; physical scales remain empirical.','',f'Selected on fixed training fold: {selected}',f'Full-training refit: {refit}','','| Model | Overall RMSE (mm) | Heading RMSE (degrees) |','|---|---:|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} | {v["equal_participant_mean_heading_rmse_deg"]:.3f} |' for k,v in summaries.items()]+['','Checkpoint epochs3/6/12/24/36 and all fold gains are saved, so longer training can be inspected without validation checkpoint selection. Fixed-fold selection remains conditional on inherited predictors. Three independent seeds have not been run for this new head. Reused validation remains exploratory. No test acquisitions were read. Prediction uses only IMU features; initial pose is supplied separately. Forward and lateral outputs are unchanged. Low-frequency/DC correction and roughness penalties discourage unsupported drift. If zero wins, the best eligible nonzero fixed-fold head is preserved as a rejected comparison.']
    (out/'report.md').write_text('\n'.join(report)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(f.relative_to(out)):digest(f) for f in out.rglob('*') if f.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
