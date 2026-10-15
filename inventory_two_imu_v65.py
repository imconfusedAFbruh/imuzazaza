"""Read-only historical inventory. Does not add recordings to any split."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import ezc3d
import pipeline as p


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    root = p.ROOT / 'outdatedwithonly_2imu'
    out = p.ROOT / 'outputs_two_imu_inventory_v65'
    if out.exists():
        raise FileExistsError(out)
    acquisitions, references, hashes = [], [], {}
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        digest = sha(path)
        hashes[str(path.relative_to(root))] = digest
        if path.name == 'metadata.json':
            meta = json.loads(path.read_text(encoding='utf-8-sig'))
            meta = meta[0] if isinstance(meta, list) else meta
            sensors = [s for s, filename in [('L', 'left_raw.csv'), ('R', 'right_raw.csv'), ('C', 'center_raw.csv')] if (path.parent / filename).exists()]
            acquisitions.append({'directory': str(path.parent.relative_to(root)), 'session_id': meta.get('session_id'), 'athlete': meta.get('athlete_name'), 'sensor_files': sensors, 'metadata_recorded_sides': meta.get('recorded_sides'), 'firmware_versions': meta.get('firmware_versions'), 'strict_track_eligible': False, 'reason': 'participant overlap and conversion/clock compatibility not established'})
        if path.suffix.lower() == '.c3d':
            row = {'path': str(path.relative_to(root)), 'sha256': digest}
            try:
                c = ezc3d.c3d(str(path))
                row.update(point_used=int(c['parameters']['POINT']['USED']['value'][0]), labels=list(c['parameters']['POINT']['LABELS']['value']), rate_hz=float(c['parameters']['POINT']['RATE']['value'][0]), frames=int(c['data']['points'].shape[2]))
            except Exception as exc:
                row['read_error'] = str(exc)
            references.append(row)
    # Byte identity is evidence of duplication; nonidentity cannot rule out re-export.
    prior = json.loads((p.ROOT / 'outputs_amended_v2/inventory.json').read_text())
    size_index = {}
    for record in prior:
        for key in ('imu', 'c3d'):
            candidate = p.ROOT / record.get(key, '')
            if candidate.is_file():
                size_index.setdefault(candidate.stat().st_size, []).append((record['id'], candidate))
    prior_hashes, duplicates = {}, []
    for relative, digest in hashes.items():
        path = root / relative
        for identifier, candidate in size_index.get(path.stat().st_size, []):
            if candidate not in prior_hashes:
                prior_hashes[candidate] = sha(candidate)
            if digest == prior_hashes[candidate]:
                duplicates.append({'legacy_file': relative, 'existing_id': identifier, 'existing_file': str(candidate.relative_to(p.ROOT))})
    p.save_json(out / 'inventory.json', {'acquisitions': acquisitions, 'c3d': references, 'file_hashes': hashes, 'byte_duplicates_with_existing_inventory': duplicates, 'semantic_acquisition_deduplication': 'unresolved: different exports can represent the same acquisition'})
    summary = {'metadata_recordings': len(acquisitions), 'sensor_file_combinations': dict(Counter(','.join(r['sensor_files']) for r in acquisitions)), 'c3d_files': len(references), 'c3d_point_used_counts': dict(Counter(str(r.get('point_used', 'read_error')) for r in references)), 'byte_duplicate_matches': len(duplicates), 'hashed_files': len(hashes), 'training_modified': False}
    p.save_json(out / 'run.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    assert len(hashlib.sha256(b'check').hexdigest()) == 64
    main()
