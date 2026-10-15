"""Explain v66 heading oracle with endpoint error accounting; no new fitting."""
import csv
import json
import numpy as np
import pipeline as p
from reference_closure_v66 import OLD, NEW, load_cache, verified_json, proxy, integrate, fixed_heading_xy

OUT = p.ROOT / 'outputs_reference_gap_accounting_v67'


def account(data, xy):
    valid = data['gt_valid'] & np.isfinite(xy).all(axis=1)
    blocks = list(p.runs(valid))
    observed = np.zeros(2); gaps = np.zeros(2)
    def residual(a,b):
        return xy[b]-xy[a]-(data['gt_xy'][b]-data['gt_xy'][a])
    for a,b in blocks:
        observed += residual(a,b-1)
    for (_, b),(c,_) in zip(blocks,blocks[1:]):
        gaps += residual(b-1,c)
    total = residual(blocks[0][0],blocks[-1][1]-1)
    assert np.max(np.abs(total-observed-gaps)) < 1e-10
    return dict(observed_error_x_m=float(observed[0]),observed_error_y_m=float(observed[1]),
        gap_error_x_m=float(gaps[0]),gap_error_y_m=float(gaps[1]),endpoint_error_m=float(np.linalg.norm(total)),
        observed_component_norm_m=float(np.linalg.norm(observed)),gap_component_norm_m=float(np.linalg.norm(gaps)),
        observed_signed_endpoint_mse_m2=float(total@observed),gap_signed_endpoint_mse_m2=float(total@gaps),
        valid_fraction=float(valid.mean()),observed_runs=len(blocks))


def relative_errors(d, xy):
    valid = d['gt_valid'] & np.isfinite(xy).all(axis=1)
    result = {}
    for seconds in (1,5,10):
        errors = []
        for a,b in p.runs(valid):
            for i in range(a,b,max(1,round(1/np.median(np.diff(d['t']))))):
                j = int(np.searchsorted(d['t'],d['t'][i]+seconds))
                if j >= b: continue
                errors.append(np.linalg.norm((xy[j]-xy[i])-(d['gt_xy'][j]-d['gt_xy'][i])))
        result[f'rpe_{seconds}s_windows'] = len(errors)
        result[f'rpe_{seconds}s_rmse_m'] = float(np.sqrt(np.mean(np.square(errors)))) if errors else None
    return result


