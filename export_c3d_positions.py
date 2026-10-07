"""Recover full stored XYZ for display while preserving observation provenance."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
import ezc3d
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs_c3d_recovery';(OUT/'full_xyz_csv').mkdir(parents=True,exist_ok=True)
inventory={r['id']:r for r in json.loads((ROOT/'outputs_amended_v2/inventory.json').read_text())}
audit=list(csv.DictReader((OUT/'native_audit.csv').open(newline='',encoding='utf-8')))
cfg=json.loads((ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings'];hashes={};records=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for ar in audit:
    row=inventory[ar['id']];assert row['partition']=='validation';path=ROOT/row['c3d'];sha=digest(path)
    meta=json.loads((ROOT/'outputs_observed_reference_v7/cache'/(row['id']+'.json')).read_text())
    if sha!=meta['signature']['c3d_sha256']:raise RuntimeError('Changed original C3D')
    hashes[row['c3d']]=sha;c=ezc3d.c3d(str(path));p=c['parameters']['POINT'];labels=[x.strip() for x in p['LABELS']['value']];ids=[labels.index(x) for x in ['L_FAL','R_FAL']]
    scale={'mm':.001,'cm':.01,'m':1}[p['UNITS']['value'][0].strip().lower()];xyz=c['data']['points'][:3,ids,:].transpose(2,1,0)*scale;res=c['data']['meta_points']['residuals'][0,ids,:].T
    stored=np.isfinite(xyz).all(2)&(np.linalg.norm(xyz,axis=2)>1e-8)&(res>=0);observed=stored&(res>0);support=np.zeros_like(observed);masks=c['data']['meta_points'].get('camera_masks');populated=False
    if masks is not None:
        support=np.asarray(masks)[:,ids,:].any(0).T;populated=bool(support.any())
        if populated:observed&=support
    sep=np.linalg.norm(xyz[:,0]-xyz[:,1],axis=1);policy=cfg['reference_geometry']['setups'][row['setup']];bands=np.zeros(len(xyz),bool)
    for band in policy['bands']:bands|=(sep>=band['lower_m'])&(sep<=band['upper_m'])
    midpoint=xyz.mean(1);pair_observed=observed.all(1);geometry=bands&(np.abs(sep-np.median(sep[pair_observed]))<=policy['rigidity_tolerance_m']);hz=float(c['header']['points']['frame_rate'])
    columns=['native_frame','time_s','L_x_m','L_y_m','L_z_m','R_x_m','R_y_m','R_z_m','midpoint_x_m','midpoint_y_m','midpoint_z_m','L_status','R_status','pair_status','L_residual_source_units','R_residual_source_units','L_camera_support','R_camera_support','existing_geometry_gate']
    export=OUT/'full_xyz_csv'/(row['id']+'.csv')
    with export.open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(columns)
        for i in range(len(xyz)):
            statuses=['observed' if observed[i,j] else 'stored_processed' if stored[i,j] else 'unavailable' for j in range(2)]
            pair='observed' if pair_observed[i] else 'stored_processed' if stored[i].all() else 'unavailable'
            writer.writerow([int(c['header']['points']['first_frame'])+i,round(i/hz,6),*np.round(xyz[i].ravel(),8),*np.round(midpoint[i],8),*statuses,pair,*res[i],*support[i].astype(int),int(geometry[i])])
    records.append(dict(id=row['id'],frames=len(xyz),observed_frames=int(pair_observed.sum()),stored_processed_frames=int((stored.all(1)&~pair_observed).sum()),unavailable_frames=int((~stored.all(1)).sum()),geometry_excluded_frames=int((~geometry).sum()),export=str(export.relative_to(ROOT))))
summary=json.loads((OUT/'native_audit_summary.json').read_text());summary.update(dict(exports=len(records),newly_interpolated_frames=0,originals_modified=False,geometry_excluded_frames=sum(r['geometry_excluded_frames'] for r in records),records=records))
(OUT/'recovery_summary.json').write_text(json.dumps(summary,indent=2));(OUT/'README.md').write_text('''# C3D position recovery for display

All 71 accepted validation C3Ds already contain finite, nonnegative-residual left/right XYZ coordinates in every native frame. No original files were repaired or overwritten, and no new interpolation was applied. The visual gaps came from excluding stored processed coordinates from the observed-reference mask.

`full_xyz_csv/` exports the complete stored marker and midpoint positions in metres, native frame/time, original residuals, camera support, per-marker provenance, and the unchanged geometry gate. `observed` means positive residual plus camera support when populated; `stored_processed` is retained source XYZ that is not direct observed truth. The camera mask is optional. Negative residual would mean unavailable even when coordinates exist; none occurs in these accepted 71 files. A separate geometry flag remains available for plausibility filtering.

Processed positions may be displayed as dashed segments. They are not restored independent measurements and do not replace the frozen ground-truth masks or accuracy scores. This inspection excludes test data and excluded recordings. See research_docs/c3d-recovery-conventions.md for primary-source documentation.
''',encoding='utf-8')
(OUT/'artifact_manifest.json').write_text(json.dumps(dict(source_sha256=hashes,output_sha256={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}),indent=2));print(json.dumps({k:summary[k] for k in ['exports','frames','stored_frames','observed_frames','processed_frames','unavailable_frames','geometry_excluded_frames','newly_interpolated_frames','originals_modified']},indent=2))
