"""Validation-only ablation: mean-square process covariance versus robust median.

Run: python covariance_filter_experiment.py
"""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
from alternatives import cached_trials, gru_predictor, filtered_predictor, artifact_hashes
from learning import load_predictor, training_group
from pipeline import ROOT, velocities, evaluate, save_json, digest


def process_covariance(trials):
    sums, counts = defaultdict(lambda: np.zeros(2)), defaultdict(int)
    for row, data, _ in trials:
        truth = np.c_[data['gt_v'], data['gt_yaw']]
        mask = data['label_valid'] & data['imu_valid'] & np.isfinite(truth).all(axis=1)
        contiguous = mask[1:] & mask[:-1]
        delta = np.diff(truth, axis=0)[contiguous]
        group = training_group(row)
        sums[group] += np.sum(delta ** 2, axis=0); counts[group] += len(delta)
    moments = [sums[g] / counts[g] for g in sums if counts[g]]
    if not moments: raise ValueError('No contiguous training labels')
    return np.maximum(np.mean(moments, axis=0), [1e-8, 1e-9])


def check():
    t = np.arange(10.)
    data = dict(gt_v=t, gt_yaw=2*t, label_valid=np.ones(10,bool), imu_valid=np.ones(10,bool))
    row = dict(participant='one', date='synthetic')
    np.testing.assert_allclose(process_covariance([(row,data,{})]), [1,4])
    data['label_valid'][4:6] = False
    np.testing.assert_allclose(process_covariance([(row,data,{})]), [1,4])


def main():
    check(); torch.set_num_threads(2)
    source, parent = ROOT/'outputs_amended_v2', ROOT/'outputs_alternatives_v3'
    out=ROOT/'outputs_covariance_v4_checked'; out.mkdir(exist_ok=True)
    if (out/'selection.json').exists(): raise RuntimeError('Selected run already exists')
    parent_freeze=json.loads((source/'final_test_lock.json').read_text())['freeze']
    for path,key in [(ROOT/'pipeline.py','code_sha256'),(ROOT/'learning.py','learning_code_sha256')]:
        if digest(path)!=parent_freeze[key]: raise RuntimeError('Frozen parent source changed')
    for name,sha in parent_freeze['artifacts'].items():
        if digest(source/name)!=sha: raise RuntimeError('Frozen parent artifact changed')
    selected=json.loads((parent/'selection.json').read_text())
    if selected['artifacts']!=artifact_hashes(source,parent): raise RuntimeError('Frozen GRU comparison changed')
    if json.loads((parent/'retrospective_test_lock.json').read_text())['selection_sha256']!=digest(parent/'selection.json'):
        raise RuntimeError('Frozen comparison selection changed')
    cfg=json.loads((source/'run.json').read_text())['settings']
    calibration=json.loads((source/'calibration.json').read_text())
    norm=json.loads((source/'normalization.json').read_text())
    train=cached_trials(source,'train',cfg)
    q=process_covariance(train); del train
    validation=cached_trials(source,'validation',cfg)
    uncertainty=json.loads((parent/'uncertainty.json').read_text())
    candidates={}; history=[]
    for name,predictor in [('tcn32',load_predictor(source,'tcn32')),
                           ('gru32',gru_predictor(parent,calibration,norm))]:
        predicted={id(d):predictor(d,velocities(d,calibration[r['setup']])) for r,d,_ in validation}
        uncertainty[name]['process_variance']=q.tolist()
        fixed=lambda d,b:predicted[id(d)]
        scores=[]
        for multiplier in (.25,1.,4.):
            model_name=name+'_mean_q_'+str(multiplier)
            score=evaluate(validation,calibration,cfg,out,name=model_name,export=False,
                  predictor=filtered_predictor(fixed,uncertainty[name],calibration,norm,multiplier))
            if score['trials'] != len(validation) or score['failed_reconstructions']:
                raise RuntimeError('Candidate coverage differs')
            history.append(dict(model=name,multiplier=multiplier,summary=score))
            scores.append((multiplier,score))
            print(model_name,score,flush=True)
        multiplier,score=min(scores,key=lambda p:p[1]['equal_participant_mean_position_rmse_m'])
        candidates[name]=dict(multiplier=multiplier,summary=score)
    paths=[Path(__file__),ROOT/'pipeline.py',ROOT/'learning.py',ROOT/'alternatives.py',
           source/'final_test_lock.json',source/'calibration.json',source/'normalization.json',source/'tcn32.pt',
           source/'split.json',source/'run.json',source/'inventory.json',source/'qc_train.csv',source/'qc_validation.csv',
           parent/'gru32.pt',parent/'uncertainty.json']
    save_json(out/'selection.json',dict(process_variance=q.tolist(),candidates=candidates,history=history,
             provenance={str(p):digest(p) for p in paths},test_evaluated=False,
             criterion='equal-participant mean validation trajectory RMSE',
             change='equal-training-group mean squared adjacent valid GT rate increments instead of pooled median'))
    save_json(out/'uncertainty.json',uncertainty)
    lines=['# Process covariance ablation','','Training-only mean-square process variance, equal group weights. '
           'Same frozen motion predictors, feature scaling, uncertainty observation model and validation recordings. '
           'No test data evaluated. This is a diagonal rate filter, not a full navigation estimator.','',
           '| Predictor + filter | Best validation RMSE (m) | Process multiplier |','|---|---:|---:|']
    for name,c in candidates.items():
        lines.append(f"| {name} | {c['summary']['equal_participant_mean_position_rmse_m']:.4f} | {c['multiplier']} |")
    lines+=['','Frozen unfiltered TCN validation RMSE: 0.3747 m. '
            'All candidates score the same 72 recordings from four participants. '
            'In-sample training uncertainty and empirical sensor calibration limitations remain.','']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__': main()
