"""Cache exact sensors for held conditional folds without another model fit."""
import json,time
from pathlib import Path
import numpy as np
import pipeline as p

OUT=p.ROOT/'outputs_clock_sensor_cache_v40';FOLDS=p.ROOT/'outputs_clock_folds_v39'
def main():
    started=time.perf_counter()
    if (OUT/'run.json').exists() or (OUT/'artifact_manifest.json').exists():raise RuntimeError('Preserve sealed cache')
    manifest=json.loads((FOLDS/'artifact_manifest.json').read_text())['sha256'];protocol=json.loads((FOLDS/'protocol.json').read_text());fallback=set(protocol['fallback_ids'])
    OUT.mkdir(exist_ok=True);(OUT/'sensors').mkdir(exist_ok=True);rows=[]
    for path in sorted((FOLDS/'common_trajectories').glob('*.npz')):
        if p.digest(path)!=manifest[str(path.relative_to(FOLDS))]:raise RuntimeError('Changed foldmotion:'+path.stem)
        with np.load(path) as z:times=z['native_c3d_time_s'];arrays=dict(native_c3d_time_s=times,common_imu_valid=z['imu_valid'])
        for prefix,source in [('old',p.ROOT/'outputs_observed_reference_v7'),('new',p.ROOT/('outputs_observed_reference_v7' if path.stem in fallback else 'outputs_observed_sync_v9'))]:
            f=source/'cache'/path.name;sm=json.loads((source/'artifact_manifest.json').read_text())['sha256']
            if p.digest(f)!=sm[str(f.relative_to(source))]:raise RuntimeError('Changed source:'+path.stem)
            with np.load(f) as z:
                # Sensor-only cache deliberately omits all optical targets.
                arrays[prefix+'_setup']=z['setup'];arrays[prefix+'_time_s']=z['t'];arrays[prefix+'_ref_t']=z['ref_t'];arrays[prefix+'_raw']=z['raw'];arrays[prefix+'_imu_valid']=z['imu_valid']
                channels=[];valid=np.ones(len(times),bool)
                for j in range(18):
                    values,good=p.masked_interp(times,z['ref_t'],z['raw'][:,j],z['imu_valid']);channels.append(values);valid &=good
                arrays[prefix+'_common_raw']=np.column_stack(channels);arrays[prefix+'_common_imu_valid']=valid
        np.savez_compressed(OUT/'sensors'/path.name,**arrays);rows.append(dict(id=path.stem,common_frames=len(times),new_clock_fallback=path.stem in fallback))
    p.write_csv(OUT/'records.csv',rows);p.save_json(OUT/'run.json',dict(held_training_recordings=len(rows),test_accessed=False,validation_accessed=False,sensor_cache_contains_reference_targets=False,
          motion_reference_source=str(FOLDS.relative_to(p.ROOT)),motion_manifest_sha256=p.digest(FOLDS/'artifact_manifest.json'),runtime_seconds=time.perf_counter()-started,source_sha256=p.digest(Path(__file__))))
    (OUT/'report.md').write_text('# Fold sensor cache v40\n\nExactold/new IMUraw/time/ref_t/valid pluscommon-nativesensorinterpolation retained for eachheldtrainingrecord. Reference targets andfoldmotion live separately inoutputs_clock_folds_v39/common_trajectories; thiscachecontains noopticaltargets. ref_t is evaluativesynchronizationmetadata, not available withoutC3D. Downstreaminferencefeatures must useIMU time/values only. No modelsrefit, no validation/test. Native-first5s startup precedes theseopticaloverlap crops; consultsealedstartupstates ororiginalCSV whenneeded.\n',encoding='utf-8')
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print('Cached',len(rows),flush=True)

if __name__=='__main__':main()
