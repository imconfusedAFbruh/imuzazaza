"""Three-channel offline ResNet: forward, lateral and yaw residuals over frozen TCN."""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler

from pipeline import ROOT, digest, metrics, summarize, velocities, save_json, write_csv
from learning import Windows, training_group, load_predictor
from planar_experiment import cached_rows, verify_parent, lateral_labels, planar_features, integrate_planar
from ronin_experiment import OfflineResNet


class PlanarResNet(OfflineResNet):
    def __init__(self):
        super().__init__()
        self.encoder[0] = nn.Conv1d(28, 32, 7, stride=2, padding=3)
        self.output = nn.Conv1d(96, 3, 1)
        nn.init.zeros_(self.output.weight); nn.init.zeros_(self.output.bias)


def predict_windows(model, x, device):
    if x.ndim != 2 or x.shape[1] != 28 or not len(x) or not np.isfinite(x).all():
        raise ValueError('Expected finite nonempty N by 28 features')
    padded = np.pad(x, ((128, 512), (0, 0))); starts = list(range(0, len(x), 256)); pieces = []
    with torch.no_grad():
        for offset in range(0, len(starts), 64):
            subset = starts[offset:offset + 64]
            batch = np.stack([padded[s:s + 512].T for s in subset])
            result = model(torch.from_numpy(batch).to(device)).cpu().numpy()
            for i, start in enumerate(subset): pieces.append(result[i, :, 128:128 + min(256, len(x) - start)].T)
    return np.concatenate(pieces)


def body_pose(motion):
    middle_motion = (motion[:, :, :-1] + motion[:, :, 1:]) / 2
    angle = F.pad(torch.cumsum(middle_motion[:, 2] * .01, dim=1), (1, 0))
    middle_angle = (angle[:, :-1] + angle[:, 1:]) / 2
    forward, lateral = middle_motion[:, 0], middle_motion[:, 1]
    delta = torch.stack([forward * torch.cos(middle_angle) - lateral * torch.sin(middle_angle),
                         forward * torch.sin(middle_angle) + lateral * torch.cos(middle_angle)], dim=1) * .01
    return F.pad(torch.cumsum(delta, dim=2), (1, 0)), angle


def planar_loss(pred, target, base, mask, scale):
    pred, target, base, mask = pred[:, :, 128:384], target[:, :, 128:384], base[:, :, 128:384], mask[:, 128:384]
    if not mask.any(): raise ValueError('No valid core labels')
    loss = F.smooth_l1_loss(pred.transpose(1, 2)[mask], target.transpose(1, 2)[mask])
    valid = mask.all(dim=1)
    if valid.any():
        position, angle = body_pose(base[valid] + pred[valid] * scale)
        reference, reference_angle = body_pose(base[valid] + target[valid] * scale)
        position_scale = max(float(torch.linalg.vector_norm(scale[0, :2, 0])) * 2.56, .05)
        heading_scale = max(float(scale[0, 2, 0]) * 2.56, .03)
        loss += .2 * F.smooth_l1_loss(position / position_scale, reference / position_scale)
        loss += .1 * F.smooth_l1_loss(angle / heading_scale, reference_angle / heading_scale)
    return loss


