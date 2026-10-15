"""Three preregistered gains of frozen v119 delta3; no fitting."""
import csv
import json
import time
import numpy as np
import pipeline as p
from trajectory_calibration_v10 import integrate
from metric_contract_v74 import metrics
from combined_physics_folds_v58 import verified_json
from joint_robust_motion_v119 import balanced

OUT=p.ROOT/'outputs_conservative_robust_v120'
PARENT=p.ROOT/'outputs_joint_robust_motion_v119'
GAINS=(.05,.075,.10)


def shrink(base, corrected, gain):
    return base+(gain/.25)*(corrected-base)


def main():
    start=time.perf_counter()
    assert np.array_equal(shrink(np.zeros((2,3)),np.ones((2,3)),0),np.zeros((2,3)))
    assert np.array_equal(shrink(np.zeros((2,3)),np.ones((2,3)),.25),np.ones((2,3)))
    if (p.ROOT/'research_state/STOP').exists():raise RuntimeError('STOP')
    OUT.mkdir(exist_ok=False);(OUT/'predictions').mkdir()
    manifest=json.loads((PARENT/'artifact_manifest.json').read_text())['sha256']
    assert p.digest(PARENT/'trials.csv')==manifest['trials.csv']
    protocol=verified_json(PARENT,'protocol.json')
    cfg=verified_json(p.ROOT/'outputs_clock_arbitrated_v42','protocol.json')['old_clock_settings']
    baseline=[r for r in csv.DictReader((PARENT/'trials.csv').open(newline='')) if float(r['delta'])==0]
    assert len(baseline)==207 and len({r['id'] for r in baseline})==207
    source_names=['conservative_robust_v120.py','joint_robust_motion_v119.py',
        'pipeline.py','trajectory_calibration_v10.py','metric_contract_v74.py',
        'research_metrics_v59.py','route_metrics_audit_v36.py',
        'research_docs/conservative_robust_v120.md']
    p.save_json(OUT/'protocol.json',dict(gains=GAINS,frozen_delta=3,training_ids=protocol['training_ids'],
        parent_manifest_sha256=p.digest(PARENT/'artifact_manifest.json'),
        source_hashes={s:p.digest(p.ROOT/s) for s in source_names},
        validation_accessed=False,test_accessed=False,new_fits=0))
    rows=[]
    for fold in range(3):
        if (p.ROOT/'research_state/STOP').exists():raise RuntimeError('STOP')
        for old in baseline:
            if int(old['fold'])!=fold:continue
            path=PARENT/'predictions'/(old['id']+'.npz')
            assert p.digest(path)==manifest[str(path.relative_to(PARENT))]
            with np.load(path) as z:arrays={k:z[k] for k in z.files}
            data={k:arrays[k] for k in ('t','gt_xy','gt_heading','gt_valid','imu_valid')}
            saved={**data}; base=arrays['delta_0_motion']; robust=arrays['delta_3_motion']
            support=data['gt_valid']&np.isfinite(arrays['delta_0_xy']).all(1)
            assert np.isclose(int(support.sum()),float(old['scored_frames']))
            for gain in (0.,*GAINS):
                motion=shrink(base,robust,gain);xy,h=integrate(data,motion)
                assert np.array_equal(support,data['gt_valid']&np.isfinite(xy).all(1))
                if gain==0:
                    assert np.allclose(xy,arrays['delta_0_xy'],equal_nan=True,atol=1e-12,rtol=1e-12)
                    assert np.allclose(h,arrays['delta_0_heading'],equal_nan=True,atol=1e-12,rtol=1e-12)
                score=p.metrics(data,xy,h,cfg);extra=metrics(data,xy,h,motion)
                rows.append(dict(id=old['id'],participant=old['participant'],condition=old['condition'],fold=fold,gain=gain,**score,**extra))
                prefix=f'gain_{gain:g}_';saved.update({prefix+'motion':motion,prefix+'xy':xy,prefix+'heading':h})
            np.savez_compressed(OUT/'predictions'/(old['id']+'.npz'),**saved)
        p.write_csv(OUT/'trials.csv',rows)
        p.save_json(OUT/'checkpoint.json',dict(completed_folds=fold+1,rows=len(rows),status='running'))
        print('Completed fold',fold,flush=True)
    base=[r for r in rows if r['gain']==0];bs,bp,bm=p.summarize(base)
    candidates=[]
    for gain in (0.,*GAINS):
        rr=[r for r in rows if r['gain']==gain];assert len(rr)==207
        summary,pp,mm=p.summarize(rr)
        pr={r['participant']:r['mean_trial_position_rmse_m']/next(b['mean_trial_position_rmse_m'] for b in bp if b['participant']==r['participant']) for r in pp}
        mr={r['condition']:r['equal_participant_mean_position_rmse_m']/next(b['equal_participant_mean_position_rmse_m'] for b in bm if b['condition']==r['condition']) for r in mm}
        guards={key:balanced(rr,key)/balanced(base,key) for key in ('Position_P95_mm','Last_Supported_Endpoint_Error_mm','heading_rmse_deg')}
        eligible=gain==0 or (summary['equal_participant_mean_position_rmse_m']<bs['equal_participant_mean_position_rmse_m'] and max(pr.values())<=1.05 and max(mr.values())<=1.05 and max(guards.values())<=1.05)
        candidates.append(dict(gain=gain,eligible=eligible,**summary,participant_ratios=pr,maneuver_ratios=mr,guard_ratios=guards))
        p.write_csv(OUT/f'gain_{gain:g}_participants.csv',pp);p.write_csv(OUT/f'gain_{gain:g}_maneuvers.csv',mm)
    selected=min((c for c in candidates if c['eligible']),key=lambda c:c['equal_participant_mean_position_rmse_m'])
    p.save_json(OUT/'run.json',dict(candidates=candidates,selected=selected,runtime_s=time.perf_counter()-start,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'checkpoint.json',dict(completed_folds=3,rows=len(rows),status='complete'))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}))
    print(json.dumps(candidates,indent=2),flush=True)


if __name__=='__main__':main()
