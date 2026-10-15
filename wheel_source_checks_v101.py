"""Synthetic source-equation checks only; no recording or model inputs."""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs_wheel_source_checks_v101'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def affine_time(ts, bm, bs, em, es):
    if bs == es:
        raise ValueError('Distinct slave trigger timestamps required')
    delta = bm - bs
    slope = (bm - em) / (bs - es)
    intercept = (em * (bs + delta) - bm * (es + delta)) / (bs - es)
    return slope * (ts + delta) + intercept


def main():
    assert not (ROOT/'research_state/STOP').exists()
    assert not Path('D:/project/WheelAthelse/research_state/STOP').exists()
    assert not OUT.exists(), 'Completed outputs must not be overwritten'
    source = ROOT / 'outputs_wheel_sources_v100'
    parent = json.loads((source / 'manifest.json').read_text())
    for name, expected in parent.items():
        assert digest(source / name) == expected, name
    protocol = ROOT / 'research_docs/wheel_source_consistency_v100_v101.md'
    records = []
    for side, yaw, wheel, phase, degrees in itertools.product(
            [-1, 1], [-2., 0., 2.], [-3., 0., 3.],
            [0., .3, np.pi / 2, np.pi], [0., 3.2, 12.]):
        a = np.deg2rad(degrees)
        g = np.array([yaw*np.cos(a)*np.sin(phase),
                      wheel+side*yaw*np.sin(a), yaw*np.cos(a)*np.cos(phase)])
        recovered_yaw = np.sign(yaw) * np.hypot(g[0], g[2]) / np.cos(a)
        recovered_wheel = g[1] - side * recovered_yaw * np.sin(a)
        error = max(abs(recovered_yaw-yaw), abs(recovered_wheel-wheel))
        assert error <= 1e-12
        records.append(dict(side=side, yaw=yaw, wheel=wheel, phase=float(phase),
                            camber_deg=degrees, max_error=float(error)))
    radius_cases = []
    for w1, w2 in [(2., 1.), (1., -1.), (0., 2.), (-1., -2.)]:
        r, b, dt = .30, .52, .01
        d1, d2 = r*w1*dt, r*w2*dt
        geometric = b*(d1+d2)/(2*(d1-d2))
        extracted13 = b*(w1+w2)/(2*(w1-w2))
        derived = b*(w1+w2)/(2*(w1-w2))
        assert abs(geometric-derived) <= 1e-12
        radius_cases.append(dict(wheel1=w1, wheel2=w2, radius_m=r,
                                 eq10_radius_m=geometric,
                                 extracted_eq13_radius=extracted13,
                                 discrepancy=extracted13-geometric))
    assert max(abs(x['discrepancy']) for x in radius_cases) <= 1e-12
    mapped = [affine_time(t, 12., 10., 112.2, 110.) for t in [10., 60., 110.]]
    np.testing.assert_allclose(mapped, [12., 62.1, 112.2], rtol=0, atol=1e-12)
    try:
        affine_time(10., 12., 10., 112., 10.)
    except ValueError:
        rejected_equal_timestamps = True
    else:
        raise AssertionError('Degenerate trigger mapping must fail')
    result = dict(experiment='v101', kind='synthetic-source-consistency-only',
                  gyro_cases=records, curvature_cases=radius_cases,
                  affine_mapping=mapped, rejected_equal_timestamps=rejected_equal_timestamps,
                  maximum_gyro_error=max(x['max_error'] for x in records),
                  wisdom_visual_transcription_verified=False,
                  recording_reads=0, predictions=0, promotion=False,
                  parents={'outputs_wheel_sources_v100/manifest.json': digest(source/'manifest.json'),
                           str(protocol.relative_to(ROOT)): digest(protocol),
                           Path(__file__).name: digest(Path(__file__))})
    OUT.mkdir()
    (OUT/'run.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'run.json': digest(OUT/'run.json')}, indent=2)+'\n')
    print(json.dumps(dict(cases=len(records), max_error=result['maximum_gyro_error'],
                         first_radius_discrepancy=radius_cases[0]['discrepancy'],
                         affine_mapping=mapped, output=str(OUT))))


if __name__ == '__main__':
    main()