def evaluate_planar(validation, predictions, cfg, mode, gain):
    records = []
    for row, data, tcn, _ in validation:
        motion = np.c_[tcn[:, 0], np.zeros(len(tcn)), tcn[:, 1]]
        correction = gain * predictions[id(data)]
        if mode == 'lateral_only': motion[:, 1] += correction[:, 1]
        else: motion += correction
        xy, heading = integrate_planar(data['t'], motion, data['gt_xy'][0], data['gt_heading'][0], data['imu_valid'])
        record = dict(id=row['id'], participant=row['participant'], condition=row['condition'], **metrics(data, xy, heading, cfg))
        if not np.isfinite(record['position_rmse_m']): raise ValueError('Non-finite trial RMSE')
        records.append(record)
    summary, people, conditions = summarize(records)
    if summary['trials'] != 72 or summary['participants'] != 4: raise ValueError('Coverage changed')
    return summary, records, people, conditions


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--epochs', type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.epochs <= 12: parser.error('Epoch budget1 through12')
    out, source = ROOT / 'outputs_planar_neural_v4', ROOT / 'outputs_amended_v2'
    if out.exists(): raise RuntimeError('Preserve existing experiment')
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required')
    verify_parent(source); out.mkdir(); started = time.perf_counter()
    torch.manual_seed(42); np.random.seed(42); torch.set_num_threads(4); device = torch.device('cuda')
    cfg = json.loads((source / 'run.json').read_text())['settings']; cal = json.loads((source / 'calibration.json').read_text())
    tcn_predict = load_predictor(source, 'tcn32')
    sequences, groups, sample_x, sample_y, sample_groups = [], [], [], [], []
    train_people = set()
    for row, data in cached_rows(source, cfg, 'train'):
        base = velocities(data, cal[row['setup']]); tcn = tcn_predict(data, base)
        side, valid = lateral_labels(data)
        target = np.c_[data['gt_v'] - tcn[:, 0], side, data['gt_yaw'] - tcn[:, 1]]
        valid &= np.isfinite(target).all(axis=1)
        x = planar_features(data, base, tcn, cal).astype(np.float32)
        group = training_group(row)
        sample_x.append(x[valid][::10]); sample_y.append(target[valid][::10]); sample_groups.extend([group] * len(sample_x[-1]))
        sequences.append((x, np.nan_to_num(target).astype(np.float32), valid, data['imu_valid'])); groups.append(group)
        train_people.add(row['participant'])
    x, y = np.concatenate(sample_x), np.concatenate(sample_y); counts = Counter(sample_groups)
    weights = np.array([1 / counts[g] for g in sample_groups])
    mean = np.average(x, axis=0, weights=weights).astype(np.float32)
    std = np.maximum(np.sqrt(np.average((x - mean) ** 2, axis=0, weights=weights)), 1e-5).astype(np.float32)
    target_mean = np.average(y, axis=0, weights=weights)
    scale = np.maximum(np.sqrt(np.average((y - target_mean) ** 2, axis=0, weights=weights)), .01).astype(np.float32)
    cap = np.maximum(np.quantile(np.abs(y), .995, axis=0), .03).astype(np.float32)
    norm = dict(mean=mean.tolist(), std=std.tolist(), target_scale=scale.tolist(), residual_cap=cap.tolist(), source='group-balanced training only',
        feature_schema='20 physical + signed center acceleration3 + signed center gyro3 + frozen TCN motion2', target='forward,lateral,yaw residual over frozenTCN [v,0,w]')
    save_json(out / 'normalization.json', norm)
    sequences = [((xx - mean) / std, yy / scale, mask, iv) for xx, yy, mask, iv in sequences]
    dataset = Windows(sequences, groups, warmup=128)
    eligible = [i for i,(sequence,start) in enumerate(dataset.index) if sequences[sequence][2][start+128:start+384].any()]
    dataset.index = [dataset.index[i] for i in eligible]; dataset.group_ids = [dataset.group_ids[i] for i in eligible]
    if not dataset.index: raise ValueError('No valid output-core windows')
    window_counts = Counter(dataset.group_ids)
    sampler = WeightedRandomSampler([1 / window_counts[g] for g in dataset.group_ids], len(dataset), generator=torch.Generator().manual_seed(42))
    loader = DataLoader(dataset, batch_size=64, sampler=sampler)
    validation = []
    for row, data in cached_rows(source, cfg, 'validation'):
        assert row['participant'] not in train_people
        base = velocities(data, cal[row['setup']]); tcn = tcn_predict(data, base)
        validation.append((row, data, tcn, (planar_features(data, base, tcn, cal).astype(np.float32) - mean) / std))
    model = PlanarResNet().to(device); optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
    mean_t, std_t, scale_t = [torch.tensor(a, device=device)[None, :, None] for a in (mean, std, scale)]
    best = {mode:float('inf') for mode in ('lateral_only','all_three')}; states = {}; history = []
    train_seconds, validation_seconds = 0., 0.
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.perf_counter(); model.train(); losses = []
        for xx, yy, mask in loader:
            xx, yy, mask = xx.to(device), yy.to(device), mask.to(device)
            physical = xx * std_t + mean_t
            base_motion = torch.stack([physical[:, 26], torch.zeros_like(physical[:, 26]), physical[:, 27]], dim=1)
            optimizer.zero_grad(); pred = model(xx); loss = planar_loss(pred, yy, base_motion, mask, scale_t)
            if not torch.isfinite(loss): raise ValueError('Non-finite loss')
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step(); losses.append(float(loss.detach()))
        torch.cuda.synchronize(); train_seconds += time.perf_counter() - epoch_start
        validation_start = time.perf_counter(); model.eval()
        predictions = {id(data):np.clip(predict_windows(model, xx, device) * scale, -cap, cap) for _,data,_,xx in validation}
        epoch_scores = {}
        for mode in best:
            scores = [(gain, evaluate_planar(validation, predictions, cfg, mode, gain)[0]) for gain in (.25,.5,1.)]
            gain, score = min(scores, key=lambda p:p[1]['equal_participant_mean_position_rmse_m']); value = score['equal_participant_mean_position_rmse_m']
            epoch_scores[mode] = dict(gain=gain, **score)
            if value < best[mode]:
                best[mode] = value; states[mode] = dict(state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}, gain=gain, epoch=epoch)
        history.append(dict(epoch=epoch, loss=float(np.mean(losses)), candidates=epoch_scores))
        validation_seconds += time.perf_counter() - validation_start
        print(f'PlanarResNet epoch {epoch}/{args.epochs}: loss={np.mean(losses):.4f}, lateral={epoch_scores["lateral_only"]["equal_participant_mean_position_rmse_m"]:.6f}, all3={epoch_scores["all_three"]["equal_participant_mean_position_rmse_m"]:.6f} m', flush=True)
    zero = {id(data):np.zeros((len(data['t']),3)) for _,data,_,_ in validation}
    candidates = {'tcn_reference': evaluate_planar(validation,zero,cfg,'all_three',0.)[0]}
    linear_selection = json.loads((ROOT / 'outputs_planar_v4/selection.json').read_text()); candidates['linear_planar'] = linear_selection['best']
    for mode, state in states.items():
        torch.save(state, out / (mode + '.pt')); model.load_state_dict(state['state']); model.eval()
        predictions = {id(data):np.clip(predict_windows(model, xx, device) * scale,-cap,cap) for _,data,_,xx in validation}
        score, records, people, conditions = evaluate_planar(validation,predictions,cfg,mode,state['gain']); candidates[mode] = dict(epoch=state['epoch'], gain=state['gain'], **score)
        write_csv(out / f'{mode}_trials.csv',records); write_csv(out / f'{mode}_participants.csv',people); write_csv(out / f'{mode}_maneuvers.csv',conditions)
    files = [ROOT / n for n in ('pipeline.py','learning.py','alternatives.py','planar_experiment.py','ronin_experiment.py','planar_neural_experiment.py','test_planar_neural_experiment.py')]
    files += [source / n for n in ('final_test_lock.json','run.json','split.json','inventory.csv','calibration.json','normalization.json','geometry_policy.json','tcn32.pt','qc_train.csv','qc_validation.csv')]
    files += [ROOT / 'outputs_planar_v4/selection.json',out / 'normalization.json',out / 'lateral_only.pt',out / 'all_three.pt']
    selection = dict(selected=min(candidates,key=lambda n:candidates[n]['equal_participant_mean_position_rmse_m']), candidates=candidates, epochs=args.epochs, history=history,
        training_trials=len(sequences),training_windows=len(dataset),training_groups=dict(window_counts), runtime_seconds=time.perf_counter()-started,
        training_seconds=train_seconds,validation_inference_and_metrics_seconds=validation_seconds,peak_allocated_vram_bytes=torch.cuda.max_memory_allocated(),
        dependencies=dict(torch=torch.__version__,numpy=np.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name()),parameters=sum(p.numel() for p in model.parameters()),
        semantics='Offline512frames, central256outputs,128futureIMUframes; initialMoCap pose only; training-only lateral labels never inference input',
        test_evaluated=False,test_previously_inspected=True,seed=42,determinism='CUDA nondeterministic kernels permitted',artifacts={str(p.resolve()):digest(p) for p in files})
    save_json(out / 'selection.json',selection)
    lines = ['# Three-channel planar neural experiment','','ResNet-inspired offline neural residual over frozenTCN. Signed center channels retain directional acceleration and angular velocity; optical lateral labels describe marker-defined body-lateral motion, not confirmed tire skid. Calibration, inheritedTCN, QC and split frozen. New feature normalization, target scales and clipping caps fitted on training only. Fixed12epoch maximum with group-balanced sampling; validation chooses checkpoint and gain(.25/.5/1).','','| Candidate | ValidationRMSE(m) | Trials | Participants |','|---|---:|---:|---:|']
    for name,score in candidates.items(): lines.append(f"| {name} | {score['equal_participant_mean_position_rmse_m']:.6f} | {score['trials']} | {score['participants']} |")
    lines += ['',f"Selected: **{selection['selected']}**. Runtime{selection['runtime_seconds']:.1f}s; CUDAtrain{train_seconds:.1f}s.",'','Offline512sample windows emit central256samples, using128futureIMUsamples. Train/inference contexts match; initial boundary padding is standardizedzero. Integrated loss uses forward/lateral body rotation; reference gaps are masked without interpolation. Same72validation trials/fourparticipants. No test recordings opened. This repeatedly reused validation is exploratory; no blind or millimetre accuracy claim is supported.','', '[RoNIN paper](https://arxiv.org/abs/1905.12853). This adapted dense three-channel network is not a faithful originalRoNIN reproduction.']
    (out / 'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(candidates),flush=True)


if __name__ == '__main__': main()
