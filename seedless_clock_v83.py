"""Full-record, uncalibrated observed-segment clock seeds; TRAIN only."""
import json
import numpy as np
import pipeline as p
from observed_reference_experiment import observed_markers
from observed_sync_experiment import synchronize_observed
from native_projection_v80 import OUT as SENSOR
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_seedless_clock_v83'


def magnitude_seed(full,gt,cfg,setup):
    # Reuse the tested observed-only search with magnitude channels and absolute
    # optical yaw. No fitted axes, bias, labels, or inherited lag enter this call.
    raw=np.zeros_like(full['raw'])
    for column in (3,9,15):
        raw[:,column]=np.linalg.norm(full['raw'][:,column:column+3],axis=1)
    terms=[dict(column=c,scale=1.,intercept=0.) for c in (3,9,15)]
    settings=dict(cfg,sync_terms={setup:terms})
    result=synchronize_observed(full['t'],raw,full['imu_valid'],dict(gt,yaw=np.abs(gt['yaw'])),settings,setup)
    result['source']='uncalibrated_magnitude_'+result['source']
    return result


def seed_labels(full,gt,offset,cfg):
    rt=full['t']-offset
    speed,sv=p.masked_interp(rt,gt['t'],gt['speed'],gt['derivative_valid'])
    yaw,yv=p.masked_interp(rt,gt['t'],gt['yaw'],gt['derivative_valid'])
    good=full['imu_valid']&sv&yv
    if good.sum()/cfg['hz']<cfg['min_valid_s']:
        raise ValueError('Insufficient seed derivative labels')
    return dict(raw=full['raw'],gt_v=speed,gt_yaw=yaw,label_valid=good)


def check():
    t=np.arange(0,35,.01);yaw=sum(np.exp(-((t-c)/.22)**2)*s for c,s in [(4,1),(9,-.7),(15,1.3),(24,-.8),(29,.6)])
    raw=np.zeros((len(t),18));raw[:,15]=yaw*1000;raw[:,3]=raw[:,9]=100+30*np.sin(t/3)
    full=dict(t=t,raw=raw,imu_valid=np.ones(len(t),bool))
    gt=dict(t=t,yaw=yaw,speed=np.ones(len(t)),derivative_valid=np.ones(len(t),bool),hz=100)
    cfg=dict(hz=100,peak_prominence=.3,peak_distance_s=.5,min_peak_matches=3,max_lag_s=2.,peak_tolerance_s=.15,ambiguity_margin=.02,min_sync_corr=.6,sync_refinement_radius_s=.025,sync_refinement_step_s=.0001,min_valid_s=2.)
    a=magnitude_seed(full,gt,cfg,'synthetic')
    assert abs(a['offset_s'])<.001
    poisoned=dict(cfg,sync_terms={'synthetic':[dict(column=0,scale=-999,intercept=777)]*3})
    assert magnitude_seed(full,gt,poisoned,'synthetic')==a
    d=seed_labels(full,gt,a['offset_s'],cfg);assert d['label_valid'].sum()>3000


def main():
    check();OUT.mkdir(exist_ok=False);(OUT/'references').mkdir();(OUT/'labels').mkdir()
    protocol=verified_json(p.ROOT/'outputs_paired_clock_refit_v72','protocol.json')
    cfg=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())['old_clock_settings']
    cfg={k:v for k,v in cfg.items() if k!='sync_terms'}
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    p.save_json(OUT/'protocol.json',dict(hypothesis='Unfitted full-record gyro magnitude events provide bootstrap labels without held-person clock seeds',
        configurations=['one magnitude seed; unchanged observed-segment gates'],settings=cfg,training_ids=protocol['training_ids'],
        no_inherited_lag=True,no_fitted_sensor_features=True,no_ATE_selection=True,validation_accessed=False,test_accessed=False,
        limitation='Frozen accepted TRAIN207 and inherited reference geometry/QC remain conditional; magnitude aliases may reject or misalign',
        next_gate='All 207 held clocks and frozen scoring support required before estimator refit; no inherited fallback or favorable subset headline'))
    manifest=json.loads((SENSOR/'artifact_manifest.json').read_text())['sha256'];rows=[]
    for n,ident in enumerate(protocol['training_ids'],1):
        r=inv[ident];assert r['partition']=='train'
        path=SENSOR/'sensors'/(ident+'.npz');assert p.digest(path)==manifest[str(path.relative_to(SENSOR))]
        meta=verified_json(SENSOR,str(path.with_suffix('.json').relative_to(SENSOR)))
        assert p.digest(p.ROOT/r['imu'])==meta['raw_sha256']
        with np.load(path) as z:full={k:z[k] for k in ('t','raw','imu_valid')}
        original=p.read_markers
        try:p.read_markers=observed_markers;gt=p.reference(p.ROOT/r['c3d'],cfg,r['setup'])
        finally:p.read_markers=original
        np.savez_compressed(OUT/'references'/(ident+'.npz'),**{k:gt[k] for k in ('t','xy','heading','valid','derivative_valid','yaw','speed','hz')})
        row=dict(id=ident,participant=r['participant'],condition=r['condition'],setup=r['setup'],source_sensor_sha256=p.digest(path),source_c3d_sha256=p.digest(p.ROOT/r['c3d']))
        try:
            sync=magnitude_seed(full,gt,cfg,r['setup']);d=seed_labels(full,gt,sync['offset_s'],cfg)
            np.savez_compressed(OUT/'labels'/(ident+'.npz'),**d)
            row.update(accepted=True,**sync,seed_labels=int(d['label_valid'].sum()))
        except (p.TrialRejected,ValueError) as exc:
            row.update(accepted=False,reason=str(exc),diagnostics=getattr(exc,'diagnostics',None))
        rows.append(row);p.save_json(OUT/'checkpoint.json',rows)
        if n%25==0:print('v83 seeds',n,'accepted',sum(q['accepted'] for q in rows),flush=True)
    assert len(rows)==207
    p.save_json(OUT/'seeds.json',rows);p.write_csv(OUT/'trials.csv',[{k:v for k,v in r.items() if k not in ('diagnostics','search_diagnostics')} for r in rows])
    p.save_json(OUT/'run.json',dict(trials=207,accepted=sum(r['accepted'] for r in rows),rejected=sum(not r['accepted'] for r in rows),promotion=False,trajectory_metrics='unavailable: clock seed experiment, no trajectory predictions',validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
