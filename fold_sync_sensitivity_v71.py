"""TRAIN-only sensitivity to inherited versus fold-fitted sync terms."""
import json
import numpy as np
import pipeline as p
from observed_reference_experiment import observed_markers
from observed_sync_experiment import synchronize_observed
from audit_fold_routes_v59 import verified_json
from clock_refit_experiment_v38 import NEW

OUT=p.ROOT/'outputs_fold_sync_sensitivity_v71'


def main():
    x=np.sin(np.arange(1000)/20.)
    assert np.max(np.abs(p.smooth_standard(x,100)-p.smooth_standard(2*x+4,100)))<1e-10
    OUT.mkdir(exist_ok=False)
    folds=verified_json(p.ROOT/'outputs_strict_preprocessing_v70','folds.json')
    cfg=json.loads((NEW/'run.json').read_text())['settings']
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    p.save_json(OUT/'protocol.json',dict(family='2 clock provenance sensitivity',configurations=['inherited v9 sync terms','fold-fitted provisional sync terms'],
        no_new_model=True,no_position_error_clock_selection=True,reference_support='Same frozen reference inclusion policy for both; fold geometry not used to discard15 accepted trials',
        limitation='Fold bootstrap seed labels inherit historical clocks; sensitivity audit is not certified strictly nested preprocessing',validation_accessed=False,test_accessed=False))
    rows=[]
    for fold,q in folds.items():
        config=dict(cfg,sync_terms={s:c['terms'] for s,c in q['provisional_sync_calibration'].items()})
        assert not set(q['fit_ids'])&set(q['held_ids'])
        for ident in q['held_ids']:
            r=inv[ident]; assert r['partition']=='train'
            original=p.read_markers
            try:
                p.read_markers=observed_markers; gt=p.reference(p.ROOT/r['c3d'],cfg,r['setup'])
            finally: p.read_markers=original
            t,raw,valid=p.sample_streams(p.imu_streams(p.ROOT/r['imu']),cfg)
            row=dict(id=ident,participant=r['participant'],condition=r['condition'],fold=fold)
            inherited=cfg['sync_terms'][r['setup']][2]; nested=config['sync_terms'][r['setup']][2]
            row['center_axis_sign_equal']=bool(inherited['column']==nested['column'] and np.sign(inherited['scale'])==np.sign(nested['scale']))
            a=p.smooth_standard(raw[:,inherited['column']]*inherited['scale']+inherited['intercept'],cfg['hz'])
            b=p.smooth_standard(raw[:,nested['column']]*nested['scale']+nested['intercept'],cfg['hz'])
            row['normalized_yaw_max_difference']=float(np.max(np.abs(a-b)))
            for name,settings in [('inherited',cfg),('fold_terms',config)]:
                try:
                    result=synchronize_observed(t,raw,valid,gt,settings,r['setup'])
                    row.update({name+'_accepted':True,name+'_offset_s':result['offset_s'],name+'_source':result['source'],name+'_correlation':result['correlation']})
                except p.TrialRejected as exc:
                    row.update({name+'_accepted':False,name+'_reason':str(exc)})
            if row['inherited_accepted'] and row['fold_terms_accepted']:
                row['offset_delta_s']=row['fold_terms_offset_s']-row['inherited_offset_s']
            rows.append(row)
            if len(rows)%20==0: print(len(rows),flush=True)
    assert len(rows)==207
    p.write_csv(OUT/'trials.csv',rows)
    matched=[r for r in rows if 'offset_delta_s' in r]
    summary=dict(trials=len(rows),both_accepted=len(matched),inherited_rejections=sum(not r['inherited_accepted'] for r in rows),fold_rejections=sum(not r['fold_terms_accepted'] for r in rows),
        center_axis_sign_changes=sum(not r['center_axis_sign_equal'] for r in rows),max_normalized_yaw_difference=max(r['normalized_yaw_max_difference'] for r in rows),
        offset_changes_over_1ms=sum(abs(r['offset_delta_s'])>.001 for r in matched),max_abs_offset_change_s=max((abs(r['offset_delta_s']) for r in matched),default=0.),
        strictly_nested=False,promotion=False,validation_accessed=False,test_accessed=False)
    p.save_json(OUT/'run.json',summary)
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
