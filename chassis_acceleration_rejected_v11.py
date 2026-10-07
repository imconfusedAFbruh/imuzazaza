"""Save and evaluate the best rejected training-fold acceleration candidate."""
import json,time
from pathlib import Path
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import ROOT,save_json,write_csv,digest
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from chassis_acceleration_v11 import prepare,fit,score,correct,acceleration,integrate

def main():
    out=ROOT/'outputs_chassis_acceleration_v11_rejected_comparator'
    if out.exists():raise RuntimeError('Preserve rejected comparator')
    out.mkdir();torch.set_num_threads(4);source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];manifest=json.loads((source/'artifact_manifest.json').read_text());cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge()
    selection=json.loads((ROOT/'outputs_chassis_acceleration_v11/inner_selection.json').read_text());candidate=min([c for c in selection['candidates'] if c['gain'] and c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=candidate,status='Rejected: unchanged ridge had lower fixed-fold error',source=selection))
    train=[]
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};train.append(prepare(row,d,ridge(imu),cal[row['setup']]))
        if len(train)%100==0:print('Refit training',len(train),flush=True)
    fits=fit(train,candidate['alpha']);save_json(out/'model.json',dict(fits=fits,candidate=candidate,training_ids=[e['row']['id'] for e in train]))
    validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};validation.append(prepare(row,d,ridge(imu),cal[row['setup']]))
    summaries={};base=dict(alpha=0,**{'lambda':0},gain=0,prior_floor=1)
    for name,c,f in [('ridge',base,{}),('rejected_acceleration',candidate,fits)]:
        (summary,ppl,conditions),records=score(validation,f,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',ppl),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    trial='2026-09-25__PS__PS_Trial2_No.18';e=next(e for e in validation if e['row']['id']==trial);d=e['data'];m=correct(e,fits,candidate['lambda'],candidate['prior_floor'],candidate['gain']);a=acceleration(e,fits)
    fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True)
    axes[0].plot(d['t'],np.where(d['label_valid'],d['gt_v'],np.nan),'k',label='Observed derivative speed');axes[0].plot(d['t'],e['motion'][:,0],label='Ridge');axes[0].plot(d['t'],m[:,0],label='Rejected acceleration smoother');axes[0].set_ylabel('Forward speed (m/s)')
    axes[1].plot(d['t'],np.where(e['valid'],e['target'],np.nan),'k',label='Observed dv/dt (diagnostic only)');axes[1].plot(d['t'],a,label='Training empirical prediction');axes[1].plot(d['t'],e['wa'],label='Empirical wheel acceleration');axes[1].set_ylabel('Forward acceleration (m/s²)')
    for name,motion in [('Ridge',e['motion']),('Rejected smoother',m)]:
        xy,h=integrate(d,motion);axes[2].plot(d['t'],np.where(d['gt_valid'],1000*np.linalg.norm(xy-d['gt_xy'],axis=1),np.nan),label=name)
    axes[2].set_ylabel('Observed position error (mm)');axes[2].set_xlabel('Time (s)')
    for ax in axes:ax.grid(alpha=.2);ax.legend();ax.axvspan(1.5,2.8,color='red',alpha=.08)
    fig.suptitle('PS No.18 Trial 2: empirical acceleration smoother rejected on training fold');fig.tight_layout();fig.savefig(out/'braking_comparator.png',dpi=160);plt.close(fig)
    save_json(out/'run.json',dict(summary=summaries,selected=candidate,status='Rejected on training fold; comparison only',training_trials=len(train),validation_trials=len(validation),test_evaluated=False,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'chassis_acceleration_v11.py',ROOT/'outputs_chassis_acceleration_v11/inner_selection.json',source/'artifact_manifest.json']}))
    text=['# Best rejected chassis acceleration candidate','','All24 acceleration smoother candidates failed to beat the unchanged ridge on the predeclared training participant fold. This artifact preserves the lowest-error nonzero candidate, chosen using that fold only, with full473-recording empirical acceleration-model refit and a single71-recording evaluation of this candidate. It is rejected, not the selected deployment model.','',f'Candidate: {candidate}','','| Method | Overall RMSE (mm) |','|---|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for k,v in summaries.items()]+['','The primary v11 artifact reports the selected unchanged baseline. This separate fixed-fold rejected candidate is saved for physical/model diagnosis; no validation-driven tuning was performed. Factory accelerometer conversion and mounting attitude remain unverified. Lateral/yaw remain exactly ridge predictions. The center empirical acceleration features and velocity measurement share sensor/model information, so independence is not assumed. Full-recording offline filtering/smoothing uses future IMU. No held-out reference updates, stationarity refitting, trajectory alignment or condition-specific deployment rules. No test signals read.']
    (out/'report.md').write_text('\n'.join(text)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
