"""Independent label arithmetic, frozen support and clock-difference diagnostics."""
import csv,json
import numpy as np
import pipeline as p
from seedless_clock_v83 import OUT as SEEDS
from fold_seedless_clock_v84 import OUT as CLOCKS
from native_projection_v80 import OUT as SENSOR
from native_refit_v81 import OUT as FROZEN
from audit_fold_routes_v59 import verified_json
from backfill_metric_contract_v75 import summaries

OUT=p.ROOT/'outputs_seedless_review_v85'


def main():
    OUT.mkdir(exist_ok=False)
    manifests={};hashes=0
    for folder in (SEEDS,CLOCKS,SENSOR,FROZEN):
        manifests[folder]=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
        for name,sha in manifests[folder].items():
            assert p.digest(folder/name)==sha;hashes+=1
    seeds={r['id']:r for r in verified_json(SEEDS,'seeds.json')}
    clocks={r['id']:r for r in verified_json(CLOCKS,'clocks.json')}
    models=verified_json(CLOCKS,'models.json');rows=[];maximum=0.;label_checks=0;total_labels=0
    for fold,q in models.items():
        fit=set(q['fit_ids']);held=set(q['held_ids']);assert not fit&held
        assert not {seeds[i]['participant'] for i in fit}&{seeds[i]['participant'] for i in held}
        assert fit=={i for i,r in seeds.items() if r['accepted'] and i not in held}
        for setup,cal in q['calibration'].items():
            assert set(cal['training_trials'])=={i for i in fit if seeds[i]['setup']==setup}
            labels=sum((seeds[i]['seed_labels']+4)//5 for i in cal['training_trials'])
            assert labels==cal['n_labels']
    for ident,seed in seeds.items():
        with np.load(SEEDS/'references'/(ident+'.npz')) as z:gt={k:z[k] for k in z.files}
        with np.load(SENSOR/'sensors'/(ident+'.npz')) as z:full={k:z[k] for k in ('t','raw','imu_valid')}
        if seed['accepted']:
            # Independently reproduce the conservative bracket mask and values.
            query=full['t']-seed['offset_s'];right=np.searchsorted(gt['t'],query).clip(1,len(gt['t'])-1);left=right-1
            support=full['imu_valid']&gt['derivative_valid'][left]&gt['derivative_valid'][right]
            support&=(query>=gt['t'][0])&(query<=gt['t'][-1])&(gt['t'][right]-gt['t'][left]<=1.5*np.median(np.diff(gt['t'])))
            with np.load(SEEDS/'labels'/(ident+'.npz')) as saved:
                assert np.array_equal(support,saved['label_valid']) and np.array_equal(full['raw'],saved['raw'])
                for source,target in [('speed','gt_v'),('yaw','gt_yaw')]:
                    values=np.interp(query,gt['t'],np.nan_to_num(gt[source]));values[~support]=np.nan
                    maximum=max(maximum,float(np.nanmax(abs(values[support]-saved[target][support]))))
                    assert np.array_equal(values[support],saved[target][support])
            assert support.sum()==seed['seed_labels'];label_checks+=1;total_labels+=int(support.sum())
        fresh=clocks[ident];meta=verified_json(SENSOR,str((SENSOR/'sensors'/(ident+'.json')).relative_to(SENSOR)))
        with np.load(FROZEN/'common_trajectories'/(ident+'.npz')) as z:
            ix=np.searchsorted(gt['t'],z['native_c3d_time_s'])
            assert np.max(abs(gt['t'][ix]-z['native_c3d_time_s']))<1e-9
            assert np.array_equal(gt['valid'][ix],z['reference_valid'])
            assert np.array_equal(gt['xy'][ix],z['reference_xy_m']) and np.array_equal(gt['heading'][ix],z['reference_heading_rad'])
            frozen_times=z['native_c3d_time_s'];frozen_support=z['imu_valid'];frozen_observed=z['reference_valid']
        row=dict(id=ident,participant=seed['participant'],condition=seed['condition'],seed_accepted=seed['accepted'],held_clock_accepted=fresh['accepted'],
            old_offset_s=meta['offsets']['old'],new_offset_s=meta['offsets']['new'],frozen_scored_frames=int((frozen_observed&frozen_support).sum()))
        if fresh['accepted']:
            lag=fresh['offset_s'];row.update(fresh_offset_s=lag,delta_vs_old_s=lag-meta['offsets']['old'],delta_vs_new_s=lag-meta['offsets']['new'])
            _,ok=p.masked_interp(frozen_times+lag,full['t'],full['raw'][:,15],full['imu_valid'])
            row['frozen_support_lost_frames']=int((frozen_support&~ok).sum())
        else:row.update(reason=fresh['reason'],frozen_support_lost_frames=None)
        rows.append(row)
    assert len(rows)==207 and label_checks==190 and maximum==0
    p.write_csv(OUT/'clock_comparison.csv',rows)
    for key in ('participant','condition'):
        table=[]
        for value in sorted({r[key] for r in rows}):
            group=[r for r in rows if r[key]==value];matched=[r for r in group if r['held_clock_accepted']]
            table.append({key:value,'trials':len(group),'seed_accepted':sum(r['seed_accepted'] for r in group),'held_clock_accepted':len(matched),
                'held_clock_rejected':len(group)-len(matched),'max_abs_delta_vs_new_s':max((abs(r['delta_vs_new_s']) for r in matched),default=None)})
        p.write_csv(OUT/(key+'_coverage.csv'),table)
    accepted=[r for r in rows if r['held_clock_accepted']]
    run=dict(artifact_hashes_verified=hashes,seed_label_checks=label_checks,seed_label_frames=total_labels,max_label_difference=maximum,
        frozen_reference_checks=207,seed_accepted=190,seed_rejected=17,held_clock_accepted=len(accepted),held_clock_rejected=207-len(accepted),
        max_abs_delta_vs_old_s=max(abs(r['delta_vs_old_s']) for r in accepted),max_abs_delta_vs_new_s=max(abs(r['delta_vs_new_s']) for r in accepted),
        changed_vs_new_over_1ms=sum(abs(r['delta_vs_new_s'])>.001 for r in accepted),changed_vs_new_over_250ms=sum(abs(r['delta_vs_new_s'])>.25 for r in accepted),
        supported_clocks_losing_frozen_frames=sum(r['frozen_support_lost_frames']>0 for r in accepted),
        lost_frozen_frames=sum(r['frozen_support_lost_frames'] for r in accepted),
        metric_status='All trajectory metrics unavailable: no new trajectory predictions; retained v81 and historical benchmarks unchanged',
        review='Same-context independent arithmetic audit plus separately requested read-only agent review',
        decision='Seed dependency removed locally, but all-207 coverage gate fails; no refit, promotion, commit or push',promotion=False,validation_accessed=False,test_accessed=False)
    p.save_json(OUT/'run.json',run)
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps(run,indent=2),flush=True)


if __name__=='__main__':main()
