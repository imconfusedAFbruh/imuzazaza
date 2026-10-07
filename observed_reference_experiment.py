"""Correct C3D observation validity; isolate initialization on fixed alignment.

Zero-residual coordinates are processed values, not original measurements.
Camera masks are optional; enforce their support when populated in the export.
Run: python observed_reference_experiment.py
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

import pipeline as p
from learning import load_predictor
from planar_experiment import verify_parent, planar_features, integrate_planar
from planar_neural_experiment import PlanarResNet, predict_windows
from refined_training_experiment import refined_rows

ORIGINAL_READ = p.read_markers
ORIGINAL_SYNC = p.synchronize


def observed_markers(path):
    points, valid, hz = ORIGINAL_READ(path)
    c = p.ezc3d.c3d(str(path)); labels = [s.strip() for s in c['parameters']['POINT']['LABELS']['value']]
    ids = [labels.index(s) for s in ('L_FAL','R_FAL')]
    residual = c['data']['meta_points']['residuals'][0,ids,:].T
    valid &= (residual > 0).all(axis=1)
    masks = c['data']['meta_points'].get('camera_masks')
    if masks is not None:
        support = np.asarray(masks)[:,ids,:].any(axis=0).T
        if support.any(): valid &= support.all(axis=1)
    return points,valid,hz


def load_planar():
    folder = p.ROOT / 'outputs_planar_neural_v4'
    norm = json.loads((folder / 'normalization.json').read_text())
    mean,std,scale,cap = [np.array(norm[k],np.float32) for k in ('mean','std','target_scale','residual_cap')]
    state = torch.load(folder / 'all_three.pt',map_location='cpu',weights_only=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PlanarResNet().to(device).eval(); model.load_state_dict(state['state'])
    def motion(data,cal,tcn_predict):
        base = p.velocities(data,cal[str(data['setup'])]); tcn = tcn_predict(data,base)
        x = (planar_features(data,base,tcn,cal).astype(np.float32)-mean)/std
        correction = state['gain']*np.clip(predict_windows(model,x,device)*scale,-cap,cap)
        return np.c_[tcn[:,0],np.zeros(len(tcn)),tcn[:,1]]+correction
    return motion


def planar_record(row,data,motion,cfg,mask=None):
    xy,heading = integrate_planar(data['t'],motion,data['gt_xy'][0],data['gt_heading'][0],data['imu_valid'])
    scoring = data if mask is None else dict(data,gt_valid=mask)
    return dict(id=row['id'],participant=row['participant'],condition=row['condition'],
                **p.metrics(scoring,xy,heading,cfg)),xy,heading


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume',action='store_true',help='Resume an incomplete run only; sealed results cannot be overwritten')
    args=parser.parse_args()
    started=time.perf_counter(); torch.set_num_threads(4)
    source,parent,out=p.ROOT/'outputs_synchronization_v5',p.ROOT/'outputs_amended_v2',p.ROOT/'outputs_observed_reference_v7'
    if out.exists() and (not args.resume or (out/'comparison.json').exists() or (out/'run.json').exists()):
        raise RuntimeError('Preserve existing experiment; --resume is allowed only for incomplete runs')
    provenance=verify_parent(parent)
    previous=json.loads((p.ROOT/'outputs_refined_training_v6/selection.json').read_text())
    for name,sha in previous['provenance'].items():
        if p.digest(p.ROOT/name)!=sha: raise RuntimeError(f'Frozen input changed: {name}')
    run=json.loads((source/'run.json').read_text()); cfg=run['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    cal=json.loads((parent/'calibration.json').read_text())
    corrected_cfg=dict(cfg,reference_observation_rule='positive residual; camera support when populated',
                       reference_protocol='v7: fixed parent clock alignment; observed initial pose and score frames')
    out.mkdir(exist_ok=args.resume); save=p.save_json
    if args.resume:
        save(out/'resumption.json',dict(reason='Initial run stopped on a recording with insufficient observed derivative labels',
             archived_source_sha256=p.digest(out/'aborted_source.py'),
             change='Classify existing preparation insufficiency as a QC exclusion; reuse only fingerprint-matching caches',
             source_sha256=p.digest(Path(__file__))))
    tcn_predict=load_predictor(parent,'tcn32'); neural_motion=load_planar()
    training=[]; validation=[]; qc=[]; common_old=[]; common_new=[]; original_all=[]
    old_sync=None; train_people=set()
    try:
        p.read_markers=observed_markers
        # This isolation experiment does not re-optimize alignment against the new
        # reference. Each recording inherits its sealed external clock mapping.
        p.synchronize=lambda *args,**kwargs:dict(old_sync,alignment_inherited=True)
        for partition in ('train','validation'):
            for row,old,meta in refined_rows(source,cfg,partition,manifest):
                if partition=='train': train_people.add(row['participant'])
                elif row['participant'] in train_people: raise RuntimeError('Participant overlap')
                record={k:row[k] for k in ('id','participant','condition','partition')}
                old_sync=meta['synchronization']
                try:
                    data,new_meta=p.prepare(row,p.ROOT,out,corrected_cfg)
                    shift=int(round((data['ref_t'][0]-old['ref_t'][0])*cfg['hz']))
                    record.update(status='accepted',initial_trim_s=float(data['ref_t'][0]-old['ref_t'][0]),
                         original_heading_deg=float(np.rad2deg(old['gt_heading'][0])),
                         corrected_heading_deg=float(np.rad2deg(data['gt_heading'][0])),
                         original_reference_frames=int(old['gt_valid'].sum()),observed_frames=int(data['gt_valid'].sum()))
                    if partition=='train': training.append((row,data,new_meta))
                    else:
                        validation.append((row,data,new_meta))
                        old_motion=neural_motion(old,cal,tcn_predict)
                        original_record,old_xy,old_h=planar_record(row,old,old_motion,cfg)
                        original_all.append(original_record)
                        # Score the OLD reconstruction on exactly the same supported
                        # frames; this distinguishes validity/initialization from merely
                        # omitting difficult frames. No pose correction of the old path.
                        mask=np.zeros(len(old['t']),bool)
                        if shift<0 or shift+len(data['t'])!=len(mask): raise RuntimeError('Fixed clocks differ')
                        mask[shift:]=data['gt_valid']
                        common_old.append(dict(record,**p.metrics(dict(old,gt_valid=mask),old_xy,old_h,cfg)))
                        new_motion=neural_motion(data,cal,tcn_predict)
                        corrected_record,xy,h=planar_record(row,data,new_motion,corrected_cfg)
                        common_new.append(corrected_record)
                        folder=out/'plots'; folder.mkdir(exist_ok=True)
                        if row['condition'] in ('OS','PS'):
                            import matplotlib
                            matplotlib.use('Agg')
                            import matplotlib.pyplot as plt
                            fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
                            reference=old['gt_xy'].copy(); reference[~mask]=np.nan
                            origin=data['gt_xy'][0]
                            ax.plot(*(reference-origin).T,'k',label='Observed MoCap')
                            ax.plot(*(old_xy[shift:]-origin).T,'--',color='#a34c36',label='Old initialization')
                            ax.plot(*(xy-origin).T,color='#1676b8',label='Observed initial pose')
                            ax.scatter(0,0,color='black',s=25)
                            ax.set(title=row['id'],xlabel='X (m)',ylabel='Y (m)');ax.set_aspect('equal',adjustable='datalim')
                            ax.legend();ax.grid(alpha=.2);fig.savefig(folder/(row['id']+'.png'),dpi=160);plt.close(fig)
                except p.TrialRejected as exc:
                    record.update(status='excluded',stage=exc.stage,reason=str(exc))
                except ValueError as exc:
                    if str(exc) not in ('Insufficient valid derivative labels','No valid initial reference pose'):
                        raise
                    record.update(status='excluded',stage='reference',reason=str(exc))
                qc.append(record)
                if len(qc)%50==0: print(f'{len(qc)} corrected recordings, {len(training)} train/{len(validation)} validation accepted',flush=True)
    finally:
        p.read_markers=ORIGINAL_READ;p.synchronize=ORIGINAL_SYNC
    corrected_cal=p.calibrate(training,corrected_cfg)
    save(out/'calibration.json',corrected_cal)
    results={}
    for name,records in [('old_full_on_matched_recordings',original_all),('old_same_observed_frames',common_old),
                         ('corrected_initialization_same_observed_frames',common_new)]:
        summary,people,conditions=p.summarize(records);results[name]=summary
        for suffix,rows in [('trials',records),('participants',people),('maneuvers',conditions)]:
            p.write_csv(out/(name+'_'+suffix+'.csv'),rows)
    results['physics_refit_observed']=p.evaluate(validation,corrected_cal,corrected_cfg,out,name='physics_refit_observed',export=False)
    results['physics_frozen_observed']=p.evaluate(validation,cal,corrected_cfg,out,name='physics_frozen_observed',export=False)
    p.write_csv(out/'qc.csv',qc)
    files=[Path(__file__),source/'artifact_manifest.json',source/'run.json',out/'calibration.json']
    provenance.update({str(f.relative_to(p.ROOT)):p.digest(f) for f in files})
    save(out/'run.json',dict(settings=corrected_cfg,training_trials=len(training),validation_trials=len(validation),
         test_evaluated=False,provenance=provenance,alignment='inherited fixed v5 mapping, not refitted',
         warning='Corrected reference coverage differs; compare old vs new on identical supported frames. Original results invalid as raw-MoCap accuracy.'))
    save(out/'comparison.json',dict(candidates=results,runtime_seconds=time.perf_counter()-started,test_evaluated=False))
    lines=['# Reference observation validity correction','','The old reader accepted residual >=0. '
           'C3D zero residuals denote processed/modelled/interpolated points. These files contain zero-residual '
           'leading and trailing points with no camera support; some leading headings are extrapolated. '
           'The corrected reader requires positive residuals and camera support when masks are populated. '
           'Camera masks are optional; an entirely absent/unpopulated mask alone is not rejected.','',
           'This isolates reference validity and initial-pose selection while holding v5 alignment and neural weights fixed. '
           'The old path is rescored on the identical supported frames without resetting or fitting it. '
           'The corrected reconstruction starts at its first observed reference pose; later reference gaps never reset it. '
           'Physics is also refitted on observed training labels only.','',
           '| Evaluation | RMSE (mm) | Recordings | Participants |','|---|---:|---:|---:|']
    for name,result in results.items(): lines.append(f'| {name} | {result["equal_participant_mean_position_rmse_m"]*1000:.3f} | {result["trials"]} | {result["participants"]} |')
    lines += ['',f'Training accepted: {len(training)}/477. Validation accepted: {len(validation)}/72. Coverage and initialization changes are in qc.csv.',
              '', '[C3D residual specification](https://www.c3d.org/HTML/Documents/gloss_residual.htm). '
              'This is a protocol correction, not evidence of improved sensor accuracy on the previous full duration. '
              'Test recordings remain unopened. Full synchronization/learning should subsequently use observed labels.','']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(results),flush=True)


if __name__=='__main__': main()
