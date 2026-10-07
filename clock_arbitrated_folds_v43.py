"""Three conditional participant-fold training-arbitrated-clock guard, no validation."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import json,time,gc
from pathlib import Path
import numpy as np
import torch
import pipeline as p
from clock_refit_experiment_v38 import entry,predict,common,load_cache,C,CUTOFF,BLEND,OLD,NEW
from participant_folds_experiment_v24 import FOLDS
from observed_ridge_inference import load_observed_ridge
from nonlinear_endpoint_experiment_v21 import bounds,adapted
from dynamic_tilt_experiment_v33 import clips_extra,expanded
from motion_endpoint_experiment_v16 import normal_system,fit

OUT=p.ROOT/'outputs_clock_arbitrated_folds_v43';BASE=p.ROOT/'outputs_dynamic_blend_v34';REFIT=p.ROOT/'outputs_clock_arbitrated_v42'
def main():
    started=time.perf_counter();torch.set_num_threads(4)
    if OUT.exists():raise RuntimeError('Preserve immutable fold audit')
    OUT.mkdir();(OUT/'common_trajectories').mkdir();protocol=json.loads((REFIT/'protocol.json').read_text());ids=protocol['training_ids'];fallback=set(protocol['fallback_old_clock_ids']);cfg=protocol['old_clock_settings']
    rows={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())};assert all(rows[id]['partition']=='train' for id in ids)
    cal=json.loads((p.ROOT/'outputs_amended_v2/calibration.json').read_text());states={q['id']:q for q in json.loads((p.ROOT/'outputs_stationary_gravity_v14/initialization.json').read_text())['records']}
    manifests={source:json.loads((source/'artifact_manifest.json').read_text()) for source in (OLD,NEW)};parent_manifest=json.loads((BASE/'artifact_manifest.json').read_text())['sha256'];ridge=load_observed_ridge()
    p.save_json(OUT/'protocol.json',dict(folds=[sorted(q) for q in FOLDS],training_ids=ids,fallback_ids=sorted(fallback),parameters=C,tilt_cutoff_hz=CUTOFF,blend=BLEND,
        control='Reused sealed same-fitting-ID oldclock foldcoefficients fromv34; verify473minusheldexactIDs',guard='Newclockrefitblend nativecommon equal-person mean andworstpersonratio<=1.05 vsoldclock samefoldblend',
        selection=False,validation_accessed=False,test_accessed=False,inherited_base_calibration=True,no_internal_resets=True,shared_native_initial_pose=True))
    training=[]
    for n,id in enumerate(ids):
        source=OLD if id in fallback else NEW;d,_=load_cache(source,id,manifests[source]);training.append(entry(rows[id],d,ridge,cal,states[id]))
        if (n+1)%50==0:print('Prepared correctedtrain',n+1,flush=True)
    allrecords=[];allcoverage=[]
    for i,held in enumerate(FOLDS):
        oldfile=BASE/f'fold_{i}_models.json'
        if p.digest(oldfile)!=parent_manifest[oldfile.name]:raise RuntimeError('Changed oldfold model')
        oldmodels=json.loads(oldfile.read_text());fitting=[e for e in training if e['row']['participant'] not in held];evaluation=[e for e in training if e['row']['participant'] in held]
        assert set(oldmodels['fit_ids'])=={e['row']['id'] for e in fitting} and set(oldmodels['held_people'])==held
        clips=bounds(fitting);extra=clips_extra(fitting)
        newmodel=dict(fits=fit(normal_system(adapted(fitting,C['basis'],clips)),.1,1.),feature_clip=clips)
        newtilt=dict(fits=fit(normal_system(expanded(fitting,clips,extra)),.1,1.),feature_clip=clips,extra_clip=extra,cutoff=CUTOFF)
        oldmodel=dict(fits=oldmodels['original'],feature_clip=oldmodels['feature_clip']);oldtilt=dict(fits=oldmodels['tilt'],feature_clip=oldmodels['feature_clip'],extra_clip=oldmodels['extra_clip'],cutoff=CUTOFF)
        p.save_json(OUT/f'fold_{i}_models.json',dict(v21=newmodel,tilt=newtilt,fitting_ids=[e['row']['id'] for e in fitting],held_ids=[e['row']['id'] for e in evaluation],old_model_sha256=p.digest(oldfile)))
        foldrecords=[];foldcoverage=[]
        for e in evaluation:
            row=e['row'];old,_=load_cache(OLD,row['id'],manifests[OLD]);eo=entry(row,old,ridge,cal,states[row['id']]);ov=predict(eo,oldmodel);ot=predict(eo,oldtilt,True);nv=predict(e,newmodel);nt=predict(e,newtilt,True)
            motions=dict(old_clock_v21=(old,ov),old_clock_blend=(old,(1-BLEND)*ov+BLEND*ot),new_clock_v21=(e['data'],nv),new_clock_blend=(e['data'],(1-BLEND)*nv+BLEND*nt))
            rr,cc=common(row,old,e['data'],motions,cfg,OUT);foldrecords.extend([dict(fold=i,**r) for r in rr]);foldcoverage.append(dict(fold=i,**cc))
        p.write_csv(OUT/f'fold_{i}_trials.csv',foldrecords);p.write_csv(OUT/f'fold_{i}_coverage.csv',foldcoverage);allrecords.extend(foldrecords);allcoverage.extend(foldcoverage);print('Completedfold',i,flush=True)
    p.write_csv(OUT/'trials.csv',allrecords);p.write_csv(OUT/'coverage.csv',allcoverage);summary={};people={}
    for name in sorted({r['method'] for r in allrecords}):
        ss,pp,mm=p.summarize([r for r in allrecords if r['method']==name]);summary[name]=ss;people[name]={q['participant']:q['mean_trial_position_rmse_m'] for q in pp}
        p.write_csv(OUT/(name+'_participants.csv'),pp);p.write_csv(OUT/(name+'_maneuvers.csv'),mm)
    ratios={person:people['new_clock_blend'][person]/value for person,value in people['old_clock_blend'].items()};worst=max(ratios.values());passed=worst<=1.05 and summary['new_clock_blend']['equal_participant_mean_position_rmse_m']<summary['old_clock_blend']['equal_participant_mean_position_rmse_m']
    p.save_json(OUT/'run.json',dict(summary=summary,participant_ratios=ratios,worst_person_ratio=worst,guard_passed=passed,validation_accessed=False,test_accessed=False,
        fitting_training_total=473,held_target_training_trials=len(allcoverage),inherited_base_calibration=True,runtime_seconds=time.perf_counter()-started,source_sha256=p.digest(Path(__file__))))
    lines=['# Training-arbitrated-clock conditional trainingfold guard v43','','Three predeclared participant folds. All473originalacceptedtrainIDs preserve8QCand3training-signal-arbitrationoldclockfallbacks. Oldcontrols reuse sealed models from EXACT same fittingIDs, not all-training coefficients. Newclips/caps/normalizers/coefficients fitted with noheldpersonlabels. No validation/test; base/calibration inherited, so conditional notfullpipelineindependent. Nativecommonobservedinitialpose shared; noresets.','', '| Model | Equal-person RMSE(mm) | Heading(deg) |','|---|---:|---:|']
    lines +=[f"| {n} | {s['equal_participant_mean_position_rmse_m']*1000:.6f} | {s['equal_participant_mean_heading_rmse_deg']:.6f} |" for n,s in summary.items()]
    lines +=['',f'Worstparticipant ratio newclockblend/oldclockblend: {worst:.6f}. Fixed5% guard passed: {passed}.', '', '| Participant | Ratio |','|---|---:|']+[f'| {person} | {ratio:.6f} |' for person,ratio in ratios.items()]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
