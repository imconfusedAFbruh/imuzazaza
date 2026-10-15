"""Describe independent timing prerequisites without estimating any new clock."""
import csv
import json
import re
from pathlib import Path
from matched_maneuver_audit_v115 import ROOT, digest

OUT = ROOT / 'outputs_timing_correspondence_v118'


def named_events(header):
    return sum(bool(str(label).strip()) for label in header['events']['events_label'])


def sync_labels(labels):
    return [str(s) for s in labels if re.search(r'sync|trig|clock', str(s), re.I)]


def main():
    assert named_events({'events': {'events_label': ['', '  ']}}) == 0
    assert named_events({'events': {'events_label': ['', 'Start']}}) == 1
    assert sync_labels(['Force X', 'Moment Z', 'TTL trigger']) == ['TTL trigger']
    parent = ROOT / 'outputs_reference_timing_metadata_v117'
    manifest = json.loads((parent / 'artifact_manifest.json').read_text())['sha256']
    assert digest(parent / 'metadata.json') == manifest['metadata.json']
    parent_run = json.loads((parent / 'run.json').read_text())
    assert digest(parent / 'run.json') == manifest['run.json']
    inventory_path = ROOT / 'outputs_amended_v2/inventory.json'
    assert digest(inventory_path) == parent_run['inventory_sha256']
    inventory = {r['id']: r for r in json.loads(inventory_path.read_text())}
    source_rows = json.loads((parent / 'metadata.json').read_text())
    assert len(source_rows) == len({r['id'] for r in source_rows}) == 8
    rows = []
    for meta in source_rows:
        inv = inventory[meta['id']]
        assert inv['partition'] == 'train'
        path = ROOT / inv['imu']
        before = digest(path)
        with path.open(newline='') as f:
            reader = csv.DictReader(f)
            first = next(reader)
            columns = reader.fieldnames
        timing_names = ('session_id', 'wheel', 'seq', 'timestamp_device_us', 'timestamp_pc_monotonic_ns', 'packet_id')
        assert all(k in columns for k in timing_names)
        assert digest(path) == before
        processing = meta['parameters'].get('PROCESSING', {}).get('selected', {})
        analog = meta['parameters'].get('ANALOG', {}).get('selected', {})
        labels = analog.get('LABELS', {}).get('value', [])
        rows.append(dict(id=meta['id'], imu_path=inv['imu'], imu_sha256=before,
                         first_row_timing={k: first[k] for k in timing_names},
                         named_header_events=named_events(meta['header']),
                         sync_named_analog_channels=sync_labels(labels),
                         creation_date=processing.get('Creation date', {}).get('value'),
                         creation_time=processing.get('Creation time', {}).get('value'),
                         cropped_start=processing.get('Cropped Measurement Start Frame', {}).get('value'),
                         cropped_end=processing.get('Cropped Measurement End Frame', {}).get('value'),
                         independent_clock_correspondence_established=False))
    OUT.mkdir(exist_ok=False)
    (OUT / 'cases.json').write_text(json.dumps(rows, indent=2))
    result = dict(experiment='v118', recordings=8,
                  named_header_event_count=sum(r['named_header_events'] for r in rows),
                  explicitly_sync_named_analog_channels=sum(len(r['sync_named_analog_channels']) for r in rows),
                  independent_mappings_established=0, imu_rows_inspected=8,
                  motion_or_localization_analysis=False, analog_samples_analyzed=0,
                  validation_accessed=False, test_accessed=False, promotion=False,
                  parent_manifest_sha256=digest(parent / 'artifact_manifest.json'),
                  input_metadata_sha256=manifest['metadata.json'],
                  input_run_sha256=manifest['run.json'],
                  protocol_sha256=digest(ROOT / 'research_docs/timing_correspondence_v118.md'),
                  helper_sha256=digest(ROOT / 'matched_maneuver_audit_v115.py'))
    (OUT / 'run.json').write_text(json.dumps(result, indent=2))
    (OUT / 'artifact_manifest.json').write_text(json.dumps(dict(
        sha256={p.name: digest(p) for p in OUT.iterdir() if p.is_file()},
        source_sha256=digest(Path(__file__))), indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
