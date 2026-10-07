"""Training-only raw gyro/acceleration-phase scale check; encoding not certified."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import json,time,csv,collections
from pathlib import Path
import numpy as np
from pipeline import ROOT,digest,save_json,write_csv,robust_line
from wheel_phase_experiment_v37 import phase_proxy
OUT=ROOT/'outputs_imu_units_v42'
def main():
    start=time.perf_counter()
    if OUT.exists():raise RuntimeError('Preserve audit')
    OUT.mkdir();parent=ROOT/'outputs_motion_endpoint_v16';manifest=json.loads((parent/'artifact_manifest.json').read_text())['sha256'];cal=json.loads((ROOT/'outputs_amended_v2/calibration.json').read_text());data={};native_rows=[];wave_samples={}
    save_json(OUT/'protocol.json',dict(question='Is rawwheelgyro/accelerometerphase slope compatible with nominal70mdps/registercount?',scope='All473acceptedtraining only; gyro-axis choice and empiricalacc normalization inherited from optical-trained calibration. Phasefit itself uses noC3D target and no wheelradius.',gate='Samev37 amplitudequality>.5,.3<absphaseangularrate<20rad/s; subsampleevery10qualifyingframes. No rawwheelvelocity gate to avoid selectingonC3D-scaledspeed.',fit='Robustlinear phaseangularrate vsrawselectedgyrocsvfield, perdate/side, independentintercept; inference notpromoted.',nominal_rad_s_per_register_count=.070*np.pi/180,caveat='Phasefiltered4Hz, derivative.51s; wheelmount/leverarm/centrifugal/tilt/translation contamination; highcorrelation cannotproveCSVencoding or actualhardwareODR.'))
    for i,p in enumerate(sorted((parent/'prepared_training').glob('*.npz'))):
        meta=p.with_suffix('.json')
        for f in (p,meta):assert digest(f)==manifest[str(f.relative_to(parent))]
        r=json.loads(meta.read_text())['row'];assert r['partition']=='train'
        with np.load(p) as z:d={k:z[k] for k in ['t','raw','imu_valid']}
        pp=phase_proxy(d,cal[r['setup']])
        for side,q in enumerate(pp):
            term=cal[r['setup']]['terms'][side];mask=d['imu_valid']&(q['quality']>.5)&(abs(q['rate'])>.3)&(abs(q['rate'])<20);ix=np.flatnonzero(mask)[::10];key=(r['setup'],side)
            if len(ix):data.setdefault(key,[]).append((d['raw'][ix,term['column']],q['rate'][ix]));wave_samples.setdefault(key,[]).append(dict(id=r['id'],samples=len(ix)))
        # Actualdevice timestamp distribution on473train acquisition files only.
        file=ROOT/r['imu'];raw=np.loadtxt(file,delimiter=',',skiprows=1,usecols=(1,2,3,5,6,7,8,9,10),converters={1:lambda x:{'L':0,'R':1,'C':2}[x.decode() if isinstance(x,bytes) else x]})
        for side in range(3):
            s=raw[raw[:,0]==side];dt=np.diff(s[:,2]);contiguous=np.diff(s[:,1])==1;dc=dt[contiguous];vec=s[:,3:9];native_rows.append(dict(id=r['id'],setup=r['setup'],sensor='LRC'[side],samples=len(s),integer_raw_fraction=float((vec==np.round(vec)).mean()),median_accel_norm=float(np.median(np.linalg.norm(vec[:,:3],axis=1))),min_raw=float(vec.min()),max_raw=float(vec.max()),raw_equal_32767_or_negative32768_fraction=float(((vec==32767)|(vec==-32768)).mean()),contiguous_samples=len(dc),fraction_9765us=float((dc==9765).mean()),fraction_9766us=float((dc==9766).mean()),mean_contiguous_dt_us=float(dc.mean()),median_dt_us=float(np.median(dc)),nonpositive_dt=int((dt<=0).sum()),identical6vector_fraction=float(np.all(np.diff(vec,axis=0)==0,axis=1).mean()),identicalgyro3_fraction=float(np.all(np.diff(vec[:,3:],axis=0)==0,axis=1).mean())))
        if (i+1)%100==0:print('Unit/phase audit',i+1,flush=True)
    results=[];nom=.070*np.pi/180
    for (setup,side),pairs in sorted(data.items()):
        x,y=map(np.concatenate,zip(*pairs));f=robust_line(x,y);beta=f['scale'];pred=x*beta+f['intercept'];results.append(dict(setup=setup,sensor='LR'[side],gyroaxis=cal[setup]['terms'][side]['axis'],samples=len(x),phase_rad_s_per_csv_unit=beta,phase_deg_s_per_csv_unit=beta*180/np.pi,absolute_nominal70mdps_ratio=abs(beta)/nom,counts_per_rad_s=1/abs(beta),phase_intercept_rad_s=f['intercept'],rawgyro_phase_correlation=float(np.corrcoef(x,y)[0,1]),residual_rmse_rad_s=float(np.sqrt(np.mean((pred-y)**2))),empirical_gravity_counts=cal[setup]['accel_counts_per_g'][side],phase_mapping_source='DirectrawCSVgyro→angularphase, no wheel radius or C3Dtarget'))
    write_csv(OUT/'phase_units.csv',results);write_csv(OUT/'native_fields_timing.csv',native_rows)
    c=[r['empirical_gravity_counts'] for r in results];ratios=[r['absolute_nominal70mdps_ratio'] for r in results];summary=dict(training_records=473,phase_units=results,nominal70mdps_rad_s_per_count=nom,nominal2g_register_counts_per_g=1/.000061,accel_empirical_counts_range=[min(c),max(c)],phase_nominal_ratio_range=[min(ratios),max(ratios)],all_native_fields_integer=all(r['integer_raw_fraction']==1 for r in native_rows),native_contiguous_dt_mean_range_us=[min(r['mean_contiguous_dt_us'] for r in native_rows),max(r['mean_contiguous_dt_us'] for r in native_rows)],minimum_fraction_9765_or9766=min(r['fraction_9765us']+r['fraction_9766us'] for r in native_rows),nonpositive_timestamp_diffs=sum(r['nonpositive_dt'] for r in native_rows),actual_odr_verified=False,csv_encoding_verified=False,test_accessed=False,validation_accessed=False,runtime_seconds=time.perf_counter()-start,source_sha256=digest(Path(__file__)))
    save_json(OUT/'run.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
