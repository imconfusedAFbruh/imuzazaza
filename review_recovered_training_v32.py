"""Artifact consistency checks and contact sheets for rendered PDF inspection."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from PIL import Image,ImageOps,ImageDraw
root=Path(__file__).resolve().parent;out=root/'outputs_recovered_training_v32';tmp=root/'tmp/pdfs/recovered_training_v32';manifest=json.loads((out/'artifact_manifest.json').read_text())
for name,sha in manifest['sha256'].items():
    if hashlib.sha256((out/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('Changed artifact '+name)
run=json.loads((out/'run.json').read_text())
for name,sha in run['source_sha256'].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('Changed source '+name)
split=json.loads((root/'outputs_amended_v2/split.json').read_text())['assignments'];inventory={r['id']:r for r in json.loads((root/'outputs_amended_v2/inventory.json').read_text())}
train=list(csv.DictReader((out/'training_recovery_audit.csv').open(newline='')));val=list(csv.DictReader((out/'original_v21_trials.csv').open(newline='')))
assert len(train)==473 and len(val)==71
assert {r['participant'] for r in train}.isdisjoint({r['participant'] for r in val})
assert all(r['partition']=='train' for r in train)
assert all(split[r['participant']]=='validation' for r in val)
for name in ['stored_endpoints','stored_endpoints_and_rates']:
    ids=json.loads((out/(name+'_model.json')).read_text())['training_ids'];assert set(ids)=={r['id'] for r in train}
for r in val:
    with np.load(out/'trajectories'/(r['id']+'.npz')) as z,np.load(root/'outputs_observed_reference_v7/cache'/(r['id']+'.npz')) as source:
        assert np.array_equal(z['reference_valid'],source['gt_valid'])
        assert np.array_equal(z['reference_xy_m'],source['gt_xy'],equal_nan=True)
        assert np.array_equal(z['reference_heading_rad'],source['gt_heading'],equal_nan=True)
files=sorted(tmp.glob('all-review-*.png'))
assert len(files)==82
for start in range(0,len(files),9):
    sheet=Image.new('RGB',(1600,1740),'white');draw=ImageDraw.Draw(sheet)
    for i,path in enumerate(files[start:start+9]):
        image=Image.open(path).convert('RGB');image.thumbnail((520,540));x=(i%3)*533;y=(i//3)*580;draw.text((x+8,y+4),'PDF page '+path.stem.split('-')[-1],fill='black');sheet.paste(image,(x+(533-image.width)//2,y+30))
    sheet.save(tmp/f'contact-{start//9+1}.png')
report=dict(training_trials=473,earlier_trials=266,target_training_trials=207,validation_trials=71,identical_observed_reference_masks_and_targets=True,participant_overlap=False,both_refits_use_all_473_training_ids=True,original_v21_reproduced_to_m_tolerance=1e-8,test_accessed=False,rendered_pdf_pages=82,contact_sheets=10)
file=out/'artifact_review.json';file.write_text(json.dumps(report,indent=2));manifest['sha256'][file.name]=hashlib.sha256(file.read_bytes()).hexdigest();manifest['report_source_sha256']=hashlib.sha256((root/'report_recovered_training_v32.py').read_bytes()).hexdigest();(out/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(report,indent=2))
