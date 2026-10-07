"""Inspect all exposed validation C3Ds; distinguish coordinates from observation flags."""
from pathlib import Path
import csv,json
from collections import Counter
import numpy as np
import ezc3d
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs_c3d_recovery';OUT.mkdir(exist_ok=True)
inventory={r['id']:r for r in json.loads((ROOT/'outputs_amended_v2/inventory.json').read_text())}
qc=list(csv.DictReader((ROOT/'outputs_observed_reference_v7/qc.csv').open(newline='',encoding='utf-8')))
rows=[inventory[r['id']] for r in qc if r['partition']=='validation' and r['status']=='accepted'];result=[]
def runs(mask):
    ix=np.flatnonzero(np.diff(np.r_[False,mask,False].astype(int)));return list(zip(ix[::2],ix[1::2]))
for r in rows:
    assert r['partition']=='validation'
    c=ezc3d.c3d(str(ROOT/r['c3d']));labels=[s.strip() for s in c['parameters']['POINT']['LABELS']['value']];ids=[labels.index(s) for s in ['L_FAL','R_FAL']]
    xyz=c['data']['points'][:3,ids,:].transpose(2,1,0);res=c['data']['meta_points']['residuals'][0,ids,:].T;hz=float(c['header']['points']['frame_rate']);finite=np.isfinite(xyz).all((1,2));nonzero=(np.linalg.norm(xyz,axis=2)>1e-8).all(1)
    stored=finite&nonzero&(res>=0).all(1);observed=stored&(res>0).all(1);masks=c['data']['meta_points'].get('camera_masks');supportpop=False
    if masks is not None:
        support=np.asarray(masks)[:,ids,:].any(0).T;supportpop=bool(support.any())
        if supportpop:observed&=support.all(1)
    missing=runs(~stored);interior=[(a,b) for a,b in missing if a>0 and b<len(stored)]
    processed=stored&~observed
    result.append(dict(id=r['id'],condition=r['condition'],participant=r['participant'],frames=len(stored),rate_hz=hz,stored_position_frames=int(stored.sum()),direct_observation_frames=int(observed.sum()),processed_position_frames=int(processed.sum()),actually_unavailable_frames=int((~stored).sum()),interior_unavailable_runs=len(interior),interior_short_200ms_frames=sum(b-a for a,b in interior if (b-a)/hz<=.2),longest_unavailable_gap_s=max([(b-a)/hz for a,b in missing],default=0),longest_processed_run_s=max([(b-a)/hz for a,b in runs(processed)],default=0),camera_masks_populated=supportpop,c3d=r['c3d']))
with (OUT/'native_audit.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
summary=dict(trials=len(result),frames=sum(r['frames'] for r in result),stored_frames=sum(r['stored_position_frames'] for r in result),observed_frames=sum(r['direct_observation_frames'] for r in result),processed_frames=sum(r['processed_position_frames'] for r in result),unavailable_frames=sum(r['actually_unavailable_frames'] for r in result),recordings_with_unavailable=sum(r['actually_unavailable_frames']>0 for r in result),short_interior_200ms_frames=sum(r['interior_short_200ms_frames'] for r in result),conditions={cond:{k:sum(r[k] for r in result if r['condition']==cond) for k in ['frames','stored_position_frames','direct_observation_frames','processed_position_frames','actually_unavailable_frames']} for cond in sorted({r['condition'] for r in result})},test_accessed=False)
(OUT/'native_audit_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
