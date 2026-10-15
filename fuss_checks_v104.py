"""Ideal rolling consistency only; no real sensor or optical inputs."""
import itertools
import json
from pathlib import Path

import numpy as np

from wheel_source_checks_v101 import ROOT, digest

OUT = ROOT/'outputs_fuss_checks_v104'


def main():
    assert not OUT.exists()
    assert not (ROOT/'research_state/STOP').exists()
    assert not Path('D:/project/WheelAthelse/research_state/STOP').exists()
    source = ROOT/'outputs_fuss_source_v103'
    for name, h in json.loads((source/'manifest.json').read_text()).items():
        assert digest(source/name) == h
    rows = []
    for degrees, center, yaw, phase in itertools.product(
            [0., 3.2, 17.], [-1., 0., 1.], [-2., 0., 2.], [0., .7]):
        a = np.deg2rad(degrees)
        r, track = .30, .52
        true = np.array([(center-yaw*track/2)/r, (center+yaw*track/2)/r])
        measured = true + yaw*np.sin(a)*np.array([1., -1.])
        transverse = np.array([abs(yaw)*np.cos(a)*np.sin(phase),
                               abs(yaw)*np.cos(a)*np.cos(phase)])
        turning_sign = np.sign(measured[1]-measured[0])
        recovered = measured - np.linalg.norm(transverse)*np.tan(a)*np.array([1., -1.])*turning_sign
        wheel_error = float(np.max(abs(recovered-true)))
        center_error = abs(r*float(recovered.mean())-center)
        uncorrected_center_error = abs(r*float(measured.mean())-center)
        assert wheel_error <= 1e-12 and center_error <= 1e-12
        assert uncorrected_center_error <= 1e-12
        if degrees == 0:
            assert measured[0] == recovered[0]
            recovered_yaw = None
        else:
            recovered_yaw = float((measured[0]-recovered[0])/np.sin(a))
            assert abs(recovered_yaw-yaw) <= 1e-12
        rows.append(dict(camber_deg=degrees, center=center, yaw=yaw, phase=phase,
                         wheel_error=wheel_error, center_error=center_error,
                         uncorrected_center_error=uncorrected_center_error,
                         recovered_yaw=recovered_yaw,
                         literal_yaw_defined=degrees!=0))
    assert len(rows)==54 and sum(not x['literal_yaw_defined'] for x in rows)==18
    parents = [source/'manifest.json', ROOT/'wheel_source_checks_v101.py',
               ROOT/'research_docs/fuss_consistency_v103_v104.md', Path(__file__)]
    result = dict(experiment='v104', synthetic_cases=rows,
                  literal_zero_camber_undefined=18,
                  maximum_wheel_error=max(x['wheel_error'] for x in rows),
                  maximum_yaw_error=max(abs(x['recovered_yaw']-x['yaw']) for x in rows if x['literal_yaw_defined']),
                  recording_reads=0, predictions=0, promotion=False,
                  visual_transcription_verified=False,
                  parents={str(p.resolve().relative_to(ROOT)):digest(p) for p in parents})
    OUT.mkdir()
    (OUT/'run.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'run.json':digest(OUT/'run.json')},indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['synthetic_cases','parents']}))


if __name__ == '__main__':
    main()
