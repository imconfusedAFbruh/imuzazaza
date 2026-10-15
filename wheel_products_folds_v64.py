"""Reuse v62 fold runner for wheel-only nonlinear speed/slowing features."""
import json
from pathlib import Path
import numpy as np
import pipeline as p
import tilt_safe_speed_folds_v62 as runner
from braking_hysteresis_folds_v56 import causal_ema

base_features = runner.features


def features(data, cal, variant):
    x = base_features(data, cal, 'no_center_accel')
    speed, yaw, diff, dv = x[:, 0], x[:, 1], x[:, 4], x[:, 6]
    if variant == 'wheel_products':
        return np.c_[x, speed * np.abs(speed), speed * yaw, yaw * yaw,
                     diff * speed, dv * np.abs(speed), x[:, 9] * np.abs(speed),
                     x[:, 12] * speed, x[:, 14] * speed]
    if variant != 'bidirectional_slowing':
        raise ValueError(variant)
    # A fixed near-zero taper avoids sign jumps; no maneuver labels or event gates.
    slowing = np.maximum(-np.tanh(speed / .1) * dv, 0.)
    result = x.copy()
    result[:, 9] = slowing
    for column, tau in zip((10, 11, 12, 13), (.1, .25, .5, 1.)):
        result[:, column] = np.nan_to_num(causal_ema(slowing, data['t'], data['imu_valid'], tau))
    result[:, 14] = result[:, 12] * np.abs(diff)
    return result


if __name__ == '__main__':
    runner.OUT = p.ROOT / 'outputs_wheel_products_v64'
    runner.VARIANTS = ('wheel_products', 'bidirectional_slowing')
    runner.features = features
    runner.main()
    protocol = json.loads((runner.OUT / 'protocol.json').read_text())
    protocol.update(hypothesis='Wheel-only low-order speed/yaw/slowing interactions or signed-speed slowing may capture travel response without tilt-contaminated acceleration',
                    wrapper_sha256=p.digest(Path(__file__)),
                    wheel_products='8 low-order interactions; training normalization and clipping unchanged',
                    bidirectional_slowing='max(-tanh(speed/.1)*dv,0), rebuilt causal EMA states; .1m/s fixed taper',
                    no_center_accel=True, dynamic_gravity_cutoff_hz=None)
    p.save_json(runner.OUT / 'protocol.json', protocol)
    p.save_json(runner.OUT / 'artifact_manifest.json', dict(sha256={str(f.relative_to(runner.OUT)):p.digest(f)
        for f in runner.OUT.rglob('*') if f.is_file() and f.name != 'artifact_manifest.json'}))
