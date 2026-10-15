"""TRAIN-only frozen projected yaw plus bounded hysteresis forward residual."""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
import json
import time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pipeline as p
import braking_hysteresis_folds_v56 as travel
from projected_yaw_folds_v52 import proxy
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from trajectory_calibration_v10 import integrate
from route_metrics_audit_v36 import pieces, route, length, restricted_ordered

OUT = p.ROOT / "outputs_combined_physics_v58"
GAINS = (0.0, 0.25, 0.5)
GUARD = 1.05
EXTRA = ("route_rmse_m", "route_p95_m", "sampled_hausdorff_m",
         "supported_run_frechet_max_m", "supported_run_arc_correspondence_rmse_m",
         "supported_last_endpoint_error_m", "supported_pathlength_absolute_error_m")


def verified_json(folder, name):
    manifest = json.loads((folder / "artifact_manifest.json").read_text())["sha256"]
    path = folder / name
    if p.digest(path) != manifest[name]:
        raise RuntimeError(f"changed frozen artifact: {path}")
    return json.loads(path.read_text())


def extra_metrics(data, xy):
    valid = data["gt_valid"] & np.isfinite(xy).all(axis=1)
    ref, pred = pieces(data["gt_xy"], valid), pieces(xy, valid)
    result = route(ref, pred, .01)
    coarse = route(ref, pred, .02)
    result.update(restricted_ordered(ref, pred))
    result.update(supported_last_endpoint_error_m=float(np.linalg.norm(xy[valid][-1] - data["gt_xy"][valid][-1])),
                  supported_pathlength_absolute_error_m=abs(sum(map(length, pred)) - sum(map(length, ref))),
                  route_rmse_refinement_abs_m=abs(result["route_rmse_m"] - coarse["route_rmse_m"]))
    return result


def aggregate_extra(rows):
    people = sorted({r["participant"] for r in rows})
    return {m: float(np.mean([np.mean([r[m] for r in rows if r["participant"] == person]) for person in people])) for m in EXTRA}


def plot(data, predictions, row):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    ref = data["gt_xy"].copy(); ref[~data["gt_valid"]] = np.nan
    origin = data["gt_xy"][0]
    axes[0].plot(*(ref - origin).T, color="black", label="C3D")
    def wrapped_heading(h, valid):
        angle = np.arctan2(np.sin(h-data["gt_heading"][0]), np.cos(h-data["gt_heading"][0]))
        jumps = np.r_[False, np.abs(np.diff(angle)) > np.pi]
        angle[~valid | jumps] = np.nan
        return np.rad2deg(angle)
    hr = wrapped_heading(data["gt_heading"].copy(), data["gt_valid"])
    axes[1].plot(data["t"], hr, color="black", label="C3D")
    for gain, (xy, heading) in predictions.items():
        color = "red" if gain == .25 else ("#e69f00" if gain == .5 else "#aaa")
        label = f"IMU gain {gain:g}"
        axes[0].plot(*(xy - origin).T, color=color, lw=1, label=label)
        axes[1].plot(data["t"], wrapped_heading(heading.copy(), np.isfinite(heading)), color=color, lw=1, label=label)
    axes[0].set_aspect("equal", adjustable="datalim")
    axes[0].set(xlabel="X from initial position (m)", ylabel="Y (m)")
    axes[1].set(xlabel="Time (s)", ylabel="Wrapped yaw from initial pose (degrees)")
    for ax in axes:
        ax.grid(alpha=.2); ax.legend(fontsize=7)
    fig.suptitle(row["id"], fontsize=9); fig.tight_layout()
    fig.savefig(OUT / "figures" / (row["id"] + ".png"), dpi=120)
    plt.close(fig)


