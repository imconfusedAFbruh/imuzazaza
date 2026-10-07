"""Fixed validation of the TRAIN-selected v52 gravity-projected center yaw.

This is development validation, not a fresh blind test. The only candidate
evaluated is weight=1.0, selected on participant-held TRAIN folds in v52.
Calibration and the projected-yaw scalar mapping are refit on the 207 known
target TRAIN recordings only. Validation is never used to choose a parameter.
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import json
import time
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

import pipeline as p
from participant_folds_experiment_v24 import FOLDS
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from trajectory_calibration_v10 import integrate


OUT = p.ROOT / "outputs_projected_yaw_validation_v54"
CUTOFF_HZ = 0.3
SELECTED_WEIGHT = 1.0


def projected_proxy(data, calibration, *, cutoff_hz=CUTOFF_HZ, sample_rate_hz=100.0):
    """Bias-corrected center gyro projected onto a low-pass gravity proxy."""
    accel = np.asarray(data["raw"][:, 12:15], dtype=float).copy()
    gravity = np.repeat(
        np.asarray(calibration["center_gravity_direction"], dtype=float)[None],
        len(accel),
        axis=0,
    )
    valid = np.asarray(data["imu_valid"], dtype=bool)
    for lo, hi in p.runs(valid):
        if hi - lo > 30:
            filt = sosfiltfilt(
                butter(2, float(cutoff_hz), fs=float(sample_rate_hz), output="sos"),
                accel[lo:hi],
                axis=0,
            )
            gravity[lo:hi] = filt / np.maximum(
                np.linalg.norm(filt, axis=1, keepdims=True), 1e-8
            )
    center_bias = np.asarray(calibration["gyro_bias_counts"][2], dtype=float)
    center_gyro = np.asarray(data["raw"][:, 15:18], dtype=float) - center_bias
    return np.sum(center_gyro * gravity, axis=1)


def main():
    started = time.perf_counter()
    if OUT.exists():
        raise RuntimeError("Preserve completed output")
    OUT.mkdir()

    v52 = json.loads((p.ROOT / "outputs_projected_yaw_v52" / "run.json").read_text())
    selected = v52["selected"]
    if float(selected["weight"]) != SELECTED_WEIGHT or float(selected["worst_ratio"]) > 1.05:
        raise RuntimeError("v52 TRAIN selection/guard changed")

    protocol = json.loads((p.ROOT / "outputs_clock_arbitrated_v42" / "protocol.json").read_text())
    cfg = protocol["old_clock_settings"]
    fallback_train = set(protocol["fallback_old_clock_ids"])
    validation_old = set(protocol.get("arbitration_validation_old_clock_ids", []))
    inventory = {
        row["id"]: row
        for row in json.loads((p.ROOT / "outputs_amended_v2" / "inventory.json").read_text())
    }
    target_people = set.union(*FOLDS)
    train_ids = [
        trial_id
        for trial_id in protocol["training_ids"]
        if inventory[trial_id]["participant"] in target_people
    ]
    validation_ids = list(protocol["validation_ids"])
    if len(train_ids) != 207 or len(validation_ids) != 71:
        raise RuntimeError("Frozen TRAIN/validation membership changed")

    manifests = {
        folder: json.loads((folder / "artifact_manifest.json").read_text())
        for folder in (OLD, NEW)
    }
    training = []
    for trial_id in train_ids:
        row = inventory[trial_id]
        if row["partition"] != "train":
            raise RuntimeError("Non-TRAIN record in fitting set")
        source = OLD if trial_id in fallback_train else NEW
        data, _ = load_cache(source, trial_id, manifests[source])
        training.append((row, data, {}))

    calibration = p.calibrate(training, cfg)
    p.save_json(OUT / "calibration.json", calibration)

    yaw_models = {}
    for setup in calibration:
        xs, ys = [], []
        for row, data, _ in training:
            if row["setup"] != setup:
                continue
            mask = (
                data["label_valid"]
                & data["imu_valid"]
                & np.isfinite(data["gt_yaw"])
            )
            idx = np.flatnonzero(mask)[::5]
            if len(idx):
                xs.append(projected_proxy(data, calibration[setup])[idx])
                ys.append(data["gt_yaw"][idx])
        if not xs:
            raise RuntimeError(f"No TRAIN yaw labels for setup {setup}")
        yaw_models[setup] = p.robust_line(np.concatenate(xs), np.concatenate(ys))
    p.save_json(OUT / "yaw_models.json", yaw_models)

    p.save_json(
        OUT / "protocol.json",
        dict(
            hypothesis="TRAIN-selected dynamic gravity projection reduces pitch/roll cross-axis contamination of center yaw",
            selected_weight=SELECTED_WEIGHT,
            selection_parent="outputs_projected_yaw_v52/run.json",
            selected_train_worst_ratio=float(selected["worst_ratio"]),
            cutoff_hz=CUTOFF_HZ,
            filter_order=2,
            fitting_records=len(train_ids),
            validation_records=len(validation_ids),
            fitting_scope="207 known target TRAIN recordings only",
            validation_policy="exactly one frozen TRAIN-selected candidate; no validation retuning",
            clock_policy="v42 frozen arbitration/QC preparation; no position-based clock choice",
            inherited_limitations="reference geometry/QC and clock preparation inherited; projected gravity is an offline low-pass proxy, not a verified attitude estimate",
            validation_accessed=True,
            test_accessed=False,
            physical_scale_note="proxy is fit in raw counts; firmware audit separately establishes approximately 0.122 mg/LSB at +/-4g and 70 mdps/LSB at +/-2000dps",
        ),
    )

    records = []
    mapping_rows = []
    for trial_id in validation_ids:
        row = inventory[trial_id]
        if row["partition"] != "validation":
            raise RuntimeError("Non-validation record in validation set")
        source = OLD if trial_id in validation_old else NEW
        data, _ = load_cache(source, trial_id, manifests[source])
        setup = row["setup"]
        velocity = p.velocities(data, calibration[setup])
        projected = projected_proxy(data, calibration[setup])
        model = yaw_models[setup]
        projected_yaw = projected * model["scale"] + model["intercept"]
        base_motion = np.c_[velocity[:, 0], np.zeros(len(velocity)), velocity[:, 1]]
        candidate_motion = np.c_[
            velocity[:, 0],
            np.zeros(len(velocity)),
            projected_yaw,
        ]
        for method, motion in (
            ("refit_physics", base_motion),
            ("projected_yaw", candidate_motion),
        ):
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
        mapping_rows.append(
            dict(
                id=trial_id,
                setup=setup,
                participant=row["participant"],
                source_clock=source.name,
                yaw_scale=model["scale"],
                yaw_intercept=model["intercept"],
            )
        )

    p.write_csv(OUT / "trials.csv", records)
    p.write_csv(OUT / "validation_mapping.csv", mapping_rows)
    summaries = {}
    people = {}
    maneuvers = {}
    for method in ("refit_physics", "projected_yaw"):
        summary, participant_rows, maneuver_rows = p.summarize(
            [row for row in records if row["method"] == method]
        )
        summaries[method] = summary
        people[method] = {
            row["participant"]: row["mean_trial_position_rmse_m"]
            for row in participant_rows
        }
        maneuvers[method] = maneuver_rows
        p.write_csv(OUT / f"{method}_participants.csv", participant_rows)
        p.write_csv(OUT / f"{method}_maneuvers.csv", maneuver_rows)

    ratios = {
        participant: people["projected_yaw"][participant] / baseline
        for participant, baseline in people["refit_physics"].items()
    }
    run = dict(
        summary=summaries,
        participant_ratios=ratios,
        worst_participant_ratio=max(ratios.values()),
        selected_weight=SELECTED_WEIGHT,
        selection_train_worst_ratio=float(selected["worst_ratio"]),
        validation_accessed=True,
        validation_retuned=False,
        test_accessed=False,
        training_records=len(train_ids),
        validation_records=len(validation_ids),
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
