"""One prespecified existing-feature clock diagnostic; no trajectory fitting."""
import json
import numpy as np
import pipeline as p
from distributed_clock_candidates_v86 import load_inputs, SENSOR, SEEDS
from projected_yaw_folds_v52 import proxy
from observed_sync_experiment import synchronize_observed
from native_refit_v81 import OUT as FROZEN
from basin_completeness_v91 import verify

OUT=p.ROOT/'outputs_projected_clock_v108'
DOC=p.ROOT/'research_docs/projected_clock_v108.md'


def projected_raw(full,cal):
    term=cal['terms'][2]
    assert term['column']==15 and term['scale']>0 and cal['center_gravity_direction'][0]>.9
    raw=full['raw'].copy()
    yaw=proxy(full,cal)
    assert np.isfinite(yaw[full['imu_valid']]).all()
    raw[:,15]=yaw
    return raw,yaw


def check():
    for n in (20,400):
        raw=np.zeros((n,18));raw[:,12]=1000;raw[:,15:18]=[13,17,19]
        full=dict(raw=raw,imu_valid=np.ones(n,bool))
        cal=dict(terms=[{}, {},dict(column=15,scale=1)],center_gravity_direction=[1,0,0],gyro_bias_counts=[[0]*3,[0]*3,[3,5,7]])
        before=raw.copy();converted,yaw=projected_raw(full,cal)
        assert np.allclose(yaw,10,atol=1e-10) and np.array_equal(raw,before)
        assert np.array_equal(converted[:,:15],before[:,:15])
        assert np.array_equal(converted[:,16:],before[:,16:])


def main():
    check();cfg,inv,clocks,models,hashes=load_inputs();hashes+=verify(FROZEN)
    OUT.mkdir(exist_ok=False);(OUT/'features').mkdir()
    deps=['projected_yaw_folds_v52.py','observed_sync_experiment.py','distributed_clock_candidates_v86.py','pipeline.py']
    p.save_json(OUT/'protocol.json',dict(preregistration_sha256=p.digest(DOC),settings=cfg,
        source_sha256=p.digest(__file__),dependencies={n:p.digest(p.ROOT/n) for n in deps},parent_hashes_verified=hashes,
        parent_manifests={str(q.name):p.digest(q/'artifact_manifest.json') for q in (SENSOR,SEEDS,FROZEN,p.ROOT/'outputs_fold_seedless_clock_v84')},
        configurations=1,validation_accessed=False,test_accessed=False))
    rows=[]
    for baseline in clocks:
        ident=baseline['id'];r=inv[ident];assert r['partition']=='train'
        model=models[str(baseline['fold'])];assert ident in model['held_ids']
        cal=model['calibration'][r['setup']]
        with np.load(SENSOR/'sensors'/(ident+'.npz')) as z:full={k:z[k] for k in ('t','raw','imu_valid')}
        with np.load(SEEDS/'references'/(ident+'.npz')) as z:gt={k:z[k] for k in ('t','yaw','speed','derivative_valid','hz')}
        gt['hz']=float(gt['hz']);raw,yaw=projected_raw(full,cal)
        np.savez_compressed(OUT/'features'/(ident+'.npz'),t=full['t'],imu_valid=full['imu_valid'],projected_counts=yaw)
        settings=dict(cfg,sync_terms={r['setup']:cal['terms']})
        row=dict(id=ident,participant=r['participant'],condition=r['condition'],fold=baseline['fold'],baseline_accepted=baseline['accepted'])
        try:
            result=synchronize_observed(full['t'],raw,full['imu_valid'],gt,settings,r['setup'])
            row.update(accepted=True,**result)
            row['delta_vs_v84_s']=result['offset_s']-baseline['offset_s'] if baseline['accepted'] else None
            with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:
                rt=z['native_c3d_time_s'];mask=z['imu_valid']&z['reference_valid']
            _,ok=p.masked_interp(rt+result['offset_s'],full['t'],yaw,full['imu_valid'])
            row.update(frozen_scored_frames=int(mask.sum()),frozen_scored_lost=int((mask&~ok).sum()))
        except p.TrialRejected as exc:row.update(accepted=False,reason=str(exc),diagnostics=exc.diagnostics)
        rows.append(row)
        if len(rows)%10==0:p.save_json(OUT/'checkpoint.json',rows);print('v108',len(rows),sum(q['accepted'] for q in rows),flush=True)
    assert len(rows)==len({r['id'] for r in rows})==207
    assert sum(r['participant']=='No.20' for r in rows)==15
    p.save_json(OUT/'clocks.json',rows)
    p.write_csv(OUT/'trials.csv',[{k:v for k,v in r.items() if k not in ('diagnostics','search_diagnostics')} for r in rows])
    accepted=sum(r['accepted'] for r in rows)
    p.save_json(OUT/'run.json',dict(trials=207,accepted=accepted,rejected=207-accepted,
        newly_accepted=sum(r['accepted'] and not r['baseline_accepted'] for r in rows),
        newly_rejected=sum(not r['accepted'] and r['baseline_accepted'] for r in rows),
        support_loss_trials=sum(r.get('frozen_scored_lost',0)>0 for r in rows),
        frozen_scored_lost=sum(r.get('frozen_scored_lost',0) for r in rows),
        decision='requires independent alias/support review' if accepted==207 else 'fail closed: no estimator refit',
        accepted_clocks_unchanged=199,promotion=False,predictions=0,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
