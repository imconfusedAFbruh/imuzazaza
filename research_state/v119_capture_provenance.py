"""Read-only source/parent seal, no numerical execution."""
import json
from pathlib import Path
import hashlib
ROOT = Path(__file__).resolve().parents[1]
names = ['learning.py','participant_folds_experiment_v24.py','clock_refit_experiment_v38.py',
         'combined_physics_folds_v58.py','research_metrics_v59.py','route_metrics_audit_v36.py',
         'outputs_projected_yaw_v52/artifact_manifest.json',
         'outputs_clock_arbitrated_v42/artifact_manifest.json',
         'outputs_observed_reference_v7/artifact_manifest.json',
         'outputs_observed_sync_v9/artifact_manifest.json',
         'outputs_amended_v2/inventory.json']
out = dict(sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names},
           purpose='Supplementary seal during live run, before outcome inspection; no fits or scores')
(ROOT/'outputs_joint_robust_motion_v119/provenance_supplement.json').write_text(json.dumps(out,indent=2))