def main():
    # Small exact decomposition check, including a gap and canceling errors.
    test = dict(gt_valid=np.array([True,True,False,True,True]),gt_xy=np.c_[np.arange(5),np.zeros(5)])
    check = account(test,test['gt_xy']+np.c_[[0,1,1,2,3],np.zeros(5)])
    assert check['observed_error_x_m']==2 and check['gap_error_x_m']==1
    OUT.mkdir(exist_ok=False)
    p.save_json(OUT/'protocol.json',dict(diagnostic_only=True,new_candidate=False,new_fitting=False,
        question='Does v66 absolute-heading regression arise within observed runs or across missing-reference intervals?',
        accounting='Telescoping endpoint displacement residual in observed runs versus bridges between supported runs; signed projections onto total endpoint error add exactly to endpoint squared error. Not causal attribution.',
        rpe='World displacement difference over contiguous observed 1/5/10s intervals, starts every1s, no gap bridging, no alignment. This is not SE(2) rotation-normalized RPE.',
        family='1 analysis of the same three v66 prespecified diagnostic configurations',validation_accessed=False,test_accessed=False))
    previous = verified_json(p.ROOT/'outputs_reference_closure_v66','run.json')
    parent = list(csv.DictReader((p.ROOT/'outputs_reference_closure_v66/trials.csv').open()))
    by_key = {(r['id'],r['method']):r for r in parent}
    clock = json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())
    inv = {r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    folds = verified_json(p.ROOT/'outputs_braking_hysteresis_v56','fold_models.json')
    manifests = {s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD,NEW)}
    rows = []
    for fold,q in folds.items():
        y = verified_json(p.ROOT/'outputs_projected_yaw_v52',f'fold_{fold}_models.json')
        for ident in q['held_ids']:
            r=inv[ident]; assert r['partition']=='train'
            src=OLD if ident in clock['fallback_old_clock_ids'] else NEW
            d,_=load_cache(src,ident,manifests[src]); cal=q['calibration'][r['setup']]; ym=y['yaw'][r['setup']]
            motion=np.c_[p.velocities(d,cal)[:,0],np.zeros(len(d['t'])),proxy(d,cal)*ym['scale']+ym['intercept']]
            xy,h=integrate(d,motion); oh=np.where(d['gt_valid'],d['gt_heading'],h); ox=fixed_heading_xy(d,motion,oh)
            arrays={}
            for method,pos,hh in [('control',xy,h),('absolute_heading_oracle',ox,oh)]:
                mask=d['gt_valid'] & np.isfinite(pos).all(axis=1)
                expected=by_key[(ident,method)]
                rmse=float(np.sqrt(np.mean(np.sum((pos[mask]-d['gt_xy'][mask])**2,axis=1))))
                assert abs(rmse-float(expected['position_rmse_m']))<1e-10
                rows.append(dict(id=ident,participant=r['participant'],condition=r['condition'],method=method,
                    position_rmse_m=rmse,**account(d,pos),**relative_errors(d,pos)))
                arrays[method+'_xy_m']=pos; arrays[method+'_heading_rad']=hh
            # Persist actual diagnostic predictions for selected failure cases.
            if r['condition']=='10x5' and r['participant'] in ('No.3','No.8'):
                (OUT/'trajectories').mkdir(exist_ok=True)
                np.savez_compressed(OUT/'trajectories'/f'{ident}.npz',time_s=d['t'],reference_xy_m=d['gt_xy'],reference_heading_rad=d['gt_heading'],reference_valid=d['gt_valid'],**arrays)
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                fig,axes=plt.subplots(1,2,figsize=(11,4)); ref=d['gt_xy'].copy(); ref[~d['gt_valid']]=np.nan
                for pos,col,label in [(ref,'k','C3D'),(xy,'r','IMU control'),(ox,'b','Heading oracle: diagnostic')]: axes[0].plot(pos[:,0],pos[:,1],col,label=label)
                axes[0].axis('equal'); axes[0].set(xlabel='X (m)',ylabel='Y (m)')
                for hh,col,label in [(d['gt_heading'],'k','C3D'),(h,'r','IMU control')]:
                    hh=np.rad2deg(np.angle(np.exp(1j*(hh-d['gt_heading'][0])))); hh=hh.copy()
                    if col=='k': hh[~d['gt_valid']]=np.nan
                    hh[np.r_[False,np.abs(np.diff(hh))>180]]=np.nan
                    axes[1].plot(d['t'],hh,col,label=label)
                axes[1].set(xlabel='Time (s)',ylabel='Wrapped relative yaw (deg)')
                for ax in axes: ax.grid(alpha=.2); ax.legend()
                fig.suptitle(ident); fig.tight_layout(); (OUT/'figures').mkdir(exist_ok=True); fig.savefig(OUT/'figures'/f'{ident}.png',dpi=140); plt.close(fig)
    p.write_csv(OUT/'trials.csv',rows)
    summaries=[]
    fields=['position_rmse_m','observed_component_norm_m','gap_component_norm_m','endpoint_error_m','observed_signed_endpoint_mse_m2','gap_signed_endpoint_mse_m2','valid_fraction']+[f'rpe_{s}s_rmse_m' for s in (1,5,10)]
    for method,condition in sorted({(r['method'],r['condition']) for r in rows}):
        members=[r for r in rows if r['method']==method and r['condition']==condition]
        summary=dict(method=method,condition=condition,trials=len(members))
        for field in fields:
            values=[float(np.mean([r[field] for r in members if r['participant']==person and r[field] is not None])) for person in sorted({r['participant'] for r in members}) if any(r['participant']==person and r[field] is not None for r in members)]
            summary[field]=float(np.mean(values)) if values else None
        summaries.append(summary)
    p.write_csv(OUT/'maneuvers.csv',summaries)
    p.save_json(OUT/'run.json',dict(summary=summaries,trials=207,diagnostic_only=True,baseline_reproduced=True,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps([r for r in summaries if r['condition']=='10x5'],indent=2))


if __name__=='__main__': main()
