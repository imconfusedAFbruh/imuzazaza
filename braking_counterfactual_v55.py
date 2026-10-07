"""Diagnostic decomposition of validation PS travel/yaw error for v42.

No model parameter, clock, threshold, or candidate is selected here. C3D rates
are used only in diagnostic counterfactuals to ask whether replacing forward
speed or yaw would remove the existing trajectory error.
"""
import json
import time
from pathlib import Path

import numpy as np

import pipeline as p
from clock_refit_experiment_v38 import NEW, load_cache
from trajectory_calibration_v10 import integrate


OUT = p.ROOT / "outputs_braking_counterfactual_v55"
FOCUS_ID = "2026-09-25__PS__PS_Trial2_No.18"


def counterfactual_motions(predicted, gt_v, gt_yaw):
    predicted = np.asarray(predicted, dtype=float)
    gt_v = np.asarray(gt_v, dtype=float)
    gt_yaw = np.asarray(gt_yaw, dtype=float)
    if predicted.ndim != 2 or predicted.shape[1] != 3:
        raise ValueError("predicted motion must be N x 3")
    if gt_v.shape != (len(predicted),) or gt_yaw.shape != (len(predicted),):
        raise ValueError("ground-truth rates must match motion length")
    speed = predicted.copy()
    speed[:, 0] = gt_v
    yaw = predicted.copy()
    yaw[:, 2] = gt_yaw
    both = predicted.copy()
    both[:, 0] = gt_v
    both[:, 2] = gt_yaw
    return {
        "predicted": predicted.copy(),
        "gt_speed": speed,
        "gt_yaw": yaw,
        "gt_speed_yaw": both,
    }


def _integral(t, x, valid):
    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    valid = np.asarray(valid, dtype=bool)
    if len(t) < 2:
        return 0.0
    dt = np.diff(t)
    good = valid[:-1] & valid[1:] & np.isfinite(x[:-1]) & np.isfinite(x[1:])
    return float(np.sum(dt[good] * 0.5 * (x[:-1][good] + x[1:][good])))


def main():
    started = time.perf_counter()
    if OUT.exists():
        raise RuntimeError("Preserve completed output")
    OUT.mkdir()

    protocol = json.loads((p.ROOT / "outputs_clock_arbitrated_v42" / "protocol.json").read_text())
    cfg = protocol["old_clock_settings"]
    if protocol.get("arbitration_validation_old_clock_ids"):
        raise RuntimeError("This diagnostic assumes the v42 validation set uses NEW clocks")

    inventory = {
        row["id"]: row
        for row in json.loads((p.ROOT / "outputs_amended_v2" / "inventory.json").read_text())
    }
    new_manifest = json.loads((NEW / "artifact_manifest.json").read_text())
    v42_manifest = json.loads((p.ROOT / "outputs_clock_arbitrated_v42" / "artifact_manifest.json").read_text())["sha256"]
    validation_ids = [
        trial_id
        for trial_id in protocol["validation_ids"]
        if inventory[trial_id]["condition"].upper() == "PS"
    ]

    p.save_json(
        OUT / "protocol.json",
        dict(
            scope="All frozen validation PS trials, with No.18 PS2 predeclared focus",
            focus_id=FOCUS_ID,
            prediction="sealed v42 new_clock_refit_blend_motion",
            diagnostic_only=True,
            selection=False,
            validation_accessed=True,
            validation_retuning=False,
            test_accessed=False,
            clock_selection_from_position=False,
            counterfactual="Replace predicted forward speed and/or yaw with observed C3D-derived rates only on finite label-valid support; retain prediction elsewhere.",
            limitation="C3D rate substitution is an oracle diagnostic and cannot be deployed. It diagnoses error budget only.",
        ),
    )

    records = []
    components = []
    for trial_id in validation_ids:
        row = inventory[trial_id]
        data, _ = load_cache(NEW, trial_id, new_manifest)
        trajectory_path = p.ROOT / "outputs_clock_arbitrated_v42" / "new_clock_trajectories" / f"{trial_id}.npz"
        rel = str(trajectory_path.relative_to(p.ROOT / "outputs_clock_arbitrated_v42"))
        if p.digest(trajectory_path) != v42_manifest[rel]:
            raise RuntimeError(f"Changed v42 trajectory: {trial_id}")
        with np.load(trajectory_path) as saved:
            predicted = np.asarray(saved["new_clock_refit_blend_motion"], dtype=float)

        label = (
            np.asarray(data["label_valid"], dtype=bool)
            & np.asarray(data["imu_valid"], dtype=bool)
            & np.isfinite(data["gt_v"])
            & np.isfinite(data["gt_yaw"])
        )
        gt_v = predicted[:, 0].copy()
        gt_yaw = predicted[:, 2].copy()
        gt_v[label] = data["gt_v"][label]
        gt_yaw[label] = data["gt_yaw"][label]
        motions = counterfactual_motions(predicted, gt_v, gt_yaw)

        valid_integral = np.asarray(data["imu_valid"], dtype=bool) & np.asarray(data["gt_valid"], dtype=bool)
        for method, motion in motions.items():
            xy, heading = integrate(data, motion)
            records.append(
                dict(
                    id=trial_id,
                    participant=row["participant"],
                    condition=row["condition"],
                    method=method,
                    **p.metrics(data, xy, heading, cfg),
                )
            )
            components.append(
                dict(
                    id=trial_id,
                    participant=row["participant"],
                    method=method,
                    signed_travel_m=_integral(data["t"], motion[:, 0], valid_integral),
                    abs_travel_m=_integral(data["t"], np.abs(motion[:, 0]), valid_integral),
                    net_yaw_deg=float(np.degrees(_integral(data["t"], motion[:, 2], valid_integral))),
                    label_fraction=float(np.mean(label)),
                )
            )

    p.write_csv(OUT / "trials.csv", records)
    p.write_csv(OUT / "components.csv", components)

    focus_metrics = {
        row["method"]: row
        for row in records
        if row["id"] == FOCUS_ID
    }
    focus_components = {
        row["method"]: row
        for row in components
        if row["id"] == FOCUS_ID
    }
    if len(focus_metrics) != 4:
        raise RuntimeError("Focus trial not found exactly once per counterfactual")

    base = focus_metrics["predicted"]["position_rmse_m"]
    diagnostic = {
        method: {
            "position_rmse_m": float(row["position_rmse_m"]),
            "heading_rmse_deg": float(row["heading_rmse_deg"]),
            "rmse_ratio_vs_predicted": float(row["position_rmse_m"] / base),
            "signed_travel_m": float(focus_components[method]["signed_travel_m"]),
            "abs_travel_m": float(focus_components[method]["abs_travel_m"]),
            "net_yaw_deg": float(focus_components[method]["net_yaw_deg"]),
            "label_fraction": float(focus_components[method]["label_fraction"]),
        }
        for method, row in focus_metrics.items()
    }
    run = dict(
        focus_id=FOCUS_ID,
        focus=diagnostic,
        validation_ps_trials=len(validation_ids),
        diagnostic_only=True,
        validation_accessed=True,
        validation_retuned=False,
        test_accessed=False,
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
