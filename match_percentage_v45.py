from pathlib import Path
import csv,json,hashlib
import numpy as np
from route_metrics_audit_v36 import pieces,sample_piece,point_to_pieces
root=Path.cwd();source=root/'outputs_dynamic_blend_v34';out=root/'outputs_match_percentage_v45';out.mkdir(exist_ok=False)
meta=list(csv.DictReader((source/'selected_blend_trials.csv').open()));manifest=json.loads((source/'artifact_manifest.json').read_text())['sha256'];rows=[]
thresholds=[10,20,50,100,200]
for row in meta:
    path=source/'trajectories'/(row['id']+'.npz')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[str(path.relative_to(source))]
    with np.load(path) as z:
        ref=z['reference_xy_m'];pred=z['selected_blend_xy_m'];valid=z['reference_valid']&np.isfinite(ref).all(1)&np.isfinite(pred).all(1)&np.isfinite(z['original_v21_xy_m']).all(1)
        error=np.linalg.norm(pred[valid]-ref[valid],axis=1)
        rp=pieces(ref,valid);pp=pieces(pred,valid)
        q=np.concatenate([sample_piece(p,.01) for p in pp]);r=np.concatenate([sample_piece(p,.01) for p in rp])
        d1=point_to_pieces(q,rp);d2=point_to_pieces(r,pp)
        result=dict(id=row['id'],participant=row['participant'],condition=row['condition'],observed_frames=int(valid.sum()))
        for mm in thresholds:
            result[f'synchronized_within_{mm}mm_pct']=float(100*np.mean(error<=mm/1000))
            result[f'symmetric_route_within_{mm}mm_pct']=float(50*(np.mean(d1<=mm/1000)+np.mean(d2<=mm/1000)))
        rows.append(result)
people=sorted({r['participant'] for r in rows});fields=[k for k in rows[0] if k.endswith('_pct')]
summary={k:float(np.mean([np.mean([r[k] for r in rows if r['participant']==p]) for p in people])) for k in fields}
with (out/'trials.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
result=dict(model='retained v34 tilt blend .75',trials=len(rows),participants=len(people),summary=summary,aggregation='Equal trial mean within participant then equal participant mean',synchronized_definition='Fraction of valid observed time-matched positions with 2D Euclidean error at most threshold',route_definition='Equal weight of two directional proportions;10mm spatial queries to exact supported polylines; no gap bridges',test_accessed=False,alignment='Original frozen initial pose only; no additional fitted alignment',caveat='Threshold-dependent development coverage, not a universal accuracy percentage')
(out/'run.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
