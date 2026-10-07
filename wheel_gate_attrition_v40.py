"""Read-only unchanged IMU gate over native recording; optical checks diagnostic only."""
import json,csv,time
from pathlib import Path
import numpy as np
from scipy.ndimage import uniform_filter1d
from pipeline import ROOT,imu_streams,sample_streams,runs,write_csv,save_json,digest
OUT=ROOT/'outputs_wheel_gate_v40'
def read(p):return json.loads(p.read_text())
def longest(mask):return max((b-a for a,b in runs(mask)),default=0)/100
def accepted(mask):
    out=np.zeros(len(mask),bool)
    for a,b in runs(mask):
        if b-a>=100:out[a:b]=True
    return out
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve audit')
    OUT.mkdir();cfg=read(ROOT/'outputs_observed_reference_v7/run.json')['settings'];ss=read(ROOT/'outputs_wheel_bias_v39/startup_states.json')['records'];ss=[s for s in ss if s['held']]+read(ROOT/'outputs_wheel_bias_v39/validation_startup_states.json')['records'];inv={r['id']:r for r in read(ROOT/'outputs_amended_v2/inventory.json')};old={r['id']:r for r in read(ROOT/'outputs_stationary_gravity_v14/initialization.json')['records']};records=[];windows=[]
    save_json(OUT/'protocol.json',dict(scope='Read-only timing/stationarity gate attrition; no gate thresholds selected/changed and no estimator fit',imu_gate='Exact v14 first5s criterion plus same criterion anywhereafter5s:wheel<.05,center3gyro<.1,accSD<.02,minimum1s; native valid, windowboundariesexcluded',optical='Frozen observed derivative cache used only AFTER IMU classifications for descriptive stationary audit:absforward<.03 andabsyaw<.03. No optical gates/tuning.',caveat='Date/fold empirical gyroisotropy andgravity scale notSIverified; nativePCclock andexistingIMUC3Doffset inherited. Observed derivative subset coverage stated.',test_accessed=False))
    for i,s in enumerate(ss):
        r=inv[s['id']];fold=s.get('fold');path=ROOT/f'outputs_calibration_fold_v37/fold_{fold}_calibration.json' if fold is not None else ROOT/'outputs_calibration_fold_v37/all473_observed_calibration.json';c=read(path)[r['setup']];streams=imu_streams(ROOT/r['imu']);t,raw,valid=sample_streams(streams,cfg);rel=t-t[0];a=raw[:,12:15]/c['accel_counts_per_g'][2];gyro=(raw[:,15:18]-c['gyro_bias_counts'][2])*abs(c['terms'][2]['scale']);wheel=np.c_[*[raw[:,q['column']]*q['scale']+q['intercept'] for q in c['terms'][:2]]];sd=np.sqrt(np.maximum(uniform_filter1d(a**2,101,axis=0)-uniform_filter1d(a,101,axis=0)**2,0));wf=np.max(np.abs(wheel),1)<.05;gf=np.linalg.norm(gyro,axis=1)<.1;af=np.max(sd,1)<.02;gate=wf&gf&af&valid;gate[:50]=False;gate[-50:]=False;pre=rel<=5.;post=rel>5.
        # First5 window has its own right boundary, exactly as production.
        ids=np.flatnonzero(pre);firstgate=gate.copy();firstgate[~pre]=False;firstgate[ids[-50:]]=False;firstq=accepted(firstgate);latergate=gate&post;laterq=accepted(latergate)
        cp=ROOT/'outputs_observed_reference_v7/cache'/f"{r['id']}.npz";mp=cp.with_suffix('.json');meta=read(mp)
        with np.load(cp) as z:d={k:z[k] for k in ['t','ref_t','gt_v','gt_yaw','label_valid']}
        absolute=d['t']+d['ref_t'][0]+meta['synchronization']['offset_s'];index=np.clip(np.searchsorted(absolute,t),1,len(absolute)-1);left=index-1;index=np.where(abs(absolute[index]-t)<abs(absolute[left]-t),index,left);supported=(abs(absolute[index]-t)<.006)&d['label_valid'][index];optquiet=(abs(d['gt_v'][index])<.03)&(abs(d['gt_yaw'][index])<.03)&supported
        firstsupports=pre&supported;stationaryfirst=pre&optquiet;classification=(firstq|laterq)&supported
        item=dict(id=r['id'],partition='heldtrain' if fold is not None else 'validation',participant=r['participant'],date=r['date'],condition=r['condition'],old_v14_startup_eligible=old[r['id']]['eligible'],new_startup_eligible=s['eligible'],native_shared_start_offset_s=float(max(z['t'][0] for z in streams)-min(z['t'][0] for z in streams)),native_duration_s=float(rel[-1]),native_first5_valid_fraction=float(valid[pre].mean()),first5_wheel_fraction=float(wf[pre].mean()),first5_gyro_fraction=float(gf[pre].mean()),first5_accSD_fraction=float(af[pre].mean()),first5_combined_fraction=float((wf&gf&af&valid)[pre].mean()),first5_longest_s=longest(firstgate),later_has_quiet=bool(laterq.any()),later_quiet_s=float(laterq.sum()/100),later_longest_s=longest(latergate),first5_observed_derivative_samples=int(firstsupports.sum()),first5_optical_stationary_samples=int(stationaryfirst.sum()),first5_optical_stationary_fraction=float(stationaryfirst.sum()/firstsupports.sum()) if firstsupports.any() else '',first5_optquiet_accSD_median=float(np.median(np.max(sd,1)[stationaryfirst])) if stationaryfirst.any() else '',first5_optquiet_gyro_norm_median=float(np.median(np.linalg.norm(gyro,axis=1)[stationaryfirst])) if stationaryfirst.any() else '',classified_quiet_supported_samples=int(classification.sum()),classified_quiet_optical_stationary_fraction=float(optquiet[classification].mean()) if classification.any() else '')
        records.append(item)
        for begin,end in runs(firstq|laterq):windows.append(dict(id=r['id'],partition=item['partition'],start_native_s=float(rel[begin]),end_native_s=float(rel[end-1]),duration_s=(end-begin)/100,observed_samples=int(supported[begin:end].sum()),optical_stationary_fraction=float(optquiet[begin:end].sum()/supported[begin:end].sum()) if supported[begin:end].any() else ''))
        if (i+1)%100==0:print('Gate audit',i+1,flush=True)
    write_csv(OUT/'gate_trials.csv',records);write_csv(OUT/'quiet_windows.csv',windows);summary={}
    for partition in ('heldtrain','validation'):
        rr=[r for r in records if r['partition']==partition];summary[partition]=dict(records=len(rr),old_startup_eligible=sum(r['old_v14_startup_eligible'] for r in rr),new_startup_eligible=sum(r['new_startup_eligible'] for r in rr),later_quiet_records=sum(r['later_has_quiet'] for r in rr),median_shared_start_offset_s=float(np.median([r['native_shared_start_offset_s'] for r in rr])),median_native_first5_valid_fraction=float(np.median([r['native_first5_valid_fraction'] for r in rr])),first5_optical_supported_records=sum(r['first5_observed_derivative_samples']>0 for r in rr),first5_optical_stationary_records=sum(r['first5_optical_stationary_samples']>=100 for r in rr),median_first5_optquiet_accSD=float(np.median([r['first5_optquiet_accSD_median'] for r in rr if r['first5_optquiet_accSD_median']!=''])),median_first5_optquiet_gyro_norm=float(np.median([r['first5_optquiet_gyro_norm_median'] for r in rr if r['first5_optquiet_gyro_norm_median']!=''])))
    groups=[]
    for field in ('date','condition'):
        for group in sorted({r[field] for r in records}):
            rr=[r for r in records if r[field]==group];groups.append(dict(field=field,group=group,records=len(rr),new_startup_eligible=sum(r['new_startup_eligible'] for r in rr),old_startup_eligible=sum(r['old_v14_startup_eligible'] for r in rr),later_quiet_records=sum(r['later_has_quiet'] for r in rr),mean_first5_wheel_fraction=float(np.mean([r['first5_wheel_fraction'] for r in rr])),mean_first5_gyro_fraction=float(np.mean([r['first5_gyro_fraction'] for r in rr])),mean_first5_accSD_fraction=float(np.mean([r['first5_accSD_fraction'] for r in rr]))))
    write_csv(OUT/'gate_groups.csv',groups);save_json(OUT/'run.json',dict(summary=summary,records=278,test_accessed=False,thresholds_changed=False,runtime_seconds=time.perf_counter()-start,source_sha256=digest(Path(__file__))));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