def main():
    start = time.perf_counter()
    if OUT.exists(): raise RuntimeError("Preserve output; use a new version")
    OUT.mkdir(); (OUT / "trajectories").mkdir(); (OUT / "figures").mkdir()
    protocol = json.loads((p.ROOT / "outputs_clock_arbitrated_v42/protocol.json").read_text())
    cfg = protocol["old_clock_settings"]
    inventory = {r["id"]: r for r in json.loads((p.ROOT / "outputs_amended_v2/inventory.json").read_text())}
    people = set.union(*FOLDS)
    ids = [i for i in protocol["training_ids"] if inventory[i]["participant"] in people]
    assert len(ids) == 207 and all(inventory[i]["partition"] == "train" for i in ids)
    fallback = set(protocol["fallback_old_clock_ids"])
    manifests = {s: json.loads((s / "artifact_manifest.json").read_text()) for s in (OLD, NEW)}
    frozen = verified_json(travel.OUT, "fold_models.json")
    yawdir = p.ROOT / "outputs_projected_yaw_v52"
    p.save_json(OUT / "protocol.json", dict(
        hypothesis="Previously selected projected yaw and bounded braking-memory forward residual address independent yaw and travel errors; combination may improve the projected-yaw control.",
        gains=GAINS, projected_yaw_weight=1.0, ridge_alpha=travel.RIDGE_ALPHA, taus_s=travel.TAUS_S,
        correction="Forward velocity only; frozen v56 fitting-only 99.5% cap; frozen v52 yaw scalar; zero lateral velocity",
        data="207 TRAIN recordings, same 12 people/participant-held folds; no validation or test",
        selection="Minimum equal-participant XY RMSE with worst participant AND maneuver ratio <=1.05 vs projected-yaw control",
        clock="Frozen v42 training clocks/QC, device-time based; inherited preparation remains conditional",
        reference="C3D used for fitting labels/evaluation and authorized initial pose only; no trajectory estimator inputs/reset/alignment",
        caveats="Offline projected gravity uses future IMU only. Historical validation hypothesis exposure remains exploratory. This is not independent whole-preparation nesting.",
        training_ids=ids, folds=[sorted(f) for f in FOLDS], validation_accessed=False, test_accessed=False,
        source_sha256={"fold_models_v56": p.digest(travel.OUT / "fold_models.json"), "script": p.digest(Path(__file__))}))
    records = []
    for fi, held in enumerate(FOLDS):
        model = frozen[str(fi)]; yaw = verified_json(yawdir, f"fold_{fi}_models.json")
        assert model["calibration"] == yaw["calibration"]
        assert set(model["fit_ids"]) == set(yaw["fitting_ids"])
        assert all(inventory[i]["participant"] not in held for i in model["fit_ids"])
        assert set(model["held_ids"]) == {i for i in ids if inventory[i]["participant"] in held}
        for trial_id in model["held_ids"]:
            row = inventory[trial_id]; src = OLD if trial_id in fallback else NEW
            data, _ = load_cache(src, trial_id, manifests[src])
            cal = model["calibration"][row["setup"]]
            entry = travel.prepare_entry(row, data, cal)
            ymodel = yaw["yaw"][row["setup"]]
            projected = proxy(data, cal) * ymodel["scale"] + ymodel["intercept"]
            predictions = {}
            for gain in GAINS:
                motion = travel.corrected_motion(entry, model["models"], gain)
                motion[:, 2] = projected
                xy, heading = integrate(data, motion)
                predictions[gain] = xy, heading
                records.append(dict(fold=fi, gain=gain, id=trial_id, participant=row["participant"], condition=row["condition"],
                                    **p.metrics(data, xy, heading, cfg), **extra_metrics(data, xy)))
            np.savez_compressed(OUT / "trajectories" / (trial_id + ".npz"), t=data["t"], reference_xy=data["gt_xy"],
                                reference_heading=data["gt_heading"], reference_valid=data["gt_valid"],
                                **{f"gain_{gain:g}_xy": value[0] for gain, value in predictions.items()},
                                **{f"gain_{gain:g}_heading": value[1] for gain, value in predictions.items()})
            plot(data, predictions, row)
            print(len(records) // len(GAINS), trial_id, flush=True)
    p.write_csv(OUT / "trials.csv", records)
    finish(records, start)


def finish(records, start):
    yawdir = p.ROOT / "outputs_projected_yaw_v52"
    summaries, ppall, mmall = {}, {}, {}
    for gain in GAINS:
        rr = [r for r in records if r["gain"] == gain]
        summary, pp, mm = p.summarize(rr); summary.update(aggregate_extra(rr))
        for item in pp: item.update(aggregate_extra([r for r in rr if r["participant"] == item["participant"]]))
        for item in mm: item.update(aggregate_extra([r for r in rr if r["condition"] == item["condition"]]))
        summaries[str(gain)], ppall[str(gain)], mmall[str(gain)] = summary, pp, mm
        p.write_csv(OUT / f"gain_{gain:g}_participants.csv", pp); p.write_csv(OUT / f"gain_{gain:g}_maneuvers.csv", mm)
    expected = verified_json(yawdir, "run.json")["selected"]["score"]
    assert abs(summaries["0.0"]["equal_participant_mean_position_rmse_m"] - expected) < 1e-10
    candidates = []
    for gain in GAINS:
        def ratios(items, control, key):
            metric = "mean_trial_position_rmse_m" if key == "participant" else "equal_participant_mean_position_rmse_m"
            base = {r[key]: r[metric] for r in control}
            return {r[key]: r[metric] / base[r[key]] for r in items}
        pr = ratios(ppall[str(gain)], ppall["0.0"], "participant")
        mr = ratios(mmall[str(gain)], mmall["0.0"], "condition")
        candidates.append(dict(gain=gain, summary=summaries[str(gain)], worst_participant_ratio=max(pr.values()),
                               worst_maneuver_ratio=max(mr.values()), participant_ratios=pr, maneuver_ratios=mr,
                               trials_regressing=sum(r["position_rmse_m"] > next(b["position_rmse_m"] for b in records if b["id"] == r["id"] and b["gain"] == 0) for r in records if r["gain"] == gain)))
    eligible = [c for c in candidates if c["worst_participant_ratio"] <= GUARD and c["worst_maneuver_ratio"] <= GUARD]
    selected = min(eligible, key=lambda c: c["summary"]["equal_participant_mean_position_rmse_m"])
    p.save_json(OUT / "run.json", dict(candidates=candidates, selected=selected, training_records=207,
                baseline_reproduced_m=expected, validation_accessed=False, test_accessed=False, runtime_s=time.perf_counter()-start))
    p.save_json(OUT / "artifact_manifest.json", dict(sha256={str(f.relative_to(OUT)): p.digest(f) for f in OUT.rglob("*") if f.is_file()}))
    print(json.dumps(selected, indent=2), flush=True)


def replot():
    inventory = {r["id"]: r for r in json.loads((p.ROOT / "outputs_amended_v2/inventory.json").read_text())}
    for path in (OUT / "trajectories").glob("*.npz"):
        with np.load(path) as z:
            data = dict(t=z["t"], gt_xy=z["reference_xy"], gt_heading=z["reference_heading"], gt_valid=z["reference_valid"])
            predictions = {g: (z[f"gain_{g:g}_xy"], z[f"gain_{g:g}_heading"]) for g in GAINS}
            plot(data, predictions, inventory[path.stem])
    result = json.loads((OUT / "run.json").read_text())
    result["plot_revision_sha256"] = p.digest(Path(__file__))
    result["plot_revision"] = "Relative wrapped yaw for both signals; preserve reference gaps and break +/-pi discontinuities. Numeric experiment unchanged."
    p.save_json(OUT / "run.json", result)
    p.save_json(OUT / "artifact_manifest.json", dict(sha256={str(f.relative_to(OUT)): p.digest(f) for f in OUT.rglob("*") if f.is_file() and f.name != "artifact_manifest.json"}))


if __name__ == "__main__":
    import sys
    if "--replot" in sys.argv:
        replot()
    elif "--finish" in sys.argv:
        import csv
        records = list(csv.DictReader((OUT / "trials.csv").open()))
        for row in records:
            for key in row:
                if key not in ("id", "participant", "condition"):
                    try: row[key] = float(row[key])
                    except ValueError: pass
        finish(records, time.perf_counter())
    else:
        main()
