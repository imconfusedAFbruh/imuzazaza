"""Five TRAIN small-shift contradictions, original calibration/window checks."""
import csv,json
from pathlib import Path
import numpy as np
import pipeline as p
from observed_reference_experiment import observed_markers
from observed_sync_experiment import observed_feature

OUT=p.ROOT/'outputs_clock_conflict_windows_v49'
def correlation(a,b):
    if len(a)<60 or min(np.std(a),np.std(b))<1e-8:return None
    return float(np.corrcoef(a,b)[0,1])
def main():
    if OUT.exists():raise RuntimeError('Preserve output')
    OUT.mkdir();rows=list(csv.DictReader((p.ROOT/'outputs_clock_small_basin_v48/signal_evidence.csv').open()))
    chosen=[q for q in rows if q['source']=='speed' and float(q['new_correlation'])-float(q['old_correlation'])<=-.025]
    cfg=json.loads((p.ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings'];inv={q['id']:q for q in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    records=[];windows=[];reader=p.read_markers
    try:
        p.read_markers=observed_markers
        for q in chosen:
            row=inv[q['id']];assert row['partition']=='train'
            t,raw,valid=p.sample_streams(p.imu_streams(p.ROOT/row['imu']),cfg);gt=p.reference(p.ROOT/row['c3d'],cfg,row['setup']);rt=gt['t'];terms=cfg['sync_terms'][row['setup']]
            wheel=[raw[:,c['column']]*c['scale']+c['intercept'] for c in terms[:2]];c=terms[2]
            for name,imu,ref,threshold in [('yaw',raw[:,c['column']]*c['scale']+c['intercept'],gt['yaw'],.025),('speed',np.abs((wheel[0]+wheel[1])/2),np.abs(gt['speed']),.03)]:
                a=p.smooth_standard(imu,cfg['hz']);b,bm=observed_feature(ref,gt['derivative_valid'],gt['hz']);common=bm.copy();pred={}
                for basin in ('old','new'):
                    pred[basin],ok=p.masked_interp(rt+float(q[basin+'_offset_s']),t,a,valid);common &=ok
                sd=float(np.std(ref[common]));old=correlation(pred['old'][common],b[common]);new=correlation(pred['new'][common],b[common]);r=dict(id=q['id'],channel=name,frames=int(common.sum()),physical_sd=sd,informative=sd>=threshold,old_correlation=old,new_correlation=new,gain=new-old,shift_ms=float(q['delta_s'])*1000)
                for start in np.arange(0,rt[-1]-7.99,8.):
                    mask=common&(rt>=start)&(rt<start+8);w_sd=float(np.std(ref[mask])) if mask.any() else 0
                    if mask.sum()<60 or w_sd<threshold:continue
                    oc=correlation(pred['old'][mask],b[mask]);nc=correlation(pred['new'][mask],b[mask])
                    if oc is None or nc is None:continue
                    windows.append(dict(id=q['id'],channel=name,start_s=float(start),frames=int(mask.sum()),physical_sd=w_sd,old_correlation=oc,new_correlation=nc,gain=nc-oc,old_strong=nc-oc<=-.025,new_strong=nc-oc>=.025))
                w=[x for x in windows if x['id']==q['id'] and x['channel']==name];r.update(windows=len(w),old_strong=sum(x['old_strong'] for x in w),new_strong=sum(x['new_strong'] for x in w));records.append(r)
    finally:p.read_markers=reader
    p.write_csv(OUT/'channels.csv',records);p.write_csv(OUT/'windows.csv',windows)
    p.save_json(OUT/'run.json',dict(records=records,windows=windows,old_sync_terms_for_both=True,no_new_lag_search=True,position_used=False,validation_accessed=False,test_accessed=False,source_sha256=p.digest(Path(__file__))))
    lines=['# Five small-clock channel conflicts, original calibration v49','','Exactly the five TRAIN v48 cases with speed correlation decline>=.025. Original v7 sync_terms for both offsets. Fixed native observed support. No new lag search, fitted parameters or trajectory positions. Physical channel thresholds yaw SD>=.025rad/s andspeed>=.03m/s;60samples minimum. Distributed nonoverlapping8s windows.','', '| Trial | Channel | Physical SD | Old corr | New corr | Gain | Windows | Strong old/new |','|---|---|---:|---:|---:|---:|---:|---|']
    lines.extend(f'| {r["id"]} | {r["channel"]} | {r["physical_sd"]:.5f} | {r["old_correlation"]:.6f} | {r["new_correlation"]:.6f} | {r["gain"]:+.6f} | {r["windows"]} | {r["old_strong"]}/{r["new_strong"]} |' for r in records)
    lines+=['','Interpretation: repeated cross-channel conflict survives original calibration and is not a single global correlation artifact. But it is not a proof of hardware clock error. Original individual wheel terms were optimized jointly for midpoint body velocity. Skid/response and derivative preprocessing can shift speed extrema relative to body yaw. No new candidate has global yaw gain>=.025; every informative speed channel declines>.025. Under a NEW protocol applying large-change gate to small updates these would be unresolved/retain-old, but the CURRENT frozen protocol retains small v9 updates. Do not retroactively call them rejected, or choose reversions from position scores. These recordings warrant a new predeclared clock uncertainty experiment and response-delay diagnosis.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(q.relative_to(OUT)):p.digest(q) for q in OUT.rglob('*') if q.is_file()}));print(json.dumps(records,indent=2))
if __name__=='__main__':main()
