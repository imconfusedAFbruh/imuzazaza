"""Independent full-record projection/support audit; no synchronization search."""
import json
import numpy as np
from scipy.signal import butter,sosfiltfilt
import pipeline as p
from distributed_clock_candidates_v86 import load_inputs,SENSOR,SEEDS
from observed_sync_experiment import segment_peaks
from native_refit_v81 import OUT as FROZEN
from projected_clock_v108 import OUT as SOURCE
from basin_completeness_v91 import verify

OUT=p.ROOT/'outputs_projected_clock_review_v109'


def available(query,t):
    return (query>=t[0])&(query<=t[-1])


def main():
    assert np.array_equal(available(np.array([-1.,0,1,2,3]),np.array([0.,1,2])),[False,True,True,True,False])
    cfg,inv,baseline,models,hashes=load_inputs();hashes+=verify(SOURCE)+verify(FROZEN)
    new={r['id']:r for r in json.loads((SOURCE/'clocks.json').read_text())}
    assert set(new)=={r['id'] for r in baseline}
    OUT.mkdir(exist_ok=False);rows=[];rejected=[];max_error=0.
    for old in baseline:
        ident=old['id'];q=new[ident];r=inv[ident];assert r['partition']=='train' and old['accepted']==q['accepted']
        cal=models[str(old['fold'])]['calibration'][r['setup']]
        with np.load(SENSOR/'sensors'/(ident+'.npz')) as z:t=z['t'];raw=z['raw'];iv=z['imu_valid']
        assert iv.all() and np.allclose(np.diff(t),.01,atol=1e-9)
        accel=sosfiltfilt(butter(2,.3,fs=100,output='sos'),raw[:,12:15],axis=0)
        gravity=accel/np.maximum(np.linalg.norm(accel,axis=1,keepdims=True),1e-8)
        reconstructed=np.einsum('ij,ij->i',raw[:,15:18]-cal['gyro_bias_counts'][2],gravity)
        with np.load(SOURCE/'features'/(ident+'.npz')) as z:
            saved=z['projected_counts'];assert np.array_equal(z['t'],t) and np.array_equal(z['imu_valid'],iv)
        error=float(np.max(np.abs(saved-reconstructed)));assert error<1e-9;max_error=max(max_error,error)
        a,b=p.smooth_standard(raw[:,15],cfg['hz']),p.smooth_standard(saved,cfg['hz'])
        row=dict(id=ident,participant=r['participant'],condition=r['condition'],accepted=q['accepted'],
            normalized_feature_correlation=float(np.corrcoef(a,b)[0,1]),normalized_feature_rms=float(np.sqrt(np.mean((a-b)**2))),
            scalar_peaks=len(segment_peaks(abs(a),iv,cfg['hz'],cfg)),projected_peaks=len(segment_peaks(abs(b),iv,cfg['hz'],cfg)))
        if q['accepted']:
            with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:rt=z['native_c3d_time_s'];mask=z['imu_valid']&z['reference_valid']
            before=available(rt+old['offset_s'],t);after=available(rt+q['offset_s'],t)
            for lag,ok in ((old['offset_s'],before),(q['offset_s'],after)):
                _,shared=p.masked_interp(rt+lag,t,saved,iv);assert np.array_equal(ok,shared)
            lost=int((mask&~after).sum());assert lost==q['frozen_scored_lost']
            row.update(delta_vs_v84_s=q['offset_s']-old['offset_s'],baseline_lost=int((mask&~before).sum()),projection_lost=lost,
                newly_unsupported=int((mask&before&~after).sum()),restored=int((mask&~before&after).sum()),old_source=old['source'],new_source=q['source'])
        else:rejected.append(dict(id=ident,baseline=old.get('diagnostics'),projection=q.get('diagnostics')))
        rows.append(row)
    assert len(rows)==207 and sum(r['participant']=='No.20' for r in rows)==15
    p.write_csv(OUT/'trials.csv',rows);p.save_json(OUT/'rejections.json',rejected)
    delta=np.array([abs(r['delta_vs_v84_s']) for r in rows if r['accepted']])
    p.save_json(OUT/'protocol.json',dict(preregistration_sha256=p.digest(p.ROOT/'research_docs/projected_clock_review_v109.md'),
        parent_hashes_verified=hashes,source_sha256=p.digest(__file__),projection_max_error_counts=max_error))
    p.save_json(OUT/'run.json',dict(trials=207,accepted=199,rejected=8,acceptance_identity_exact=True,
        baseline_unsupported=sum(r.get('baseline_lost',0) for r in rows),projection_unsupported=sum(r.get('projection_lost',0) for r in rows),
        newly_unsupported=sum(r.get('newly_unsupported',0) for r in rows),restored=sum(r.get('restored',0) for r in rows),
        median_abs_offset_delta_s=float(np.median(delta)),max_abs_offset_delta_s=float(delta.max()),
        changed_over_25ms=int(np.count_nonzero(delta>.025)),source_changes=sum(r.get('old_source')!=r.get('new_source') for r in rows if r['accepted']),
        projection_max_error_counts=max_error,promotion=False,predictions=0,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
