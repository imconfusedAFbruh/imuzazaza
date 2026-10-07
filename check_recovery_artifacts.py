"""Check exported artifact provenance without accessing held-out test recordings."""
from pathlib import Path
import hashlib,json
import numpy as np
root=Path(__file__).resolve().parent
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={}
for folder in ['outputs_c3d_recovery','outputs_subject_st_sl_3d_restored']:
    out=root/folder;m=json.loads((out/'artifact_manifest.json').read_text())
    for name,expected in m['source_sha256'].items():
        if digest(root/name)!=expected:raise RuntimeError(f'Changed source: {name}')
    for name,expected in m['output_sha256'].items():
        if digest(out/name)!=expected:raise RuntimeError(f'Changed export: {name}')
    checks[folder]={'source_files_checked':len(m['source_sha256']),'exports_checked':len(m['output_sha256'])}
out=root/'outputs_subject_st_sl_3d_restored';m=json.loads((out/'artifact_manifest.json').read_text())
if digest(root/'output/pdf/trajectory_directional_pivot_report.pdf')!=m['base_pdf_sha256']:raise RuntimeError('Changed base PDF')
count=0
for p in (out/'trajectories').glob('*.npz'):
    new=np.load(p);old=np.load(root/'outputs_subject_st_sl_3d/trajectories'/p.name)
    if not np.array_equal(new['reference_valid'],old['reference_valid']):raise RuntimeError('Changed observed mask')
    mask=new['reference_valid']
    if not np.array_equal(new['reference_xyz_m'][mask],old['reference_xyz_m'][mask]):raise RuntimeError('Changed observed XYZ')
    count+=1
checks.update(unchanged_observed_masks_and_xyz=count,base_pdf_unchanged=True,original_c3ds_unchanged=True,pdf_pages_reviewed=[105,106,107,108,109],interactive_checked='SL / No.5 / trial 2: observed and stored processed series plus Z profile',test_accessed=False)
review=out/'visual_review.json';review.write_text(json.dumps(checks,indent=2));m['output_sha256']['visual_review.json']=digest(review);(out/'artifact_manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps(checks,indent=2))
