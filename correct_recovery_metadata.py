"""Correct date coverage metadata; fitted models and predictions are unchanged."""
from pathlib import Path
import csv,json,hashlib
root=Path(__file__).resolve().parent;out=root/'outputs_recovered_training_v32';source=root/'recovered_training_experiment_v32.py'
snapshot=out/'executed_training_source.py';snapshot.write_bytes(source.read_bytes())
text=source.read_text();text=text.replace("a['participant'].startswith('earlier:')","a['id'][:10] not in ('2026-09-24','2026-09-25')").replace("not a['id'][:10] not in ('2026-09-24','2026-09-25')","a['id'][:10] in ('2026-09-24','2026-09-25')");source.write_text(text)
run=json.loads((out/'run.json').read_text());audit=list(csv.DictReader((out/'training_recovery_audit.csv').open(newline='')))
run['earlier_training_trials']=sum(a['id'][:10] not in ('2026-09-24','2026-09-25') for a in audit);run['target_training_trials']=len(audit)-run['earlier_training_trials']
run['metadata_correction']='Date coverage counts corrected from participant-prefix heuristic to acquisition date: 266 earlier, 207 target. Fitted models/predictions unchanged. Executed source snapshot retained.'
run['executed_source_snapshot_sha256']=hashlib.sha256(snapshot.read_bytes()).hexdigest();run['source_sha256']['recovered_training_experiment_v32.py']=hashlib.sha256(source.read_bytes()).hexdigest();(out/'run.json').write_text(json.dumps(run,indent=2))
manifest=json.loads((out/'artifact_manifest.json').read_text())
for p in [snapshot,out/'run.json']:manifest['sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2));print(run['earlier_training_trials'],run['target_training_trials'])
