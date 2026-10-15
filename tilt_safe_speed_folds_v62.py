"""TRAIN-only tilt-invariant feature ablation for bounded speed residual."""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
import json
import time
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfiltfilt
import pipeline as p
import braking_hysteresis_folds_v56 as travel
from projected_yaw_folds_v52 import proxy
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from trajectory_calibration_v10 import integrate
from combined_physics_folds_v58 import verified_json
from research_metrics_v59 import trajectory_metrics, aggregate

OUT = p.ROOT / "outputs_tilt_safe_speed_v62"
GAINS = (0., .25, .5)
VARIANTS = ("no_center_accel", "dynamic_gravity")
KEEP = list(range(10)) + [13, 17, 21, 25, 35, 36]


def features(data, cal, variant):
    if variant == "no_center_accel":
        return travel.hysteresis_features(data, cal)[:, KEEP]
    raw = data["raw"].copy()
    counts = float(cal["accel_counts_per_g"][2])
    fixed = np.asarray(cal["center_gravity_direction"])
    fixed = fixed / max(float(np.linalg.norm(fixed)), 1e-8)
    direction = np.repeat(fixed[None], len(raw), axis=0)
    for lo, hi in p.runs(data["imu_valid"]):
        if hi-lo > 30:
            low = sosfiltfilt(butter(2, .3, fs=100, output="sos"), raw[lo:hi, 12:15], axis=0)
            direction[lo:hi] = low / np.maximum(np.linalg.norm(low, axis=1, keepdims=True), 1e-8)
    # Reuse v56's full feature bank with dynamic rather than fixed gravity.
    raw[:, 12:15] -= (direction-fixed[None]) * counts
    return travel.hysteresis_features({**data, "raw": raw}, cal)


def main():
    started = time.perf_counter()
    if OUT.exists(): raise RuntimeError("Preserve existing output")
    OUT.mkdir(); (OUT / "trajectories").mkdir()
    protocol = json.loads((p.ROOT / "outputs_clock_arbitrated_v42/protocol.json").read_text())
    cfg = protocol["old_clock_settings"]
    inventory = {r["id"]: r for r in json.loads((p.ROOT / "outputs_amended_v2/inventory.json").read_text())}
    people = set.union(*FOLDS)
    ids = [i for i in protocol["training_ids"] if inventory[i]["participant"] in people]
    assert len(ids) == 207 and all(inventory[i]["partition"] == "train" for i in ids)
    fallback = set(protocol["fallback_old_clock_ids"])
    manifests = {s: json.loads((s / "artifact_manifest.json").read_text()) for s in (OLD, NEW)}
    trials = []
    for trial_id in ids:
        source = OLD if trial_id in fallback else NEW
        data, _ = load_cache(source, trial_id, manifests[source])
        trials.append((inventory[trial_id], data))
    sealed = verified_json(travel.OUT, "fold_models.json")
    yawdir = p.ROOT / "outputs_projected_yaw_v52"
    p.save_json(OUT / "protocol.json", dict(
        hypothesis="Fixed gravity subtraction contaminates speed residuals on slopes; acceleration-free or dynamic gravity features may retain useful travel correction without ST regression.",
        variants=VARIANTS, gains=GAINS, no_accel_feature_indices=KEEP,
        dynamic_gravity_cutoff_hz=.3, filter_order=2, ridge_alpha=1., residual_cap="fitting TRAIN absolute residual99.5% with minimum.05m/s",
        selection="minimum equal-person XY RMSE, both worst-person and worst-maneuver ratio<=1.05 vs frozen projectedyaw",
        fitting="same207targetTRAIN folds and sealedcalibration; normalize/fit/cap using fitting persons only; no maneuver labels in prediction",
        timing="inherited frozen v42device-time based clocks; no clock tuning", training_ids=ids,
        reference="C3D used for fitting labels/evaluation/authorizedinitialpose only; no subsequentreferenceinput/reset/transform",
        caveats="dynamicgravity uses futureIMU offline; acceleration directionproxy remains unverified attitude; inherited clocks/QC and historicalvalidationexposure make results conditionalexploratory",
        script_sha256=p.digest(Path(__file__)), validation_accessed=False, test_accessed=False))
    rows, fold_models = [], {}
    for fold, held in enumerate(FOLDS):
        parent = sealed[str(fold)]
        yaw = verified_json(yawdir, f"fold_{fold}_models.json")
        assert parent["calibration"] == yaw["calibration"] and set(parent["fit_ids"]) == set(yaw["fitting_ids"])
        entries = {variant: [] for variant in VARIANTS}
        for row, data in trials:
            cal = parent["calibration"][row["setup"]]
            base = travel.prepare_entry(row, data, cal)
            for variant in VARIANTS:
                entries[variant].append({**base, "features": features(data, cal, variant)})
        models = {variant: travel.fit_models([e for e in entries[variant] if e["row"]["participant"] not in held]) for variant in VARIANTS}
        fold_models[str(fold)] = dict(calibration=parent["calibration"], yaw=yaw["yaw"], models=models, fit_ids=parent["fit_ids"], held_ids=parent["held_ids"])
        for idx, (row, data) in enumerate(trials):
            if row["participant"] not in held: continue
            cal = parent["calibration"][row["setup"]]
            ymodel = yaw["yaw"][row["setup"]]
            predicted_yaw = proxy(data, cal) * ymodel["scale"] + ymodel["intercept"]
            exports = {}
            for variant in VARIANTS:
                for gain in GAINS:
                    if gain == 0 and variant != VARIANTS[0]: continue
                    motion = travel.corrected_motion(entries[variant][idx], models[variant], gain)
                    motion[:, 2] = predicted_yaw
                    xy, heading = integrate(data, motion)
                    key = "control" if gain == 0 else f"{variant}_{gain:g}"
                    rows.append({"id":row["id"], "participant":row["participant"], "condition":row["condition"], "fold":fold, "variant":variant, "gain":gain, "candidate":key,
                                 **p.metrics(data, xy, heading, cfg), **trajectory_metrics(data, xy, heading)})
                    exports[key + "_xy"] = xy; exports[key + "_heading"] = heading
            np.savez_compressed(OUT / "trajectories" / (row["id"]+".npz"), t=data["t"], reference_xy=data["gt_xy"], reference_heading=data["gt_heading"], reference_valid=data["gt_valid"], **exports)
            print(len(rows)//5, row["id"], flush=True)
    p.write_csv(OUT / "trials.csv", rows); p.save_json(OUT / "fold_models.json", fold_models)
    summaries = aggregate(rows, ("candidate",)); people = aggregate(rows, ("candidate", "participant")); maneuvers = aggregate(rows, ("candidate", "condition"))
    p.write_csv(OUT / "summary.csv", summaries); p.write_csv(OUT / "participants.csv", people); p.write_csv(OUT / "maneuvers.csv", maneuvers)
    expected = verified_json(yawdir, "run.json")["selected"]["score"]
    assert abs(next(s["position_rmse_m"] for s in summaries if s["candidate"] == "control") - expected) < 1e-10
    candidates = []
    for summary in summaries:
        key = summary["candidate"]
        def ratios(items, group):
            base = {r[group]: r["position_rmse_m"] for r in items if r["candidate"] == "control"}
            return {r[group]: r["position_rmse_m"]/base[r[group]] for r in items if r["candidate"] == key}
        pr, mr = ratios(people, "participant"), ratios(maneuvers, "condition")
        candidates.append(dict(candidate=key, summary=summary, participant_ratios=pr, maneuver_ratios=mr, worst_participant_ratio=max(pr.values()), worst_maneuver_ratio=max(mr.values())))
    selected = min([c for c in candidates if c["worst_participant_ratio"]<=1.05 and c["worst_maneuver_ratio"]<=1.05], key=lambda c:c["summary"]["position_rmse_m"])
    p.save_json(OUT / "run.json", dict(candidates=candidates, selected=selected, validation_accessed=False, test_accessed=False, baseline_reproduced_m=expected, runtime_s=time.perf_counter()-started))
    p.save_json(OUT / "artifact_manifest.json", dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob("*") if f.is_file()}))
    print(json.dumps(selected, indent=2), flush=True)


