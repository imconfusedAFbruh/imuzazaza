"""No.8 PS TRAIN clock signals, unchanged v42 gate, no position objective."""
import json,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pipeline as p
from observed_reference_experiment import observed_markers
from observed_sync_experiment import observed_feature
from clock_alias_audit_v40 import evaluate

OUT=p.ROOT/'outputs_no8_clock_signals_v46'

def main():
    if OUT.exists():raise RuntimeError('Preserve output')
    OUT.mkdir();(OUT/'figures').mkdir()
    cfg=json.loads((p.ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings']
    gate=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/arbitration.json').read_text())['gate']
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    candidates=[q for q in csv.DictReader((p.ROOT/'outputs_clock_arbitrated_v42/clock_changes.csv').open()) if q['partition']=='train' and q['id'].endswith('No.8') and '__PS__' in q['id']]
    p.save_json(OUT/'protocol.json',dict(gate=gate,calibration='Same v7 sync_terms for both clocks',fixed_common_support='Native observed derivative and sensor support across both candidate basins +/-100ms',grid_step_s=.005,validation_accessed=False,test_accessed=False,position_used=False))
    records=[];curves=[];arrays={};saved=p.read_markers
    try:
        p.read_markers=observed_markers
        for q in candidates:
            row=inv[q['id']];assert row['partition']=='train'
            t,raw,iv=p.sample_streams(p.imu_streams(p.ROOT/row['imu']),cfg)
            gt=p.reference(p.ROOT/row['c3d'],cfg,row['setup']);rt=gt['t'];cal=cfg['sync_terms'][row['setup']]
            wheel=[raw[:,c['column']]*c['scale']+c['intercept'] for c in cal[:2]]
            old,new=float(q['old_offset_s']),float(q['new_offset_s']);lags=np.r_[old+np.arange(-.1,.1001,.005),new+np.arange(-.1,.1001,.005)]
            fig,axs=plt.subplots(2,2,figsize=(11,7));store=dict(native_c3d_time_s=rt)
            for j,(mode,imu,ref) in enumerate([('signed_yaw',raw[:,cal[2]['column']]*cal[2]['scale']+cal[2]['intercept'],gt['yaw']),('signed_speed',(wheel[0]+wheel[1])/2,gt['speed'])]):
                a=p.smooth_standard(imu,cfg['hz']);b,bm=observed_feature(ref,gt['derivative_valid'],gt['hz']);common=bm.copy()
                for lag in lags:
                    _,ok=p.masked_interp(rt+lag,t,a,iv);common &=ok
                threshold=.025 if mode=='signed_yaw' else .03
                physical_sd=float(np.std(ref[common]));identifiable=physical_sd>=threshold
                r=dict(id=q['id'],channel=mode,old_offset_s=old,new_offset_s=new,delta_s=new-old,common_frames=int(common.sum()),physical_reference_sd=physical_sd,identifiable=identifiable,
                       exact_existing_rule='retain_v9_small_update' if abs(new-old)<=gate['large_threshold_s'] else 'large_update_gate')
                scores=[]
                for k,lag in enumerate(lags):
                    c,n,x,good=evaluate(t,a,iv,rt,b,common,lag);scores.append(c if c is not None else np.nan)
                    curves.append(dict(id=q['id'],channel=mode,basin='old' if k<41 else 'new',offset_s=float(lag),correlation=c,frames=n))
                for name,lag in [('old',old),('new',new)]:
                    c,n,x,good=evaluate(t,a,iv,rt,b,common,lag);r[name+'_correlation']=c
                    axs[j,0].plot(rt,np.where(good,x,np.nan),label=name+' IMU')
                    # Same common support, physical (unstandardized) braking derivative.
                    xp,xv=p.masked_interp(rt+lag,t,imu,iv);der=np.gradient(xp,rt);support=common & xv
                    rr=np.gradient(ref,rt);inds=np.flatnonzero(support&np.isfinite(der)&np.isfinite(rr))
                    if mode=='signed_speed' and len(inds):
                        ri=inds[np.argmin(rr[inds])];ii=inds[np.argmin(der[inds])]
                        r[name+'_strongest_braking_s']=float(rt[ii]);r['reference_strongest_braking_s']=float(rt[ri]);r[name+'_braking_residual_s']=float(rt[ii]-rt[ri])
                    store[mode+'_'+name+'_standard']=x
                r['correlation_gain']=r['new_correlation']-r['old_correlation'];records.append(r)
                axs[j,0].plot(rt,np.where(common,b,np.nan),'k',label='observed C3D');axs[j,0].set_title(mode+' standardized signals');axs[j,0].legend(fontsize=7)
                axs[j,1].plot(lags[:41],scores[:41],label='old basin');axs[j,1].plot(lags[41:],scores[41:],label='new basin');axs[j,1].axvline(old,color='C0',ls=':');axs[j,1].axvline(new,color='C1',ls=':');axs[j,1].legend(fontsize=7);axs[j,1].set_title('Fixed-support correlation (diagnostic only)')
                store[mode+'_reference_standard']=b;store[mode+'_common_valid']=common
            for ax in axs.ravel():ax.grid(alpha=.2)
            fig.suptitle(q['id']+'; existing rule retains new, small shift',fontsize=10);fig.tight_layout();fig.savefig(OUT/'figures'/(q['id']+'.png'),dpi=140);plt.close(fig)
            np.savez_compressed(OUT/(q['id']+'.npz'),**store)
    finally:p.read_markers=saved
    p.write_csv(OUT/'channels.csv',records);p.write_csv(OUT/'basin_curves.csv',curves)
    p.save_json(OUT/'run.json',dict(records=records,validation_accessed=False,test_accessed=False,position_used=False,source_sha256=p.digest(Path(__file__))))
    lines=['# No.8 PS clock signal audit v46','','Existing v42 gate automatically retains accepted updates <=250ms. All three No.8 PS updates meet this rule. This audit does NOT override that frozen rule or select offsets from trajectory error. Same v7 calibration, signed speed and signed yaw, identical native derivative/sensor support across both +/-100ms diagnostic basins.','', '| Trial | Channel | Shift ms | Frames | Reference SD | Old corr | New corr | Gain |','|---|---|---:|---:|---:|---:|---:|---:|']
    lines.extend(f'| {r["id"]} | {r["channel"]} | {r["delta_s"]*1000:+.3f} | {r["common_frames"]} | {r["physical_reference_sd"]:.5f} | {r["old_correlation"]:.6f} | {r["new_correlation"]:.6f} | {r["correlation_gain"]:+.6f} |' for r in records)
    lines+=['','The large-update correlation gate would require gain >=.025 to >=.6 and no other informative channel regression >.025, plus independent short-trial event support. Correlation and strongest braking event are diagnostics, not absolute time accuracy. Strongest event can change identity; no ordinal assertion is made. Signed speed uses inherited empirical scale/axis; sensor units remain unverified.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(records,indent=2))

if __name__=='__main__':main()
