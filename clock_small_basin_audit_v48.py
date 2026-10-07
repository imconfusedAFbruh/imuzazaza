"""Adjudicate large old/v9 lag disagreements by fixed-support signal evidence.

No position metrics, no new lag search, training data only.
"""
import json,csv,time
from pathlib import Path
import numpy as np
import pipeline as p
from observed_reference_experiment import observed_markers
from observed_sync_experiment import observed_feature

OUT=p.ROOT/'outputs_clock_small_basin_v48'
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve audit')
    OUT.mkdir();changes=[q for q in csv.DictReader((p.ROOT/'outputs_clock_refit_v38/clock_changes.csv').open(newline='')) if q['partition']=='train' and 0.001<abs(float(q['offset_delta_s']))<=.25 and 'No.8' not in q['id']]
    inventory={q['id']:q for q in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())};cfg=json.loads((p.ROOT/'outputs_observed_sync_v9/run.json').read_text())['settings'];results=[]
    p.save_json(OUT/'protocol.json',dict(hypothesis='Small clock updates can also have conflicting speed and yaw evidence; screening TRAIN changes outside independently audited No8',minimum_shift_s=.001,maximum_shift_s=.25,excluded_participant='No.8 separately audited v46',
        candidates='Exactlyold/v9 offsets; no newlagsearch or positionobjective',support='Native C3D observedderivatives andnativeIMUvalidsupport identical forboth offsets',train_only=True,test_accessed=False))
    oldreader=p.read_markers
    try:
        p.read_markers=observed_markers
        for q in changes:
            row=inventory[q['id']];gt=p.reference(p.ROOT/row['c3d'],cfg,row['setup']);streams=p.imu_streams(p.ROOT/row['imu']);t,raw,valid=p.sample_streams(streams,cfg);terms=cfg['sync_terms'][row['setup']]
            wheel=[raw[:,c['column']]*c['scale']+c['intercept'] for c in terms[:2]];c=terms[2]
            for mode,imu,ref in [('signed_yaw',raw[:,c['column']]*c['scale']+c['intercept'],gt['yaw']),('speed',np.abs((wheel[0]+wheel[1])/2),np.abs(gt['speed']))]:
                a=p.smooth_standard(imu,cfg['hz']);b,rm=observed_feature(ref,gt['derivative_valid'],gt['hz']);sampled={};support=rm.copy()
                for name in ('old','new'):
                    lag=float(q[name+'_offset_s']);values,good=p.masked_interp(gt['t']+lag,t,a,valid);sampled[name]=values;support &=good
                if support.sum()<30 or np.std(b[support])<1e-8:oc=nc=None
                else:oc=float(np.corrcoef(sampled['old'][support],b[support])[0,1]);nc=float(np.corrcoef(sampled['new'][support],b[support])[0,1])
                results.append(dict(id=row['id'],condition=row['condition'],source=mode,old_offset_s=float(q['old_offset_s']),new_offset_s=float(q['new_offset_s']),delta_s=float(q['offset_delta_s']),common_observed_derivative_frames=int(support.sum()),old_correlation=oc,new_correlation=nc,
                    preferred='old' if oc is not None and oc>nc else 'new' if nc is not None else 'unidentifiable'))
    finally:p.read_markers=oldreader
    p.write_csv(OUT/'signal_evidence.csv',results);p.save_json(OUT/'run.json',dict(trials=len(changes),results=results,test_accessed=False,position_used=False,runtime_seconds=time.perf_counter()-start,source_sha256=p.digest(Path(__file__))))
    lines=['# Small clock-basin fixed-support screening v48','','Fixed support native observedderivative correlation for BOTH exactlyold andv9 offsets. No lag search or positionobjective, trainonly. Relative lagbasins can be audited without comparing unequalcoverage correlation scores. Equalperiodic route peaks still require uniqueevent/timecode evidence; preferredcorrelation alone is not physicaltimeaccuracy.','', '| Trial | Channel | Shift(s) | Frames | Oldcorr | Newcorr | Preference |','|---|---|---:|---:|---:|---:|---|']
    lines +=[f"| {q['id']} | {q['source']} | {q['delta_s']:+.4f} | {q['common_observed_derivative_frames']} | {q['old_correlation']} | {q['new_correlation']} | {q['preferred']} |" for q in results]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(results,indent=2),flush=True)

if __name__=='__main__':main()
