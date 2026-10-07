"""Refresh visualization markup without rereading or changing trajectory arrays."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
visual=Path('C:/Users/poon1/.codex/visualizations/2026/10/02/01a0fdfe-26f7-7b80-9bc3-f59af6a526e3/slope-trajectories-3d.html')
old=visual.read_text(encoding='utf-8');start=old.index('<script type="application/json" id="slope-plot-data">')+len('<script type="application/json" id="slope-plot-data">');end=old.index('</script>',start)
data=old[start:end];records=json.loads(data);subject=any(r['condition']=='SL' for r in records);restore=any(r.get('processed_n',0)>0 for r in records)
fragment=(root/'slope-3d-template.html').read_text(encoding='utf-8').replace('__SLOPE_DATA__',data)
if subject:fragment=fragment.replace('Measured slope trajectories in 3D','Subject ST / SL trajectories in 3D' if restore else 'Measured subject ST / SL trajectories in 3D').replace('training recordings','subject validation recordings').replace("r.condition==='SlopeF'","r.condition==='ST'")
visual.write_text(fragment,encoding='utf-8')
folder='outputs_subject_st_sl_3d_restored' if subject and restore else 'outputs_subject_st_sl_3d' if subject else 'outputs_slope_3d'
path=root/folder/'artifact_manifest.json';manifest=json.loads(path.read_text());manifest['visual_sha256']=hashlib.sha256(visual.read_bytes()).hexdigest();path.write_text(json.dumps(manifest,indent=2))
