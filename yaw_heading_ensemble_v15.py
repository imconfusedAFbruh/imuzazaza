"""Fixed three-seed robustness comparison for the v12 yaw head."""
import json,time,shutil
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader,WeightedRandomSampler
from pipeline import ROOT,digest,save_json,write_csv
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from learning import training_group
from yaw_heading_experiment_v12 import YawTCN,Windows,HORIZONS,CONTEXT,imu_features,predict,score

def train_seed(entries,norm,seed,device):
    torch.manual_seed(seed);np.random.seed(seed);model=YawTCN().to(device);dataset=Windows(entries,norm)
    counts=Counter(dataset.groups);sampler=WeightedRandomSampler([1/counts[g] for g in dataset.groups],len(dataset),replacement=True)
    loader=DataLoader(dataset,batch_size=32,sampler=sampler,num_workers=0);optim=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.01);history=[]
    for epoch in range(1,13):
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
        row=dict(seed=seed,epoch=epoch,mean_training_loss=float(np.mean(losses)),training_windows=len(dataset));history.append(row);print('Epoch',row,flush=True)
    return model,history

def main():
    out=ROOT/'outputs_yaw_heading_ensemble_v15';parent=ROOT/'outputs_yaw_heading_v12'
    if out.exists():raise RuntimeError('Preserve ensemble experiment')
    out.mkdir();started=time.perf_counter();torch.set_num_threads(4);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    for name,sha in json.loads((parent/'artifact_manifest.json').read_text())['sha256'].items():
        if digest(parent/name)!=sha:raise RuntimeError('Changed sealed v12 artifact '+name)
    run=json.loads((parent/'run.json').read_text())
    for name,sha in run['provenance'].items():
        if digest(ROOT/name)!=sha:raise RuntimeError('Changed v12 dependency '+name)
    if run['selected']['epoch']!=12 or run['selected']['gain']!=.5:raise RuntimeError('Preselected protocol changed')
    norm=json.loads((parent/'normalization.json').read_text());source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge();entries=[]
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu);entries.append(dict(row=row,data=d,motion=m,x=imu_features(imu,m,cal),group=training_group(row)))
        if len(entries)%100==0:print('Prepared training',len(entries),flush=True)
    if [e['row']['id'] for e in entries]!=norm['training_ids'] or len(entries)!=473:raise RuntimeError('Normalization training coverage mismatch')
    shutil.copy2(parent/'normalization.json',out/'normalization.json');shutil.copy2(parent/'yaw_tcn.pt',out/'seed42.pt');shutil.copy2(parent/'refit_epoch_history.csv',out/'seed42_history.csv')
    for seed in (43,44):
        model,history=train_seed(entries,norm,seed,device);torch.save(dict(state={k:v.detach().cpu() for k,v in model.state_dict().items()},epoch=12,gain=.5,seed=seed),out/f'seed{seed}.pt');write_csv(out/f'seed{seed}_history.csv',history);del model
    models=[]
    for seed in (42,43,44):
        state=torch.load(out/f'seed{seed}.pt',map_location='cpu',weights_only=True);model=YawTCN().to(device).eval();model.load_state_dict(state['state']);models.append(model)
    validation=[];corrections=[[],[],[]]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu);e=dict(row=row,data=d,motion=m,x=imu_features(imu,m,cal));validation.append(e)
        for i,model in enumerate(models):corrections[i].append(predict(model,e['x'],norm,device))
    ensemble=[np.mean([corrections[j][i] for j in range(3)],axis=0) for i in range(len(validation))]
    summaries={}
    cases=[('ridge',corrections[0],0.)]+[(f'seed{seed}',corrections[i],.5) for i,seed in enumerate((42,43,44))]+[('ensemble',ensemble,.5)]
    for name,correction,gain in cases:
        (summary,people,conditions),records=score(validation,correction,gain,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',people),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    if abs(summaries['seed42']['equal_participant_mean_position_rmse_m']-run['summary']['selected']['equal_participant_mean_position_rmse_m'])>1e-8:raise RuntimeError('Seed42 reproduction mismatch')
    scores=[summaries[f'seed{s}']['equal_participant_mean_position_rmse_m'] for s in (42,43,44)]
    save_json(out/'run.json',dict(summary=summaries,seed_range_m=[min(scores),max(scores)],seed_median_m=float(np.median(scores)),seeds=[42,43,44],epoch=12,gain=.5,training_trials=len(entries),validation_trials=len(validation),test_evaluated=False,runtime_seconds=time.perf_counter()-started,device=str(device),selection='Fixed v12 conditional training-fold epoch12/gain.5; ensemble mean predeclared; no individual validation seed selection',provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'yaw_heading_experiment_v12.py',parent/'artifact_manifest.json',source/'artifact_manifest.json',ROOT/'observed_ridge_inference.py']}))
    lines=['# Fixed yaw-head seed robustness v15','','Seeds42/43/44 all use fixed12epochs andgain0.5 selected previously on the v12 training participant fold. Seed42 state/normalization were copied from sealed v12; seeds43/44 trained using the identical objective. No validation hyperparameter or seed selection. Ensemble averages capped yaw residuals before adding them to ridge. Forward/lateral remain unchanged.','',f'Individualseed median: {np.median(scores)*1000:.3f}mm; range {min(scores)*1000:.3f}–{max(scores)*1000:.3f}mm.','','| Method | Overall RMSE (mm) | Heading RMSE (degrees) |','|---|---:|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} | {v["equal_participant_mean_heading_rmse_deg"]:.3f} |' for k,v in summaries.items()]+['','The epoch/gain choice is conditional on the inherited predictor/calibration and repeatedly inspected validation remains exploratory. All473 training and71 validation acquisitions retain observed-reference masks, fixed synchronization and one initial pose. No test acquisitions read. Raw sensor conversion remains empirical. Circular endpoint losses cannot establish hidden full-turn counts. New head is causal, but inherited ridge features retain1.28s future IMU. No best-seed deployment is justified by this comparison alone.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
