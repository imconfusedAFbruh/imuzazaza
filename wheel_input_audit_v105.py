"""Source input metadata and valid-support audit; no motion fits or scores."""
import csv
import json
from pathlib import Path

import numpy as np

from basin_completeness_v91 import verify
from wheel_source_checks_v101 import ROOT, digest

OUT = ROOT/'outputs_wheel_inputs_v105'
SENSOR = ROOT/'outputs_native_projection_v80'
MODELS = ROOT/'outputs_fold_seedless_clock_v84'


def main():
    assert not OUT.exists()
    assert not (ROOT/'research_state/STOP').exists()
    assert not Path('D:/project/WheelAthelse/research_state/STOP').exists()
    hashes = verify(SENSOR)+verify(MODELS)
    inv = {r['id']:r for r in json.loads((ROOT/'outputs_amended_v2/inventory.json').read_text())}
    models = json.loads((MODELS/'models.json').read_text())
    rows = []
    for fold, model in models.items():
        assert not set(model['held_ids']) & set(model['fit_ids'])
        for ident in model['held_ids']:
            meta = inv[ident]
            assert meta['partition']=='train'
            with np.load(SENSOR/'sensors'/(ident+'.npz')) as z:
                t, valid = z['t'], z['imu_valid']
            assert len(t)==len(valid) and np.all(np.diff(t)>0)
            prefix = t < t[0]+.5
            internal = (~valid).copy()
            internal[0]=internal[-1]=False
            rows.append(dict(id=ident,participant=meta['participant'],fold=fold,
                             frames=len(t),invalid=int((~valid).sum()),
                             internal_invalid=int(internal.sum()),prefix_frames=int(prefix.sum()),
                             valid_prefix_frames=int((prefix&valid).sum()),
                             prefix_half_second_span_available=bool(t[-1]>=t[0]+.5),
                             stationarity_verified=False))
    assert len(rows)==len({x['id'] for x in rows})==207
    assert sum(x['participant']=='No.20' for x in rows)==15
    cal = [dict(fold=f,setup=s,fields=list(c),
                objectives=[x.get('fit_objective','') for x in c['terms']],
                axes=[x['axis'] for x in c['terms']])
           for f,q in models.items() for s,c in q['calibration'].items()]
    result = dict(experiment='v105',trials=207,no20=15,parent_hashes_verified=hashes,
                  total_frames=sum(x['frames'] for x in rows),
                  invalid_frames=sum(x['invalid'] for x in rows),
                  internal_invalid_frames=sum(x['internal_invalid'] for x in rows),
                  complete_prefix_trials=sum(x['prefix_frames']==x['valid_prefix_frames'] and x['prefix_half_second_span_available'] for x in rows),
                  quiet_prefix_stationarity_verified=False,calibration_metadata=cal,
                  predictions=0,promotion=False,
                  parents={str(p.relative_to(ROOT)):digest(p) for p in
                           [ROOT/'config/default.yaml',ROOT/'research_docs/wheel_inputs_v105.md',
                            ROOT/'wheel_input_audit_v105.py',ROOT/'wheel_source_checks_v101.py']})
    OUT.mkdir()
    with (OUT/'trials.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (OUT/'run.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({p.name:digest(p) for p in OUT.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['calibration_metadata','parents']}))


if __name__ == '__main__':
    main()
