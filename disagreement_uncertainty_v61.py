"""TRAIN-only nested-OOF wheel/body disagreement uncertainty diagnostic."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import json, time
from collections import Counter
import numpy as np
from scipy.stats import spearmanr
import pipeline as p
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from braking_hysteresis_folds_v56 import causal_derivative, causal_ema

OUT = p.ROOT / 'outputs_disagreement_uncertainty_v61'
BLOCK = 20
EPS = 1e-6


def ridge(x, y, people):
    counts = Counter(people)
    w = np.array([1/counts[q] for q in people], float); w /= w.sum()
    mean = np.sum(x*w[:, None], axis=0)
    std = np.maximum(np.sqrt(np.sum((x-mean)**2*w[:, None], axis=0)), 1e-6)
    z = np.c_[(x-mean)/std, np.ones(len(x))]
    reg = np.eye(z.shape[1]); reg[-1, -1] = 0
    coef = np.linalg.solve(z.T@(w[:, None]*z)+reg, z.T@(w*y))
    return dict(mean=mean.tolist(), std=std.tolist(), coef=coef.tolist())


def predict(model, x):
    return np.c_[(x-model['mean'])/model['std'], np.ones(len(x))]@model['coef']


def center(data, cal):
    return data['raw'][:, 12:15]/cal['accel_counts_per_g'][2] - np.asarray(cal['center_gravity_direction'])[None]


def blocks(data):
    mask = data['label_valid'] & data['imu_valid'] & np.isfinite(data['gt_v'])
    return [(i, i+BLOCK) for lo, hi in p.runs(mask) for i in range(lo, hi-BLOCK, BLOCK)]


def fit_acceleration(trials, calibration):
    models = {}
    for setup in calibration:
        x, y, people = [], [], []
        for row, data in trials:
            if row['setup'] != setup: continue
            a = center(data, calibration[setup]); t = data['t']
            for lo, hi in blocks(data):
                dt = t[hi]-t[lo]
                x.append(np.mean(a[lo:hi+1], axis=0))
                y.append((data['gt_v'][hi]-data['gt_v'][lo])/dt)
                people.append(row['participant'])
        models[setup] = ridge(np.asarray(x), np.asarray(y), people)
    return models


def diagnostic_blocks(row, data, calibration, accel_model):
    # Features depend only on IMU; truth is used below only for diagnostic target.
    cal = calibration[row['setup']]; valid = data['imu_valid']; t = data['t']
    speed = p.velocities(data, cal)[:, 0]
    aw = causal_ema(causal_derivative(speed, t, valid), t, valid, .05)
    ac = predict(accel_model[row['setup']], center(data, cal))
    ac = causal_ema(ac, t, valid, .05)
    jc = causal_derivative(ac, t, valid)
    records = []
    # Feature construction runs on full IMU support before consulting label masks.
    feature_by_start = {}
    for lo, hi in p.runs(valid):
        bias = 0.0
        for a in range(lo, hi-BLOCK, BLOCK):
            b = a+BLOCK; dt = t[b]-t[a]
            dc = float(np.trapezoid(ac[a:b+1], t[a:b+1]))
            u = speed[b]-speed[a]-dc
            timing = (abs(aw[a])+abs(aw[b])+float(np.trapezoid(abs(jc[a:b+1]), t[a:b+1])))/104
            raw = abs(u); centered = abs(u-bias); excess = max(centered-timing, 0.)
            feature_by_start[a] = [float(np.mean(abs(speed[a:b+1]))), float(np.mean(np.maximum(-aw[a:b+1], 0))), raw, centered, excess]
            bias += (1-np.exp(-dt/2))* (u-bias)
    mask = data['label_valid'] & valid & np.isfinite(data['gt_v'])
    for a, feature in feature_by_start.items():
        b = a+BLOCK
        if not mask[a:b+1].all(): continue
        err = speed[a:b+1]-data['gt_v'][a:b+1]
        truth_acc = (data['gt_v'][b]-data['gt_v'][a])/(t[b]-t[a])
        est_acc = float(np.trapezoid(ac[a:b+1], t[a:b+1]))/(t[b]-t[a])
        records.append(dict(id=row['id'], participant=row['participant'], condition=row['condition'], start_s=float(t[a]), features=feature, squared_error=float(np.mean(err**2)), accel_error_squared=float((est_acc-truth_acc)**2), zero_accel_error_squared=float(truth_acc**2)))
    return records


def fit_variance(records, columns):
    x = np.array([r['features'] for r in records])[:, columns]
    y = np.array([r['squared_error'] for r in records]); people = [r['participant'] for r in records]
    model = ridge(x, np.log(y+EPS), people)
    counts = Counter(people); w = np.array([1/counts[q] for q in people]); w /= w.sum()
    unscaled = np.exp(np.clip(predict(model, x), -20, 10))
    model['variance_scale'] = float(np.sum(w*y/unscaled))
    model['columns'] = columns
    return model


def evaluate(records, model, method, fold):
    x = np.array([r['features'] for r in records])[:, model['columns']]
    variance = np.maximum(EPS, model['variance_scale']*np.exp(np.clip(predict(model, x), -20, 10)))
    return [dict(**{k:v for k,v in r.items() if k!='features'}, fold=fold, method=method, variance=float(v), nll=float(.5*(np.log(v)+r['squared_error']/v)), variance_mae=float(abs(v-r['squared_error']))) for r,v in zip(records, variance)]


def aggregate(rows, key):
    result = []
    for value in sorted({r[key] for r in rows}):
        q = [r for r in rows if r[key]==value]
        corr = spearmanr([r['variance'] for r in q], [r['squared_error'] for r in q]).statistic
        result.append(dict(group=value, blocks=len(q), nll=float(np.mean([r['nll'] for r in q])), variance_mae=float(np.mean([r['variance_mae'] for r in q])), spearman=float(corr) if np.isfinite(corr) else 0., accel_mse=float(np.mean([r['accel_error_squared'] for r in q])), zero_accel_mse=float(np.mean([r['zero_accel_error_squared'] for r in q]))))
    return result


def main():
    started = time.perf_counter()
    if OUT.exists(): raise RuntimeError('Preserve immutable artifact')
    OUT.mkdir()
    protocol = json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())
    frozen = json.loads((p.ROOT/'outputs_braking_hysteresis_v56/fold_models.json').read_text())
    inventory = {r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    people = set.union(*FOLDS); fallback = set(protocol['fallback_old_clock_ids'])
    ids = [i for i in protocol['training_ids'] if inventory[i]['participant'] in people]
    assert len(ids)==207
    manifests = {src:json.loads((src/'artifact_manifest.json').read_text()) for src in (OLD, NEW)}
    trials = []
    for i in ids:
        row = inventory[i]; assert row['partition']=='train'
        src = OLD if i in fallback else NEW; data,_ = load_cache(src,i,manifests[src]); trials.append((row,data))
    p.save_json(OUT/'protocol.json', dict(hypothesis='Timing-excess wheel/body acceleration increment disagreement predicts held-participant speed-error variance beyond speed/braking.', training_ids=ids, block_samples=BLOCK, block_nominal_s=.2, accel_smoothing_tau_s=.05, bias_tau_s=2., age_envelope_s=1/104, ridge_alpha=1., folds=[sorted(q) for q in FOLDS], uncertainty_fit='Inner participant OOF baseline/accel errors; each inner calibration and center model excludes its held participants.', controls='speed magnitude + braking magnitude', candidates=['raw','bias_centered','timing_excess'], validation_accessed=False,test_accessed=False,reference_input_at_inference=False,scope='207 known target TRAIN; frozen clock/QC/reference preparation remains inherited. Diagnostic only, no trajectory correction.'))
    rows = []; models = {}
    for fold, held in enumerate(FOLDS):
        fitting = [q for q in trials if q[0]['participant'] not in held]
        testing = [q for q in trials if q[0]['participant'] in held]
        assert set(q[0]['id'] for q in fitting)==set(frozen[str(fold)]['fit_ids'])
        outer_cal = frozen[str(fold)]['calibration']
        accel = fit_acceleration(fitting, outer_cal)
        inner_records = []
        for inner_held in FOLDS:
            inner_test = [q for q in fitting if q[0]['participant'] in inner_held]
            if not inner_test: continue
            inner_fit = [q for q in fitting if q[0]['participant'] not in inner_held]
            cal = p.calibrate([(r,d,{}) for r,d in inner_fit], protocol['old_clock_settings'])
            am = fit_acceleration(inner_fit, cal)
            for r,d in inner_test: inner_records.extend(diagnostic_blocks(r,d,cal,am))
        held_records = []
        for r,d in testing: held_records.extend(diagnostic_blocks(r,d,outer_cal,accel))
        models[str(fold)] = dict(acceleration=accel, fitting_ids=[q[0]['id'] for q in fitting],held_ids=[q[0]['id'] for q in testing], uncertainty={})
        for name, cols in [('control',[0,1]),('raw',[0,1,2]),('bias_centered',[0,1,3]),('timing_excess',[0,1,4])]:
            model = fit_variance(inner_records, cols); models[str(fold)]['uncertainty'][name] = model
            rows.extend(evaluate(held_records,model,name,fold))
        print('completed v61 fold',fold,'held blocks',len(held_records),flush=True)
    p.write_csv(OUT/'held_blocks.csv',rows); p.save_json(OUT/'fold_models.json',models)
    summaries = {}; participant_tables = {}
    for name in ('control','raw','bias_centered','timing_excess'):
        selected = [r for r in rows if r['method']==name]
        pp = aggregate(selected,'participant'); mm=aggregate(selected,'condition'); participant_tables[name]={q['group']:q for q in pp}
        p.write_csv(OUT/f'{name}_participants.csv',pp); p.write_csv(OUT/f'{name}_maneuvers.csv',mm)
        summaries[name] = {k:float(np.mean([q[k] for q in pp])) for k in ('nll','variance_mae','spearman','accel_mse','zero_accel_mse')}
    comparisons = []
    for name in ('raw','bias_centered','timing_excess'):
        for person,q in participant_tables[name].items():
            base=participant_tables['control'][person]
            comparisons.append(dict(method=name,participant=person,nll_delta=q['nll']-base['nll'],spearman_delta=q['spearman']-base['spearman'],mae_ratio=q['variance_mae']/base['variance_mae'],pass_nll=q['nll']<base['nll'],pass_mae_guard=q['variance_mae']<=1.05*base['variance_mae']))
    p.write_csv(OUT/'participant_pass_fail.csv',comparisons)
    c=summaries['control']; t=summaries['timing_excess']; worst=max(q['mae_ratio'] for q in comparisons if q['method']=='timing_excess')
    passes=t['nll']<c['nll'] and t['spearman']>c['spearman'] and worst<=1.05 and t['accel_mse']<t['zero_accel_mse']
    run=dict(summary=summaries,diagnostic_pass=bool(passes),timing_excess_worst_participant_mae_ratio=worst,conclusion='Candidate mechanism warrants separate nested observer experiment' if passes else 'Reject diagnostic; do not build smoother from this confidence model',training_records=len(ids),validation_accessed=False,test_accessed=False,trajectory_changed=False,runtime_s=time.perf_counter()-started)
    p.save_json(OUT/'run.json',run)
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps(run,indent=2),flush=True)


if __name__=='__main__': main()
