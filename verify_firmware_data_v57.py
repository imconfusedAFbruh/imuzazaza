"""Recheck the frozen 473 TRAIN + 71 validation CSVs; never open test signals."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs_firmware_verification_v57'
HEADER = 'session_id,wheel,seq,timestamp_device_us,timestamp_pc_monotonic_ns,ax_raw,ay_raw,az_raw,gx_raw,gy_raw,gz_raw,packet_id,sequence_class,missing_before'.split(',')


def main():
    inventory = {r['id']: r for r in json.loads((ROOT / 'outputs_amended_v2/inventory.json').read_text())}
    with (ROOT / 'outputs_observed_reference_v7/qc.csv').open(newline='') as f:
        accepted = [r for r in csv.DictReader(f) if r['status'] == 'accepted' and r['partition'] in ('train', 'validation')]
    assert len(accepted) == 544
    assert sum(r['partition'] == 'train' for r in accepted) == 473
    OUT.mkdir(exist_ok=False)
    totals = defaultdict(lambda: dict(files=0, rows=0, missing_before=0, sequence_missing=0,
                                     duplicates=0, backwards=0, nonmonotonic_time=0))
    samples = defaultdict(lambda: dict(dt=[], norm=[]))
    evidence = []
    for i, row in enumerate(accepted):
        source = inventory[row['id']]
        assert source['partition'] == row['partition'] != 'test'
        path = ROOT / source['imu']
        with path.open(newline='') as f:
            assert next(csv.reader(f)) == HEADER, path
        raw_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        cached = json.loads((ROOT / 'outputs_observed_reference_v7/cache' / (row['id'] + '.json')).read_text())
        assert raw_sha == cached['signature']['imu_sha256'], path
        data = np.loadtxt(path, delimiter=',', skiprows=1, dtype=np.int64,
                          usecols=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13),
                          converters={1: lambda s: {'L': 0, 'R': 1, 'C': 2}[s.decode() if isinstance(s, bytes) else s]})
        record = dict(id=row['id'], partition=row['partition'], path=source['imu'], sha256=raw_sha, roles={})
        for code, role in enumerate('LRC'):
            s = data[data[:, 0] == code]
            assert len(s) > 1, (path, role)
            seq = np.diff(s[:, 1])
            dt = np.diff(s[:, 2])
            key = source['date'] + '|' + role
            counts = dict(rows=len(s), missing_before=int(s[:, -1].sum()),
                          sequence_missing=int(np.maximum(seq - 1, 0).sum()),
                          duplicates=int((seq == 0).sum()), backwards=int((seq < 0).sum()),
                          nonmonotonic_time=int((dt <= 0).sum()))
            totals[key]['files'] += 1
            for name, value in counts.items():
                totals[key][name] += value
            samples[key]['dt'].append(dt)
            samples[key]['norm'].append(np.linalg.norm(s[:, 4:7].astype(float), axis=1))
            record['roles'][role] = counts
        evidence.append(record)
        if (i + 1) % 100 == 0:
            print(f'Checked {i + 1}/544', flush=True)
    for key, arrays in samples.items():
        dt = np.concatenate(arrays['dt'])
        totals[key]['median_dt_us'] = float(np.median(dt))
        totals[key]['effective_hz'] = float(1e6 / np.median(dt))
        totals[key]['dt_p01_p99_us'] = np.percentile(dt, [1, 99]).tolist()
        totals[key]['median_accel_norm_counts'] = float(np.median(np.concatenate(arrays['norm'])))
    bad = [r['id'] for r in evidence if any(any(v[n] for n in ('missing_before', 'sequence_missing', 'duplicates', 'backwards', 'nonmonotonic_time')) for v in r['roles'].values())]
    result = dict(records=544, train=473, validation=71, test_opened=False,
                  raw_hashes_match_sealed_cache=True, by_date_role=dict(totals), affected_records=bad,
                  exact_flashed_binary_proven=False, runtime_range_readback_available=False)
    (OUT / 'run.json').write_text(json.dumps(result, indent=2))
    (OUT / 'input_evidence.json').write_text(json.dumps(evidence, indent=2))
    assert not bad, bad
    print(json.dumps(dict(records=544, affected_records=bad, raw_hashes_match=True, test_opened=False)), flush=True)


if __name__ == '__main__':
    main()
