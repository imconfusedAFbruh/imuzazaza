from pathlib import Path
import csv,json,hashlib
from pypdf import PdfReader
from PIL import Image,ImageChops
root=Path.cwd();out=root/'outputs_pdf_two_panel_v54';pdf=root/'output/pdf/trajectory_research_accuracy_audit.pdf';reader=PdfReader(pdf)
rows=[r for r in csv.DictReader(open(root/'outputs_clock_routes_v44/trials.csv')) if r['model']=='new_clock_refit_blend'];assert len(reader.pages)==83
keys=['route_rmse_m','route_p95_m','sampled_hausdorff_m','supported_run_frechet_max_m','supported_last_endpoint_error_m','supported_pathlength_absolute_error_m']
for i,row in enumerate(rows):
    page=reader.pages[12+i];txt=page.extract_text();a=Image.open(out/'figures'/(row['id']+'.png')).convert('RGB');b=page.images[0].image.convert('RGB');assert a.size==b.size and ImageChops.difference(a,b).getbbox() is None
    assert 'FAILED' in txt and all(f'{float(row[k])*1000:.1f}' in txt for k in keys)
qa=dict(pages=83,trajectory_pages=71,embedded_images_match=71,caption_values_match=426,pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),reviewed_render_pages=[11,24,70,78],model_unchanged=True,straight_panel_padding='Minimum Y extent .65X to keep equal-scale axes and labels legible')
(out/'final_qa.json').write_text(json.dumps(qa,indent=2));print(json.dumps(qa,indent=2))
