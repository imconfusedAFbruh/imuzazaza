"""C3D metadata only: inspect existing timing evidence for rejected TRAIN IDs."""
import json
import re
from pathlib import Path
import ezc3d
import numpy as np
from matched_maneuver_audit_v115 import ROOT, digest

OUT = ROOT / 'outputs_reference_timing_metadata_v117'
TIMING = re.compile(r'DATE|TIME|CLOCK|SYNC|TRIG|START|END|FRAME', re.I)


def native(value):
    if isinstance(value, np.ndarray):
        return native(value.tolist())
    if isinstance(value, np.generic):
        return native(value.item())
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(type(value).__name__)


def extract(parameters):
    result = {}
    for group, entries in parameters.items():
        names = [k for k, v in entries.items() if isinstance(v, dict) and 'value' in v]
        chosen = [k for k in names if group in ('EVENT', 'TRIAL') or TIMING.search(group + ':' + k)
                  or group == 'ANALOG' and k in ('USED', 'LABELS', 'UNITS', 'RATE', 'DESCRIPTIONS')]
        result[group] = dict(parameter_names=names, selected={k: native(entries[k]) for k in chosen})
    return result


def main():
    assert json.loads(json.dumps(native({'x': np.array([np.int64(2)]), 'y': np.bool_(True)}))) == {'x': [2], 'y': True}
    fixture = extract({'POINT': {'FRAMES': {'value': [100]}, 'LABELS': {'value': ['L', 'R']}},
                       'EVENT': {'TIMES': {'value': np.array([[0], [1.]])}}})
    assert set(fixture['POINT']['selected']) == {'FRAMES'}
    assert fixture['EVENT']['selected']['TIMES']['value'] == [[0.0], [1.0]]
    parent = ROOT / 'outputs_reference_clock_bound_v113'
    manifest = json.loads((parent / 'artifact_manifest.json').read_text())['sha256']
    assert digest(parent / 'cases.json') == manifest['cases.json']
    cases = json.loads((parent / 'cases.json').read_text())
    assert len(cases) == len({r['id'] for r in cases}) == 8
    inventory_path = ROOT / 'outputs_amended_v2/inventory.json'
    inventory_hash = digest(inventory_path)
    inventory = {r['id']: r for r in json.loads(inventory_path.read_text())}
    rows = []
    for case in cases:
        row = inventory[case['id']]
        assert row['partition'] == 'train'
        path = ROOT / row['c3d']
        before = digest(path)
        c = ezc3d.c3d(str(path))
        metadata = extract(c['parameters'])
        assert digest(path) == before
        rows.append(dict(id=row['id'], path=row['c3d'], sha256=before,
                         reference_gate_blocked=not case['imu_only_possible'],
                         header=native({k: c['header'][k] for k in c['header'].keys()}), parameters=metadata))
    assert digest(inventory_path) == inventory_hash
    OUT.mkdir(exist_ok=False)
    (OUT / 'metadata.json').write_text(json.dumps(rows, indent=2, allow_nan=False))
    result = dict(experiment='v117', train_reference_files=8, point_or_analog_samples_analyzed=0,
                  inventory_sha256=inventory_hash, cases_sha256=manifest['cases.json'],
                  parent_manifest_sha256=digest(parent / 'artifact_manifest.json'),
                  protocol_sha256=digest(ROOT / 'research_docs/reference_timing_metadata_v117.md'),
                  validation_accessed=False, test_accessed=False, promotion=False,
                  qualification='Metadata fields require independent correspondence to IMU timing; no new clocks accepted')
    (OUT / 'run.json').write_text(json.dumps(result, indent=2))
    (OUT / 'artifact_manifest.json').write_text(json.dumps(dict(
        sha256={p.name: digest(p) for p in OUT.iterdir() if p.is_file()},
        source_sha256=digest(Path(__file__))), indent=2))
    for row in rows:
        print(row['id'], {g: list(q['selected']) for g, q in row['parameters'].items() if q['selected']})


if __name__ == '__main__':
    main()
