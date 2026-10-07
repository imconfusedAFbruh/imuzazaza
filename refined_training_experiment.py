"""Retrain the planar residual on frozen v5 synchronized training recordings.

Run: python refined_training_experiment.py
Fixed 12 epochs, participant-balanced sampling, validation-only checkpoint/gain
selection; test signals are forbidden. Inherited TCN and physical scales stay fixed.
"""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler

from pipeline import ROOT, digest, save_json, write_csv, velocities
from learning import Windows, training_group, load_predictor
from planar_experiment import verify_parent, lateral_labels, planar_features
from planar_neural_experiment import PlanarResNet, predict_windows, planar_loss, evaluate_planar
from synchronization_experiment import neural_score


def refined_rows(source, cfg, partition, manifest):
    if partition not in ('train', 'validation'):
        raise ValueError('Test signals forbidden during development')
    parent = ROOT / 'outputs_amended_v2'
    rows = {r['id']:r for r in json.loads((parent / 'inventory.json').read_text())}
    original = {r['id']:r for r in json.loads((parent / 'input_identity_audit.json').read_text())['records']}
    fingerprint = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    accepted = [r for r in json.loads((source / 'alignment.json').read_text()) if r['partition'] == partition]
    if len(accepted) != (477 if partition == 'train' else 72):
        raise RuntimeError('Parent accepted coverage changed')
    for record in accepted:
        row = rows[record['id']]
        if row['partition'] != partition or original[row['id']]['partition'] != partition:
            raise RuntimeError('Partition metadata differs')
        path = source / 'cache' / (row['id'] + '.npz')
        metadata = path.with_suffix('.json')
        for file in (path, metadata):
            if digest(file) != manifest['sha256'][str(file.relative_to(source))]:
                raise RuntimeError(f'Refined cache changed: {file}')
        meta = json.loads(metadata.read_text())
        if meta['signature']['settings_sha256'] != fingerprint or meta['signature']['preparation_version'] != 2:
            raise RuntimeError('Stale refined preparation settings')
        for kind in ('imu','c3d'):
            sha = digest(ROOT / row[kind])
            if sha != meta['signature'][kind + '_sha256'] or sha != original[row['id']][kind + '_sha256']:
                raise RuntimeError(f'Raw acquisition changed: {row["id"]}')
        with np.load(path) as z:
            yield row, {k:z[k] for k in z.files}, meta


