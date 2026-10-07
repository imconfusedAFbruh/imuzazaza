"""TRAIN-only continuous braking-hysteresis forward-speed residual.

Exploratory follow-up to the pre-existing braking/travel-deficit hypothesis.
No validation or historical test data are accessed.  Unlike the rejected v34
braking bridge, there is no event gate or validation-chosen threshold: a small
causal feature bank captures wheel deceleration history and center-acceleration
history continuously, and a participant-held ridge predicts only forward-speed
residual.  Yaw is never changed.
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

import json
import time
from collections import Counter

import numpy as np

import pipeline as p
from learning import training_group
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from trajectory_calibration_v10 import integrate


OUT = p.ROOT / "outputs_braking_hysteresis_v56"
TAUS_S = (0.10, 0.25, 0.50, 1.00)
GAINS = (0.0, 0.25, 0.50, 0.75, 1.00)
RIDGE_ALPHA = 1.0


def causal_ema(values, t, valid, tau_s):
    """Causal exponential smoother, reset at each valid run.

    Invalid samples are NaN so callers cannot accidentally bridge gaps.
    """
    x = np.asarray(values, dtype=float)
    tt = np.asarray(t, dtype=float)
    vv = np.asarray(valid, dtype=bool)
    if x.shape[0] != len(tt) or len(vv) != len(tt):
        raise ValueError("time/valid/features length mismatch")
    one_dim = x.ndim == 1
    if one_dim:
        x = x[:, None]
    if x.ndim != 2:
        raise ValueError("values must be 1D or 2D")
    out = np.full_like(x, np.nan, dtype=float)
    for a, b in p.runs(vv):
        if b <= a:
            continue
        out[a] = x[a]
        for i in range(a + 1, b):
            dt = max(float(tt[i] - tt[i - 1]), 0.0)
            alpha = 1.0 - np.exp(-dt / max(float(tau_s), 1e-6))
            out[i] = out[i - 1] + alpha * (x[i] - out[i - 1])
    return out[:, 0] if one_dim else out


def causal_derivative(values, t, valid):
    x = np.asarray(values, dtype=float)
    tt = np.asarray(t, dtype=float)
    vv = np.asarray(valid, dtype=bool)
    out = np.zeros_like(x, dtype=float)
    for a, b in p.runs(vv):
        if b - a <= 1:
            continue
        dt = np.diff(tt[a:b])
        dx = np.diff(x[a:b])
        out[a + 1:b] = np.divide(dx, dt, out=np.zeros_like(dx), where=dt > 0)
        out[a] = 0.0
    out[~vv] = 0.0
    return out


def hysteresis_features(data, calibration):
    """Continuous causal features; no optical signal and no future context."""
    t = np.asarray(data["t"], dtype=float)
    raw = np.asarray(data["raw"], dtype=float)
    valid = np.asarray(data["imu_valid"], dtype=bool)
    terms = calibration["terms"]
    if len(terms) < 3:
        raise ValueError("calibration requires L/R/center gyro terms")

    left = raw[:, terms[0]["column"]] * terms[0]["scale"] + terms[0]["intercept"]
    right = raw[:, terms[1]["column"]] * terms[1]["scale"] + terms[1]["intercept"]
    base = p.velocities(data, calibration)
    speed = base[:, 0]
    yaw = base[:, 1]
    dl = causal_derivative(left, t, valid)
    dr = causal_derivative(right, t, valid)
    dv = causal_derivative(speed, t, valid)
    braking = np.maximum(-dv, 0.0)

    counts = max(float(calibration["accel_counts_per_g"][2]), 1e-6)
    acc = raw[:, 12:15] / counts
    gravity = np.asarray(calibration["center_gravity_direction"], dtype=float)
    gravity = gravity / max(float(np.linalg.norm(gravity)), 1e-8)
    acc_dynamic = acc - gravity[None, :]

    cols = [
        speed,
        yaw,
        left,
        right,
        right - left,
        np.abs(right - left),
        dv,
        dl,
        dr,
        braking,
        *[acc_dynamic[:, j] for j in range(3)],
    ]

    brake_states = {}
    acc_states = {}
    for tau in TAUS_S:
        bstate = causal_ema(braking, t, valid, tau)
        astate = causal_ema(acc_dynamic, t, valid, tau)
        bstate = np.nan_to_num(bstate, nan=0.0)
        astate = np.nan_to_num(astate, nan=0.0)
        brake_states[tau] = bstate
        acc_states[tau] = astate
        cols.append(bstate)
        cols.extend(astate[:, j] for j in range(3))

    slow_acc = acc_states[1.00]
    highpass_acc = acc_dynamic - slow_acc
    cols.extend(highpass_acc[:, j] for j in range(3))
    bmid = brake_states[0.50]
    cols.extend(bmid * acc_dynamic[:, j] for j in range(3))
    cols.append(bmid * np.abs(right - left))
    cols.append(causal_ema(np.abs(right - left), t, valid, 0.50))

    f = np.column_stack(cols).astype(np.float64)
    f[~valid] = 0.0
    if not np.isfinite(f).all():
        raise ValueError("non-finite hysteresis features")
    return f


def prepare_entry(row, data, calibration):
    v = p.velocities(data, calibration)
    motion = np.c_[v[:, 0], np.zeros(len(v)), v[:, 1]]
    label = (
        np.asarray(data["label_valid"], dtype=bool)
        & np.asarray(data["imu_valid"], dtype=bool)
        & np.isfinite(data["gt_v"])
    )
    return dict(
        row=row,
        data=data,
        setup=row["setup"],
        group=training_group(row),
        motion=motion,
        features=hysteresis_features(data, calibration),
        label=label,
        target=np.asarray(data["gt_v"], dtype=float) - v[:, 0],
    )


def fit_models(entries):
    models = {}
    for setup in sorted({e["setup"] for e in entries}):
        es = [e for e in entries if e["setup"] == setup]
        xs, ys, groups = [], [], []
        for e in es:
            idx = np.flatnonzero(e["label"])[::5]
            if not len(idx):
                continue
            xs.append(e["features"][idx])
            ys.append(e["target"][idx])
            groups.extend([e["group"]] * len(idx))
        if not xs:
            raise RuntimeError(f"no fitting labels for setup {setup}")
        x = np.concatenate(xs).astype(float)
        y = np.concatenate(ys).astype(float)
        counts = Counter(groups)
        w = np.asarray([1.0 / counts[g] for g in groups], dtype=float)
        w /= w.sum()
        mean = np.sum(x * w[:, None], axis=0)
        std = np.maximum(np.sqrt(np.sum((x - mean) ** 2 * w[:, None], axis=0)), 1e-6)
        z = np.c_[(x - mean) / std, np.ones(len(x))]
        reg = RIDGE_ALPHA * np.eye(z.shape[1])
        reg[-1, -1] = 0.0
        coef = np.linalg.solve(z.T @ (z * w[:, None]) + reg, z.T @ (y * w))
        cap = max(0.05, float(np.quantile(np.abs(y), 0.995)))
        pred = np.clip(z @ coef, -cap, cap)
        models[setup] = dict(
            mean=mean.tolist(),
            std=std.tolist(),
            coef=coef.tolist(),
            cap_mps=cap,
            fitting_samples=len(x),
            weighted_frame_rmse_mps=float(np.sqrt(np.sum(w * (pred - y) ** 2))),
        )
    return models


def corrected_motion(entry, models, gain):
    motion = np.asarray(entry["motion"], dtype=float).copy()
    if not gain:
        return motion
    model = models[entry["setup"]]
    x = np.asarray(entry["features"], dtype=float)
    z = np.c_[
        (x - np.asarray(model["mean"])) / np.asarray(model["std"]),
        np.ones(len(x)),
    ]
    residual = np.clip(
        z @ np.asarray(model["coef"]),
        -float(model["cap_mps"]),
        float(model["cap_mps"]),
    )
    residual[~np.asarray(entry["data"]["imu_valid"], dtype=bool)] = 0.0
    motion[:, 0] += float(gain) * residual
    return motion


def evaluate(entries, models, gain, cfg, fold):
    rows = []
    for e in entries:
        m = corrected_motion(e, models, gain)
        xy, heading = integrate(e["data"], m)
        rows.append(
            dict(
                fold=fold,
                gain=gain,
                id=e["row"]["id"],
                participant=e["row"]["participant"],
                condition=e["row"]["condition"],
                **p.metrics(e["data"], xy, heading, cfg),
            )
        )
    return rows


def main():
    started = time.perf_counter()
    if OUT.exists():
        raise RuntimeError("Preserve completed output")
    OUT.mkdir()

    protocol = json.loads((p.ROOT / "outputs_clock_arbitrated_v42" / "protocol.json").read_text())
    cfg = protocol["old_clock_settings"]
    fallback = set(protocol["fallback_old_clock_ids"])
    inventory = {
        row["id"]: row
        for row in json.loads((p.ROOT / "outputs_amended_v2" / "inventory.json").read_text())
    }
    target_people = set.union(*FOLDS)
    ids = [
        trial_id
        for trial_id in protocol["training_ids"]
        if inventory[trial_id]["participant"] in target_people
    ]
    if len(ids) != 207:
        raise RuntimeError("target TRAIN membership changed")
    manifests = {
        src: json.loads((src / "artifact_manifest.json").read_text())
        for src in (OLD, NEW)
    }
    trials = []
    for trial_id in ids:
        row = inventory[trial_id]
        if row["partition"] != "train":
            raise RuntimeError("non-TRAIN record")
        src = OLD if trial_id in fallback else NEW
        data, _ = load_cache(src, trial_id, manifests[src])
        trials.append((row, data, {}))

    p.save_json(
        OUT / "protocol.json",
        dict(
            hypothesis="A continuous causal braking-memory state can explain forward-speed/travel residual without the rejected v34 event gate.",
            feature_family="per-fold calibrated L/R speeds and derivatives + center acceleration residual + causal EMA states at 0.10/0.25/0.50/1.00s; no future context",
            taus_s=TAUS_S,
            gains=GAINS,
            ridge_alpha=RIDGE_ALPHA,
            correction="forward speed only; yaw/lateral unchanged; residual clipped to fitting TRAIN 99.5% absolute speed residual",
            folds=[sorted(f) for f in FOLDS],
            selection="minimum equal-participant TRAIN-fold trajectory RMSE subject to frozen <=1.05 worst-person ratio vs same-fold refit physics",
            clock_policy="frozen v42 TRAIN arbitration; no position-based clock selection",
            scope="207 identified target TRAIN recordings only; calibration and residual model refit excluding held participants",
            hypothesis_provenance="braking/travel deficit was a pre-existing TODO before v55; v55 later confirmed it on validation. This v56 run remains exploratory and does not restore independence from prior validation hypothesis generation.",
            validation_accessed=False,
            test_accessed=False,
        ),
    )

    all_rows = []
    fold_models = {}
    for fold_idx, held in enumerate(FOLDS):
        fitting_trials = [q for q in trials if q[0]["participant"] not in held]
        cal = p.calibrate(fitting_trials, cfg)
        entries = [prepare_entry(row, data, cal[row["setup"]]) for row, data, _ in trials]
        fit_entries = [e for e in entries if e["row"]["participant"] not in held]
        held_entries = [e for e in entries if e["row"]["participant"] in held]
        models = fit_models(fit_entries)
        fold_models[str(fold_idx)] = dict(
            calibration=cal,
            models=models,
            fit_ids=[e["row"]["id"] for e in fit_entries],
            held_ids=[e["row"]["id"] for e in held_entries],
        )
        for gain in GAINS:
            all_rows.extend(evaluate(held_entries, models, gain, cfg, fold_idx))
        print("completed v56 fold", fold_idx, flush=True)

    p.write_csv(OUT / "fold_trials.csv", all_rows)
    p.save_json(OUT / "fold_models.json", fold_models)

    summaries = {}
    participants = {}
    maneuvers = {}
    for gain in GAINS:
        rows = [r for r in all_rows if float(r["gain"]) == float(gain)]
        s, pp, mm = p.summarize(rows)
        summaries[str(gain)] = s
        participants[str(gain)] = pp
        maneuvers[str(gain)] = mm
        p.write_csv(OUT / f"gain_{str(gain).replace('.', 'p')}_participants.csv", pp)
        p.write_csv(OUT / f"gain_{str(gain).replace('.', 'p')}_maneuvers.csv", mm)

    baseline_people = {
        q["participant"]: q["mean_trial_position_rmse_m"]
        for q in participants["0.0"]
    }
    candidates = []
    for gain in GAINS:
        pp = participants[str(gain)]
        ratios = {
            q["participant"]: q["mean_trial_position_rmse_m"] / baseline_people[q["participant"]]
            for q in pp
        }
        candidates.append(
            dict(
                gain=gain,
                score_m=summaries[str(gain)]["equal_participant_mean_position_rmse_m"],
                heading_deg=summaries[str(gain)]["equal_participant_mean_heading_rmse_deg"],
                worst_person_ratio=max(ratios.values()),
                participant_ratios=ratios,
            )
        )
    eligible = [c for c in candidates if c["worst_person_ratio"] <= 1.05]
    selected = min(eligible, key=lambda c: c["score_m"])

    # Reproduce the exact v49 refit-physics baseline before interpreting v56.
    v49 = json.loads((p.ROOT / "outputs_simple_refit_folds_v49" / "run.json").read_text())
    expected = v49["summary"]["refit_physics"]["equal_participant_mean_position_rmse_m"]
    if abs(summaries["0.0"]["equal_participant_mean_position_rmse_m"] - expected) > 1e-10:
        raise RuntimeError("v49 physics baseline did not reproduce")

    # Freeze a final all-TRAIN model for future work, but do not validate it here.
    full_cal = p.calibrate(trials, cfg)
    full_entries = [prepare_entry(row, data, full_cal[row["setup"]]) for row, data, _ in trials]
    final_models = fit_models(full_entries)
    p.save_json(
        OUT / "model.json",
        dict(
            selected=selected,
            calibration=full_cal,
            models=final_models,
            training_ids=ids,
            feature_count=int(full_entries[0]["features"].shape[1]),
        ),
    )

    run = dict(
        candidates=candidates,
        selected=selected,
        baseline_reproduced_m=float(expected),
        training_records=207,
        validation_accessed=False,
        test_accessed=False,
        participant_guard_max_ratio=1.05,
        runtime_s=time.perf_counter() - started,
    )
    p.save_json(OUT / "run.json", run)
    p.save_json(
        OUT / "artifact_manifest.json",
        dict(
            sha256={
                str(path.relative_to(OUT)): p.digest(path)
                for path in OUT.rglob("*")
                if path.is_file()
            }
        ),
    )
    print(json.dumps(run, indent=2), flush=True)


if __name__ == "__main__":
    main()
