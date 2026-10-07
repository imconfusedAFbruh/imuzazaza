"""Audit C3D marker observation support in train/validation only; preserve parents."""
import json
from collections import defaultdict
from pathlib import Path

import ezc3d
import numpy as np

from pipeline import ROOT, digest, read_markers, runs, save_json


def main():
    out = ROOT / 'outputs_reference_support_audit_v7'
    if out.exists() and any(out.iterdir()):
        raise RuntimeError('Preserve existing diagnostics')
    rows = json.loads((ROOT / 'outputs_amended_v2/inventory.json').read_text())
    audit, failures = [], []
    for row in rows:
        if row['partition'] not in ('train', 'validation') or not row.get('c3d'):
            continue
        try:
            path = ROOT / row['c3d']
            c = ezc3d.c3d(str(path))
            labels = [x.strip() for x in c['parameters']['POINT']['LABELS']['value']]
            ids = [labels.index(name) for name in ('L_FAL', 'R_FAL')]
            points, valid, hz = read_markers(path)
            residual = c['data']['meta_points']['residuals'][0, ids, :].T
            support = c['data']['meta_points']['camera_masks'][:, ids, :].any(axis=0).all(axis=0)
            positive = (residual > 0).all(axis=1)
            supported = support & valid & positive
            zero = (residual == 0).any(axis=1) & valid
            initial = np.flatnonzero(supported)
            lat = points[:, 0, :2] - points[:, 1, :2]
            heading = np.arctan2(-lat[:, 0], lat[:, 1])
            entry = dict(id=row['id'], setup=row['setup'], participant=row['participant'],
                         partition=row['partition'], condition=row['condition'], frames=len(valid),
                         hz=hz, original_valid_fraction=float(valid.mean()),
                         supported_valid_fraction=float(supported.mean()),
                         valid_but_no_camera_frames=int((valid & ~support).sum()),
                         camera_mask_shape=list(c['data']['meta_points']['camera_masks'].shape),
                         per_marker_any_camera_fraction=[float(x.mean()) for x in c['data']['meta_points']['camera_masks'][:,ids,:].any(axis=0)],
                         per_marker_positive_residual_fraction=[float((residual[:,i]>0).mean()) for i in range(2)],
                         positive_residual_no_camera_frames=int((positive & valid & ~support).sum()),
                         no_camera_equals_zero_residual=bool(np.array_equal(valid & ~support, zero)),
                         unsupported_runs_s=[[int(a)/hz, int(b)/hz] for a, b in runs(valid & ~support)],
                         first_supported_s=float(initial[0]/hz) if len(initial) else None,
                         initial_heading_deg=float(np.rad2deg(heading[0])) if np.isfinite(heading[0]) else None,
                         first_supported_heading_deg=float(np.rad2deg(heading[initial[0]])) if len(initial) else None,
                         c3d_sha256=digest(path))
            audit.append(entry)
        except (ValueError, OSError, KeyError) as error:
            failures.append(dict(id=row['id'], reason=str(error)))
    groups = defaultdict(list)
    for entry in audit:
        groups[(entry['setup'], entry['partition'])].append(entry)
    summary = []
    for (setup, partition), group in groups.items():
        summary.append(dict(setup=setup, partition=partition, recordings=len(group),
                            recordings_with_no_supported_points=sum(x['supported_valid_fraction'] == 0 for x in group),
                            recordings_with_valid_unsupported_points=sum(x['valid_but_no_camera_frames'] > 0 for x in group),
                            mean_supported_fraction=float(np.mean([x['supported_valid_fraction'] for x in group])),
                            no_camera_equals_zero_residual_recordings=sum(x['no_camera_equals_zero_residual'] for x in group)))
    out.mkdir(exist_ok=True)
    save_json(out/'audit.json', dict(records=audit, failures=failures, summary=summary,
        test_signals_opened=False, provenance={'source_sha256':digest(Path(__file__)),
        'inventory_sha256':digest(ROOT/'outputs_amended_v2/inventory.json')},
        semantics='Camera support distinguishes export-filled points from observationally supported points. '
                  'Does not prove absolute accuracy or physical hub geometry. No estimator fitted or evaluated.'))
    for entry in summary:
        print(json.dumps(entry), flush=True)
    print('failures', len(failures), flush=True)


if __name__ == '__main__':
    main()