def plot_diagnostics():
    import csv
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    records = list(csv.DictReader((OUT / "trials.csv").open()))
    result = json.loads((OUT / "run.json").read_text())
    baseline = {r["id"]:float(r["position_rmse_m"]) for r in records if r["candidate"] == "control"}
    candidates = [c["candidate"] for c in result["candidates"] if c["candidate"] != "control"]
    folder = OUT / "figures"; folder.mkdir(exist_ok=True)
    viewed = []
    for candidate in candidates:
        rows = [r for r in records if r["candidate"] == candidate]
        ordered = sorted(rows, key=lambda r:float(r["position_rmse_m"])-baseline[r["id"]])
        worst_st = max((r for r in rows if r["condition"] == "ST"), key=lambda r:float(r["position_rmse_m"])-baseline[r["id"]])
        chosen = {r["id"]:r for r in (ordered[0], ordered[-1], worst_st)}
        for trial_id, row in chosen.items():
            with np.load(OUT / "trajectories" / (trial_id+".npz")) as z:
                t, ref, hr, valid = z["t"], z["reference_xy"].copy(), z["reference_heading"].copy(), z["reference_valid"]
                fig, axes = plt.subplots(1,2,figsize=(10,4)); origin=ref[0]; ref[~valid]=np.nan
                axes[0].plot(*(ref-origin).T, color="black", label="C3D")
                def wrapped(h, mask):
                    a=np.arctan2(np.sin(h-hr[0]),np.cos(h-hr[0])); a[~mask | np.r_[False,np.abs(np.diff(a))>np.pi]]=np.nan
                    return np.rad2deg(a)
                axes[1].plot(t,wrapped(hr.copy(),valid),color="black",label="C3D")
                for key,color,label in (("control","#999","Projected-yaw control"),(candidate,"red","IMU "+candidate)):
                    xy,h=z[key+"_xy"],z[key+"_heading"]
                    axes[0].plot(*(xy-origin).T,color=color,label=label,lw=1)
                    axes[1].plot(t,wrapped(h.copy(),np.isfinite(h)),color=color,label=label,lw=1)
                axes[0].set_aspect("equal",adjustable="datalim");axes[0].set(xlabel="X (m)",ylabel="Y (m)")
                axes[1].set(xlabel="Time (s)",ylabel="Wrapped yaw from initial pose (degrees)")
                for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=7)
                fig.suptitle(trial_id+f" | {baseline[trial_id]*1000:.1f} -> {float(row['position_rmse_m'])*1000:.1f} mm",fontsize=9)
                fig.tight_layout();path=folder/(candidate+"__"+trial_id+".png");fig.savefig(path,dpi=120);plt.close(fig)
                viewed.append(str(path.relative_to(OUT)))
    result["diagnostic_figures"] = viewed
    result["plot_script_sha256"] = p.digest(Path(__file__))
    p.save_json(OUT / "run.json", result)
    p.save_json(OUT / "artifact_manifest.json", dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob("*") if f.is_file() and f.name!="artifact_manifest.json"}))


if __name__ == "__main__":
    import sys
    plot_diagnostics() if "--plots" in sys.argv else main()