def main():
    started = time.perf_counter()
    source, parent, out = ROOT / 'outputs_synchronization_v5', ROOT / 'outputs_amended_v2', ROOT / 'outputs_refined_training_v6'
    if out.exists(): raise RuntimeError('Preserve existing experiment; choose a new version for another run')
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required for this fixed training run')
    provenance = verify_parent(parent)
    manifest = json.loads((source / 'artifact_manifest.json').read_text())
    # Seal checks include only the development caches and their diagnostic files.
    for name, sha in manifest['sha256'].items():
        if digest(source / name) != sha: raise RuntimeError(f'Synchronization artifact changed: {name}')
    run = json.loads((source / 'run.json').read_text())
    for name, sha in run['provenance'].items():
        if digest(ROOT / name) != sha: raise RuntimeError(f'Synchronization dependency changed: {name}')
    neural_source = ROOT / 'outputs_planar_neural_v4'
    old_selection = json.loads((neural_source / 'selection.json').read_text())
    for name, sha in old_selection['artifacts'].items():
        if digest(name) != sha: raise RuntimeError(f'Frozen neural artifact changed: {name}')
    out.mkdir(); torch.set_num_threads(4); torch.manual_seed(42); np.random.seed(42)
    device = torch.device('cuda'); cfg = run['settings']
    cal = json.loads((parent / 'calibration.json').read_text())
    tcn_predict = load_predictor(parent, 'tcn32')
    sequences, groups, sample_x, sample_y, sample_groups = [], [], [], [], []
    train_people = set(); train_ids = []
    for row, data, _ in refined_rows(source, cfg, 'train', manifest):
        base = velocities(data, cal[row['setup']]); tcn = tcn_predict(data, base)
        side, valid = lateral_labels(data)
        target = np.c_[data['gt_v'] - tcn[:, 0], side, data['gt_yaw'] - tcn[:, 1]]
        valid &= np.isfinite(target).all(axis=1)
        x = planar_features(data, base, tcn, cal).astype(np.float32)
        group = training_group(row)
        sample_x.append(x[valid][::10]); sample_y.append(target[valid][::10])
        sample_groups.extend([group] * len(sample_x[-1]))
        sequences.append((x, np.nan_to_num(target).astype(np.float32), valid, data['imu_valid']))
        groups.append(group); train_people.add(row['participant']); train_ids.append(row['id'])
        if len(sequences) % 50 == 0: print(f'{len(sequences)}/477 refined training feature sequences', flush=True)
    x, y = np.concatenate(sample_x), np.concatenate(sample_y); counts = Counter(sample_groups)
    weights = np.array([1 / counts[g] for g in sample_groups])
    mean = np.average(x, axis=0, weights=weights).astype(np.float32)
    std = np.maximum(np.sqrt(np.average((x - mean) ** 2, axis=0, weights=weights)), 1e-5).astype(np.float32)
    target_mean = np.average(y, axis=0, weights=weights)
    scale = np.maximum(np.sqrt(np.average((y - target_mean) ** 2, axis=0, weights=weights)), .01).astype(np.float32)
    cap = np.maximum(np.quantile(np.abs(y), .995, axis=0), .03).astype(np.float32)
    save_json(out / 'normalization.json', dict(mean=mean.tolist(), std=std.tolist(), target_scale=scale.tolist(),
        residual_cap=cap.tolist(), source='refined training only; normalization and scales equal group weighted; caps pooled training quantile',
        feature_schema='20 physical + signed center acceleration3 + signed center gyro3 + frozen TCN motion2',
        target='forward,lateral,yaw residual over frozenTCN [v,0,w]', training_ids=train_ids,
        training_groups=dict(counts)))
    sequences = [((xx - mean) / std, yy / scale, mask, iv) for xx,yy,mask,iv in sequences]
    dataset = Windows(sequences, groups, warmup=128)
    eligible = [i for i,(sequence,start) in enumerate(dataset.index) if sequences[sequence][2][start+128:start+384].any()]
    dataset.index = [dataset.index[i] for i in eligible]; dataset.group_ids = [dataset.group_ids[i] for i in eligible]
    if not dataset.index: raise RuntimeError('No valid output-core windows')
    window_counts = Counter(dataset.group_ids)
    sampler = WeightedRandomSampler([1 / window_counts[g] for g in dataset.group_ids], len(dataset),
                                    generator=torch.Generator().manual_seed(42))
    loader = DataLoader(dataset, batch_size=64, sampler=sampler)
    validation, validation_trials = [], []
    for row, data, meta in refined_rows(source, cfg, 'validation', manifest):
        if row['participant'] in train_people: raise RuntimeError('Participant leakage')
        base = velocities(data, cal[row['setup']]); tcn = tcn_predict(data, base)
        validation.append((row, data, tcn, (planar_features(data, base, tcn, cal).astype(np.float32) - mean) / std))
        validation_trials.append((row,data,meta))
    frozen_score = neural_score(validation_trials, parent, cal, cfg, out, 'frozen_planar_reference')
    expected = json.loads((source / 'comparison.json').read_text())['candidates']['refined_planar_neural_frozen']
    if abs(frozen_score['equal_participant_mean_position_rmse_m'] - expected['equal_participant_mean_position_rmse_m']) > 1e-9:
        raise RuntimeError('Frozen reference did not reproduce')
    torch.manual_seed(42)
    model = PlanarResNet().to(device); optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
    mean_t, std_t, scale_t = [torch.tensor(a, device=device)[None,:,None] for a in (mean,std,scale)]
    best_value, best_state, history = float('inf'), None, []
    train_seconds, validation_seconds = 0., 0.
    for epoch in range(1, 13):
        epoch_start = time.perf_counter(); model.train(); losses = []
        for xx,yy,mask in loader:
            xx,yy,mask = xx.to(device),yy.to(device),mask.to(device)
            physical = xx * std_t + mean_t
            base_motion = torch.stack([physical[:,26],torch.zeros_like(physical[:,26]),physical[:,27]],dim=1)
            optimizer.zero_grad(); pred = model(xx); loss = planar_loss(pred,yy,base_motion,mask,scale_t)
            if not torch.isfinite(loss): raise RuntimeError('Non-finite loss')
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.); optimizer.step(); losses.append(float(loss.detach()))
        torch.cuda.synchronize(); train_seconds += time.perf_counter() - epoch_start
        evaluation_start = time.perf_counter(); model.eval()
        predictions = {id(data):np.clip(predict_windows(model,xx,device)*scale,-cap,cap) for _,data,_,xx in validation}
        scores = [(gain,evaluate_planar(validation,predictions,cfg,'all_three',gain)[0]) for gain in (.25,.5,1.)]
        gain,score = min(scores,key=lambda pair:pair[1]['equal_participant_mean_position_rmse_m'])
        history.append(dict(epoch=epoch,loss=float(np.mean(losses)),gain_scores=[dict(gain=g,**s) for g,s in scores]))
        if score['equal_participant_mean_position_rmse_m'] < best_value:
            best_value = score['equal_participant_mean_position_rmse_m']
            best_state = dict(state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},gain=gain,epoch=epoch)
            torch.save(best_state,out / 'all_three.pt')
        validation_seconds += time.perf_counter() - evaluation_start
        print(f'epoch {epoch}/12: loss={np.mean(losses):.4f}, gain={gain}, validation={1000*score["equal_participant_mean_position_rmse_m"]:.3f} mm',flush=True)
        save_json(out / 'training_history.json',history)
    model.load_state_dict(best_state['state']); model.eval()
    predictions = {id(data):np.clip(predict_windows(model,xx,device)*scale,-cap,cap) for _,data,_,xx in validation}
    score,records,people,conditions = evaluate_planar(validation,predictions,cfg,'all_three',best_state['gain'])
    for label,rows in [('trials',records),('participants',people),('maneuvers',conditions)]:
        write_csv(out / ('all_three_' + label + '.csv'),rows)
    candidates = dict(frozen_planar=frozen_score,retrained_planar=dict(epoch=best_state['epoch'],gain=best_state['gain'],**score))
    winner = min(candidates,key=lambda name:candidates[name]['equal_participant_mean_position_rmse_m'])
    files = [Path(__file__),source / 'artifact_manifest.json',source / 'run.json',source / 'comparison.json',
             neural_source / 'selection.json',neural_source / 'normalization.json',neural_source / 'all_three.pt',
             out / 'normalization.json',out / 'all_three.pt',out / 'training_history.json']
    files += [ROOT / name for name in ('pipeline.py','learning.py','planar_experiment.py','planar_neural_experiment.py','ronin_experiment.py','synchronization_experiment.py')]
    provenance.update({str(f.relative_to(ROOT)):digest(f) for f in files})
    selection = dict(selected=winner,candidates=candidates,epochs=12,gain_candidates=[.25,.5,1.],history=history,
        training_trials=len(sequences),training_windows=len(dataset),training_groups=dict(window_counts),
        validation_trials=72,validation_participants=4,test_evaluated=False,test_previously_inspected=True,
        settings=cfg,seed=42,determinism='CUDA nondeterministic kernels permitted; training seed reset immediately before model initialization',
        runtime_seconds=time.perf_counter()-started,training_seconds=train_seconds,validation_seconds=validation_seconds,
        peak_vram_bytes=torch.cuda.max_memory_allocated(),gpu=torch.cuda.get_device_name(),torch=torch.__version__,
        provenance=provenance,scope='Only planar residual and its normalization/scales/caps retrained; inherited TCN and physics calibration frozen')
    save_json(out / 'selection.json',selection)
    lines = ['# Refined synchronization: planar retraining v6','','Same architecture, 12 epochs and gains 0.25/0.5/1.0; '
             'forward/lateral/yaw residuals use refined training labels. Feature normalization and residual scales/caps use training only. '
             'Known participants receive equal sampling weight; older unmapped participants are grouped by date. '
             'Inherited TCN and physics calibration remain frozen. The reference candidate is reproduced on the same refined validation recordings.','',
             '| Candidate | Validation RMSE (mm) |','|---|---:|']
    for name,s in candidates.items(): lines.append(f'| {name} | {1000*s["equal_participant_mean_position_rmse_m"]:.3f} |')
    lines += ['',f'Selected: **{winner}**. Best retraining checkpoint: epoch {best_state["epoch"]}, gain {best_state["gain"]}.',
              '', 'Same 72 recordings/four participants. Offline windows use 1.28 s future IMU context. Reference enters initial pose and '
              'offline synchronization, not continuous reconstruction feedback. No test signals opened. Reused validation is exploratory; '
              'one seed does not establish statistical significance. CSV units and independent timing/geometry accuracy remain unresolved.','']
    (out / 'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(selected=winner,candidates=candidates)),flush=True)


if __name__ == '__main__': main()
