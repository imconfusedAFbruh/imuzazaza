"""Authorized three-configuration TRAIN-only shared robust motion residual."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import csv
import json
import time
from collections import Counter
import numpy as np
import pipeline as p
from braking_hysteresis_folds_v56 import hysteresis_features
from learning import training_group
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from projected_yaw_folds_v52 import proxy
from trajectory_calibration_v10 import integrate
from combined_physics_folds_v58 import verified_json
from metric_contract_v74 import metrics as extended_metrics

OUT = p.ROOT / 'outputs_joint_robust_motion_v119'
DELTAS = (1.5, 3., 6.)


def robust_fit(z, y, weights, delta):
    reg = np.eye(z.shape[1]); reg[-1, -1] = 0
    def solve(w):
        w = w / w.sum()
        return np.linalg.solve(z.T @ (z * w[:, None]) + reg,
                               z.T @ (y * w[:, None]))
    coef = solve(weights)
    for _ in range(8):
        norm = np.linalg.norm(z @ coef - y, axis=1)
        shared = np.minimum(1., delta / np.maximum(norm, 1e-12))
        coef = solve(weights * shared)
    assert np.isfinite(coef).all() and shared.shape == (len(z),)
    return coef


def self_check():
    z = np.ones((101, 1)); w = np.ones(101)
    for y in (np.zeros((101, 2)), np.ones((101, 2))):
        assert np.allclose(robust_fit(z, y, w, 1.5), y[:1])
    y = np.zeros((101, 2)); y[-1] = [100, 100]
    coef = robust_fit(z, y, w, 1.5)
    assert np.linalg.norm(coef) < np.linalg.norm(y.mean(0)) * .1
    assert np.allclose(coef[:, 0], coef[:, 1])


def fit(entries, delta):
    result = {}
    for setup in sorted({e['row']['setup'] for e in entries}):
        xs, ys, groups = [], [], []
        for e in entries:
            if e['row']['setup'] != setup: continue
            ix = np.flatnonzero(e['label'])[::5]
            if not len(ix): raise ValueError('No fitting labels: ' + e['row']['id'])
            xs.append(e['features'][ix]); ys.append(e['target'][ix])
            groups.extend([training_group(e['row'])] * len(ix))
        x, y = np.concatenate(xs), np.concatenate(ys)
        counts = Counter(groups)
        w = np.array([1 / counts[g] for g in groups]); w /= w.sum()
        mean = np.sum(x * w[:, None], axis=0)
        std = np.maximum(np.sqrt(np.sum((x-mean)**2*w[:, None], axis=0)), 1e-5)
        scale = np.maximum(1.4826*np.median(np.abs(y-np.median(y, axis=0)), axis=0), .005)
        z = np.c_[(x-mean)/std, np.ones(len(x))]
        coef = robust_fit(z, y/scale, w, delta)
        result[setup] = dict(mean=mean.tolist(), std=std.tolist(), scale=scale.tolist(),
                             coef=coef.tolist(), fitting_samples=len(x))
    return result


def corrected(e, models):
    model = models[e['row']['setup']]
    z = np.c_[(e['features']-model['mean'])/model['std'], np.ones(len(e['features']))]
    correction = np.clip((z @ np.array(model['coef']))*model['scale'], [-.1, -.05], [.1, .05])
    correction[~e['data']['imu_valid']] = 0
    motion = e['motion'].copy(); motion[:, [0, 2]] += .25*correction
    assert np.isfinite(motion).all()
    return motion


def balanced(rows, key):
    return float(np.mean([np.mean([r[key] for r in rows if r['participant']==person])
                          for person in sorted({r['participant'] for r in rows})]))


def main():
    started = time.perf_counter(); self_check()
    if OUT.exists(): raise RuntimeError('Preserve existing output')
    if (p.ROOT/'research_state/STOP').exists(): raise RuntimeError('STOP')
    q = verified_json(p.ROOT/'outputs_clock_arbitrated_v42', 'protocol.json')
    inventory = {r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    people = set.union(*FOLDS)
    ids = [i for i in q['training_ids'] if inventory[i]['participant'] in people]
    assert len(ids)==207 and len(set(ids))==207 and len(people)==12
    assert all(inventory[i]['partition']=='train' for i in ids)
    parent = p.ROOT/'outputs_projected_yaw_v52'
    manifest = json.loads((parent/'artifact_manifest.json').read_text())['sha256']
    assert p.digest(parent/'trials.csv')==manifest['trials.csv']
    saved = {r['id']:r for r in csv.DictReader((parent/'trials.csv').open(newline='')) if float(r['weight'])==1}
    frozen = [verified_json(parent, f'fold_{i}_models.json') for i in range(3)]
    OUT.mkdir(); (OUT/'predictions').mkdir()
    sources = [__file__, 'braking_hysteresis_folds_v56.py', 'projected_yaw_folds_v52.py',
               'pipeline.py', 'trajectory_calibration_v10.py', 'metric_contract_v74.py',
               'research_docs/joint_robust_motion_v119.md']
    p.save_json(OUT/'protocol.json', dict(deltas=DELTAS, gain=.25, caps=[.1,.05],
        ridge_alpha=1, iterations=8, label_stride=5, training_ids=ids,
        validation_accessed=False, test_accessed=False, promotion_allowed=False,
        source_hashes={str(s):p.digest(p.ROOT/s) for s in sources},
        normalization='group-weighted feature mean/std floor1e-5; unweighted centered target MAD*1.4826 floor.005, fixed across IRLS',
        inherited_caveats='offline projected gravity proxy; frozen optical crop/initial pose/clocks; no true acquisition endpoint claim'))
    manifests = {s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD, NEW)}
    trials = []
    for id in ids:
        src = OLD if id in q['fallback_old_clock_ids'] else NEW
        d, _ = load_cache(src, id, manifests[src]); trials.append((inventory[id], d))
    records = []; baseline_verified = []
    # Reproduce ALL historical baseline scores before any candidate scoring.
    for i, held in enumerate(FOLDS):
        model = frozen[i]
        assert set(model['fitting_ids']) == {r['id'] for r,d in trials if r['participant'] not in held}
        for row, d in trials:
            if row['participant'] not in held: continue
            cal = model['calibration'][row['setup']]; yaw = model['yaw'][row['setup']]
            v = p.velocities(d, cal)
            motion = np.c_[v[:,0], np.zeros(len(v)), proxy(d,cal)*yaw['scale']+yaw['intercept']]
            xy, h = integrate(d, motion); score = p.metrics(d,xy,h,q['old_clock_settings'])
            old = saved[row['id']]
            assert score['scored_frames']==int(old['scored_frames'])
            for key in ('position_rmse_m','heading_rmse_deg'):
                assert np.isclose(score[key],float(old[key]),rtol=1e-10,atol=1e-12)
            baseline_verified.append(dict(id=row['id'], **score))
    assert len(baseline_verified)==207
    p.save_json(OUT/'baseline_verified.json', baseline_verified)
    print('All207 v52 baselines reproduced before candidate scoring', flush=True)
    for i, held in enumerate(FOLDS):
        if (p.ROOT/'research_state/STOP').exists(): raise RuntimeError('STOP')
        entries = []; model = frozen[i]
        for row, d in trials:
            cal = model['calibration'][row['setup']]; yaw = model['yaw'][row['setup']]
            v = p.velocities(d,cal)
            motion = np.c_[v[:,0],np.zeros(len(v)),proxy(d,cal)*yaw['scale']+yaw['intercept']]
            label = d['label_valid'] & d['imu_valid'] & np.isfinite(d['gt_v']) & np.isfinite(d['gt_yaw'])
            entries.append(dict(row=row, data=d, motion=motion, label=label,
                target=np.c_[d['gt_v'],d['gt_yaw']]-motion[:,[0,2]], features=hysteresis_features(d,cal)))
        fitting = [e for e in entries if e['row']['participant'] not in held]
        models = {delta:fit(fitting,delta) for delta in DELTAS}
        p.save_json(OUT/f'fold_{i}_models.json', dict(fitting_ids=[e['row']['id'] for e in fitting], held_people=sorted(held),models=models))
        for e in entries:
            row, d = e['row'],e['data']
            if row['participant'] not in held: continue
            arrays = dict(t=d['t'], gt_xy=d['gt_xy'],gt_heading=d['gt_heading'],gt_valid=d['gt_valid'],imu_valid=d['imu_valid'])
            support = None
            for delta in (0., *DELTAS):
                motion = e['motion'] if delta==0 else corrected(e,models[delta])
                xy,h = integrate(d,motion); mask = d['gt_valid'] & np.isfinite(xy).all(1)
                if support is None: support = mask
                assert np.array_equal(support,mask)
                score = p.metrics(d,xy,h,q['old_clock_settings'])
                extra = extended_metrics(d,xy,h,motion)
                assert score['scored_frames']==extra['Valid_Frame_Count']
                lm=e['label']; assert lm.any()
                records.append(dict(id=row['id'],participant=row['participant'],condition=row['condition'],fold=i,delta=delta,
                    **score, **extra, label_speed_rmse_mps=float(np.sqrt(np.mean((motion[lm,0]-d['gt_v'][lm])**2))),
                    label_yaw_rmse_radps=float(np.sqrt(np.mean((motion[lm,2]-d['gt_yaw'][lm])**2)))))
                prefix=f'delta_{delta:g}_'; arrays.update({prefix+'motion':motion,prefix+'xy':xy,prefix+'heading':h})
            np.savez_compressed(OUT/'predictions'/(row['id']+'.npz'),**arrays)
        p.write_csv(OUT/'trials.csv', records)
        p.save_json(OUT/'checkpoint.json',dict(completed_folds=i+1,rows=len(records),status='running'))
        print(f'Fold{i} complete: {len(records)} scored rows saved',flush=True)
    base=[r for r in records if r['delta']==0]
    bs,bp,bm=p.summarize(base)
    assert np.isclose(bs['equal_participant_mean_position_rmse_m']*1000,147.74650809690637)
    candidates=[]
    for delta in (0.,*DELTAS):
        rows=[r for r in records if r['delta']==delta]; assert len(rows)==207
        s,pp,mm=p.summarize(rows)
        pr={r['participant']:r['mean_trial_position_rmse_m']/next(b['mean_trial_position_rmse_m'] for b in bp if b['participant']==r['participant']) for r in pp}
        mr={r['condition']:r['equal_participant_mean_position_rmse_m']/next(b['equal_participant_mean_position_rmse_m'] for b in bm if b['condition']==r['condition']) for r in mm}
        guards={key:balanced(rows,key)/balanced(base,key) for key in ('Position_P95_mm','Last_Supported_Endpoint_Error_mm','heading_rmse_deg')}
        eligible=delta==0 or (s['equal_participant_mean_position_rmse_m']<bs['equal_participant_mean_position_rmse_m'] and max(pr.values())<=1.05 and max(mr.values())<=1.05 and max(guards.values())<=1.05)
        candidates.append(dict(delta=delta,eligible=eligible,**s,participant_ratios=pr,maneuver_ratios=mr,guard_ratios=guards))
        p.write_csv(OUT/f'delta_{delta:g}_participants.csv',pp);p.write_csv(OUT/f'delta_{delta:g}_maneuvers.csv',mm)
    selected=min((c for c in candidates if c['eligible']),key=lambda c:c['equal_participant_mean_position_rmse_m'])
    p.save_json(OUT/'run.json',dict(candidates=candidates,selected=selected,validation_accessed=False,test_accessed=False,runtime_s=time.perf_counter()-started))
    p.save_json(OUT/'checkpoint.json',dict(completed_folds=3,rows=len(records),status='complete'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps(candidates,indent=2),flush=True)


if __name__=='__main__': main()
