"""CPU fixed-fold convex channel blend of independently refitted v16/v17 heads."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import json,time,itertools
from pathlib import Path
import numpy as np
import torch
from pipeline import ROOT,digest,save_json,write_csv,metrics,summarize
from observed_training_experiment import observed_rows
from observed_ridge_inference import load_observed_ridge
from stationary_gravity_experiment_v14 import feature_matrix
from motion_endpoint_experiment_v16 import normal_system,fit as fit_endpoint
from braking_context_experiment_v17 import features,fit as fit_forward
from trajectory_calibration_v10 import integrate

FOLD={'No.3','No.8','No.15','No.20'}
def grid():
    result=[];seen=set()
    for forward16,yaw16,forward17 in itertools.product((0.,.5,1.),repeat=3):
        total=forward16+forward17;scale=max(total,1.);a,b=forward16/scale,forward17/scale;key=(a,yaw16,b)
        if key in seen:continue
        seen.add(key);result.append(dict(forward16=a,yaw16=yaw16,forward17=b))
    return result
GRID=grid()

def prediction(e,f16,f17,c):
    m=e['motion'].copy();a,b,y=c['forward16'],c['forward17'],c['yaw16']
    if a or y:
        model=f16[e['setup']];z=np.c_[(e['x16']-model['mean'])/model['std'],np.ones(len(m))];r16=.5*np.clip(z@model['weights'],-np.array(model['cap']),np.array(model['cap']))
        m[:,0]+=a*r16[:,0];m[:,2]+=y*r16[:,1]
    if b:
        model=f17[e['setup']];z=np.c_[(e['x17']-model['mean'])/model['std'],np.ones(len(m))];r17=.5*np.clip(z@model['weights'],-model['cap'],model['cap']);m[:,0]+=b*r17
    return m
def score(entries,f16,f17,c,cfg):
    records=[]
    for e in entries:
        xy,h=integrate(e['data'],prediction(e,f16,f17,c));records.append(dict(id=e['row']['id'],participant=e['row']['participant'],condition=e['row']['condition'],**metrics(e['data'],xy,h,cfg)))
    return summarize(records),records
def adapt16(entries):
    return [dict(e,x=e['x16'],label=e['label16'],target=e['target16']) for e in entries]
def adapt17(entries):
    return [dict(e,x={.5:e['x17']},label=e['label17'],target=e['target17']) for e in entries]
def parents():
    result={}
    for name in ('outputs_motion_endpoint_v16','outputs_braking_context_v17'):
        p=ROOT/name;manifest=json.loads((p/'artifact_manifest.json').read_text())
        for n,sha in manifest['sha256'].items():
            if digest(p/n)!=sha:raise RuntimeError('Changed parentartifact '+name+'/'+n)
        for n,sha in json.loads((p/'run.json').read_text())['provenance'].items():
            if digest(ROOT/n)!=sha:raise RuntimeError('Changed parentsource '+n)
        result[name]=(p,manifest)
    return result
def load_training(pp):
    p16,m16=pp['outputs_motion_endpoint_v16'];p17,m17=pp['outputs_braking_context_v17'];entries=[]
    for path in sorted((p16/'prepared_training').glob('*.npz')):
        metadata=json.loads(path.with_suffix('.json').read_text());row=metadata['row']
        if row['partition']!='train':raise RuntimeError('Nontrainingpreparedrecord')
        with np.load(path) as z:
            feature=z['features'];motion=z['ridge_motion'];target=z['residual_target'];label=z['residual_label_valid'];data={k:z[k] for k in z.files if k not in ('features','ridge_motion','residual_target','residual_label_valid')}
        with np.load(p17/'training_features'/(row['id']+'.npz')) as z:
            if not np.array_equal(z['t'],data['t']) or not np.array_equal(z['imu_valid'],data['imu_valid']) or np.max(np.abs(z['base_motion']-motion))>1e-10:raise RuntimeError('Parentmotion/timing mismatch')
            x17=z['x05'];target17=z['target_forward_residual'];label17=z['observed_label_valid']
        entries.append(dict(row=row,data=data,motion=motion,x16=feature,x17=x17,target16=target,target17=target17,label16=label,label17=label17,setup=row['setup'],group=row['date']+':unmapped' if row['participant']=='earlier-unmapped' else row['participant']))
    if len(entries)!=473:raise RuntimeError('Trainingcoveragechanged')
    return entries
def main():
    start=time.perf_counter();out=ROOT/'outputs_motion_blend_v20'
    if out.exists():raise RuntimeError('Preserveblendexperiment')
    out.mkdir();torch.set_num_threads(4)
    if torch.cuda.is_available():raise RuntimeError('CPUonly')
    pp=parents();save_json(out/'predeclared_grid.json',dict(candidates=GRID,fold=sorted(FOLD),base_endpoint_parameters=dict(alpha=.1,endpoint_weight=1.,gain=.5),base_forward_parameters=dict(context=.5,alpha=.1,gain=.5),forward_weights='Normalize forward16+forward17 to sum<=1; convex clipped residual mixture, no doubled magnitude',selection='Best equalparticipantpathRMSEwith<=5%worstpersonregression;zeroandcurrentv16 included',test_evaluated=False));source=ROOT/'outputs_observed_reference_v7';cfg=json.loads((source/'run.json').read_text())['settings'];train=load_training(pp);inner=[e for e in train if e['row']['participant'] in FOLD];fitrows=[e for e in train if e['row']['participant'] not in FOLD];f16=fit_endpoint(normal_system(adapt16(fitrows)),.1,1.);f17=fit_forward(adapt17(fitrows),.5,.1);zero=dict(forward16=0.,yaw16=0.,forward17=0.);(_,people,_),_=score(inner,f16,f17,zero,cfg);baseline={p['participant']:p['mean_trial_position_rmse_m'] for p in people};candidates=[];trials=[]
    for c in GRID:
        (summary,people,conditions),records=score(inner,f16,f17,c,cfg);c=dict(c,score=summary['equal_participant_mean_position_rmse_m'],heading=summary['equal_participant_mean_heading_rmse_deg'],worst_person_ratio=max(p['mean_trial_position_rmse_m']/baseline[p['participant']] for p in people));candidates.append(c);trials.extend([dict(candidate_index=len(candidates)-1,**r) for r in records]);print('inner',c,flush=True)
    selected=min([c for c in candidates if c['worst_person_ratio']<=1.05],key=lambda c:c['score']);save_json(out/'inner_selection.json',dict(selected=selected,candidates=candidates,fold=sorted(FOLD),caveat='Both residualheads/norms/caps refitEXCLUDINGfold;inheritedridge/calibrationpreviouslysawfold;sameconditionalfoldreusedforfinitecompositeselection'));write_csv(out/'inner_trials.csv',trials)
    f16=fit_endpoint(normal_system(adapt16(train)),.1,1.);f17=fit_forward(adapt17(train),.5,.1)
    errors={}
    for label,f,parent in [('endpoint',f16,pp['outputs_motion_endpoint_v16'][0]),('forward',f17,pp['outputs_braking_context_v17'][0])]:
        old=json.loads((parent/'model.json').read_text())['fits'];errors[label]=max(float(np.max(np.abs(np.array(f[k]['weights'])-old[k]['weights']))) for k in f)
        if errors[label]>1e-6:raise RuntimeError('Parentfulltrainingcoefficientsdifferent '+label)
    save_json(out/'model.json',dict(selected=selected,endpoint_fits=f16,forward_fits=f17,training_ids=[e['row']['id'] for e in train],parent_max_weight_differences=errors));del train,inner,fitrows
    manifest=json.loads((source/'artifact_manifest.json').read_text());states={r['id']:r for r in json.loads((ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']};cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());ridge=load_observed_ridge();validation=[]
    for row,d,_ in observed_rows(source,cfg,'validation',manifest):
        imu={k:d[k] for k in ('setup','t','raw','imu_valid')};m=ridge(imu);state=states[row['id']];validation.append(dict(row=row,data=d,motion=m,x16=feature_matrix(imu,m,cal[row['setup']],state,'gravity_rotation'),x17=features(imu,m,cal[row['setup']],state,.5),setup=row['setup']))
    summaries={}
    for name,c in [('cpu_ridge',zero),('v16_endpoint',dict(forward16=1.,yaw16=1.,forward17=0.)),('selected_blend',selected)]:
        (summary,people,conditions),records=score(validation,f16,f17,c,cfg);summaries[name]=summary
        for suffix,rows in [('trials',records),('participants',people),('maneuvers',conditions)]:write_csv(out/f'{name}_{suffix}.csv',rows)
    parent_score=json.loads((pp['outputs_motion_endpoint_v16'][0]/'run.json').read_text())['summary']['endpoint']['equal_participant_mean_position_rmse_m']
    if abs(summaries['v16_endpoint']['equal_participant_mean_position_rmse_m']-parent_score)>1e-8:raise RuntimeError('v16scorefailedreproduction')
    save_json(out/'run.json',dict(summary=summaries,selected=selected,training_trials=473,validation_trials=len(validation),test_evaluated=False,cpu_only=True,runtime_seconds=time.perf_counter()-start,parent_max_weight_differences=errors,provenance={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'motion_endpoint_experiment_v16.py',ROOT/'braking_context_experiment_v17.py',ROOT/'stationary_gravity_experiment_v14.py',ROOT/'outputs_motion_endpoint_v16/artifact_manifest.json',ROOT/'outputs_braking_context_v17/artifact_manifest.json',source/'artifact_manifest.json',ROOT/'outputs_amended_v2/calibration.json']}));lines=['# Convex motion channel blend v20','','Both residualheads refitexcludingfixedfoldparticipants before selection. Hyperparametersfixedto parent training-selected values. Convexforwardmixture preventsdoublecountingclippedresidualmagnitude; yawweightseparate; lateralunchangedridge. No date/condition/person inference switches.','',f'Selected: {selected}','','| Model | Overall RMSE(mm) |','|---|---:|']+[f'| {k} | {v["equal_participant_mean_position_rmse_m"]*1000:.3f} |' for k,v in summaries.items()]+['','All-trainingrefit reproducedparentweights<=1e-6 and v16pairedscore<=1e-8m. Sameobservedreferenceframes/clocks/initialpose. Conditionalfoldcaveat remains for inheritedridge/calibration; repeatedvalidationexploratory. No testacquisitions read.'];(out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}));print(json.dumps(summaries,indent=2),flush=True)
if __name__=='__main__':main()
