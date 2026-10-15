"""TRAIN-only reference closure and heading oracles. Never an estimator input."""
import json
import time
import numpy as np
import pipeline as p
from clock_refit_experiment_v38 import OLD, NEW, load_cache
from audit_fold_routes_v59 import verified_json
from projected_yaw_folds_v52 import proxy
from planar_experiment import lateral_labels
from trajectory_calibration_v10 import integrate
from research_metrics_v59 import trajectory_metrics, aggregate

OUT = p.ROOT / 'outputs_reference_closure_v66'


def world_velocity(v, side, heading):
    c, s = np.cos(heading), np.sin(heading)
    return np.c_[v*c-side*s, v*s+side*c]


def integrate_world(t, velocity):
    return np.vstack((np.zeros(2), np.cumsum(np.diff(t)[:, None]*(velocity[1:]+velocity[:-1])/2, axis=0)))


def fixed_heading_xy(d, motion, heading):
    # Same midpoint motion convention as retained integrator; shortest circular mean.
    middle = np.angle(np.exp(1j*heading[:-1])+np.exp(1j*heading[1:]))
    local = (motion[1:]+motion[:-1])/2
    velocity = world_velocity(local[:, 0], local[:, 1], middle)
    xy = np.vstack((np.zeros(2), np.cumsum(np.diff(d['t'])[:, None]*velocity, axis=0)))+d['gt_xy'][0]
    bad = np.flatnonzero(~d['imu_valid'])
    if len(bad):
        xy[bad[0]:] = np.nan
    return xy


def self_check():
    t = np.linspace(0, 1, 101)
    v = np.c_[t*0+2, t*0]
    assert np.max(np.abs(integrate_world(t, v)[:, 0]-2*t)) < 1e-12
    h = np.linspace(3, 3.5, len(t))
    d = dict(t=t, imu_valid=np.ones(len(t), bool), gt_xy=np.zeros((len(t), 2)), gt_heading=h)
    m = np.c_[t*0+1, t*0, t*0+.5]
    xy, expected = integrate(d, m)
    assert np.max(np.abs(fixed_heading_xy(d, m, expected)-xy)) < 1e-12
    d['imu_valid'][50] = False
    assert np.isnan(fixed_heading_xy(d, m, expected)[50:]).all()


def main():
    self_check()
    started = time.perf_counter()
    OUT.mkdir(exist_ok=False)
    p.save_json(OUT/'protocol.json', dict(hypothesis='v63 all-truth residual is dominated by derivative gaps/fallback rather than a broken pose integrator',
        family='1 reference/integration correctness', configurations=['consistent raw-XY derivative local closure', 'cached local-motion derivative closure', 'absolute observed heading with predicted velocity'],
        controls='v52 frozen TRAIN207 control; unchanged calibration, clocks, initial pose and observed scoring mask',
        local_runs='Each contiguous derivative-labelled run is independently anchored ONLY for reference closure diagnosis. Not continuous localization and never promoted.',
        heading_oracle='Observed C3D heading replaces predicted heading only on gt_valid; predicted heading through gaps; continuous position, no position resets',
        selection=False, diagnostic_only=True, validation_accessed=False, test_accessed=False))
    clock = json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text())
    inv = {r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    folds = verified_json(p.ROOT/'outputs_braking_hysteresis_v56', 'fold_models.json')
    manifests = {s:json.loads((s/'artifact_manifest.json').read_text()) for s in (OLD, NEW)}
    rows, closures = [], []
    for fold, q in folds.items():
        y = verified_json(p.ROOT/'outputs_projected_yaw_v52', f'fold_{fold}_models.json')
        assert q['calibration'] == y['calibration'] and set(q['fit_ids']) == set(y['fitting_ids'])
        for ident in q['held_ids']:
            r = inv[ident]
            assert r['partition'] == 'train' and ident not in q['fit_ids']
            d, _ = load_cache(OLD if ident in clock['fallback_old_clock_ids'] else NEW, ident, manifests[OLD if ident in clock['fallback_old_clock_ids'] else NEW])
            cal, ym = q['calibration'][r['setup']], y['yaw'][r['setup']]
            v = p.velocities(d, cal)
            motion = np.c_[v[:, 0], np.zeros(len(v)), proxy(d, cal)*ym['scale']+ym['intercept']]
            xy, heading = integrate(d, motion)
            assert np.nanmax(np.abs(fixed_heading_xy(d, motion, heading)-xy)) < 1e-10
            oracle_h = np.where(d['gt_valid'], d['gt_heading'], heading)
            oracle_xy = fixed_heading_xy(d, motion, oracle_h)
            common = d['gt_valid'] & np.isfinite(xy).all(axis=1) & np.isfinite(oracle_xy).all(axis=1)
            side, side_valid = lateral_labels(d)
            labels = d['label_valid'] & side_valid & d['imu_valid'] & np.isfinite(d['gt_v']) & np.isfinite(d['gt_yaw'])
            for method, pos, h in [('control',xy,heading), ('absolute_heading_oracle',oracle_xy,oracle_h)]:
                metric = trajectory_metrics(d, pos, h)
                assert metric['supported_frames'] == int(common.sum())
                error = pos[common]-d['gt_xy'][common]
                theta = d['gt_heading'][common]
                along = error[:,0]*np.cos(theta)+error[:,1]*np.sin(theta)
                across = -error[:,0]*np.sin(theta)+error[:,1]*np.cos(theta)
                magnitude = np.linalg.norm(error, axis=1)
                rows.append(dict(id=ident, participant=r['participant'], condition=r['condition'], method=method,
                    along_rmse_m=float(np.sqrt(np.mean(along**2))), cross_rmse_m=float(np.sqrt(np.mean(across**2))),
                    position_mae_m=float(magnitude.mean()), position_p95_m=float(np.percentile(magnitude,95)),
                    common_frames=int(common.sum()), label_fraction=float(labels.mean()), **metric))
            for a,b in p.runs(labels):
                if b-a < 20:
                    continue
                t, ref, h = d['t'][a:b], d['gt_xy'][a:b], d['gt_heading'][a:b]
                raw_world = np.gradient(ref, t, axis=0)
                cached_world = world_velocity(d['gt_v'][a:b],side[a:b],h)
                for method, velocity in [('consistent_xy_derivative',raw_world),('cached_body_derivative',cached_world)]:
                    pos = integrate_world(t, velocity)+ref[0]
                    error = np.linalg.norm(pos-ref,axis=1)
                    closures.append(dict(id=ident,participant=r['participant'],condition=r['condition'],method=method,
                        start=a,end=b,duration_s=float(t[-1]-t[0]),frames=b-a,rmse_m=float(np.sqrt(np.mean(error**2))),endpoint_m=float(error[-1])))
            if r['condition'] == '10x5' and r['participant'] == 'No.8':
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                fig, axes = plt.subplots(1,2,figsize=(11,4))
                ref = d['gt_xy'].copy(); ref[~d['gt_valid']] = np.nan
                axes[0].plot(ref[:,0],ref[:,1],'k',label='C3D'); axes[0].plot(xy[:,0],xy[:,1],'r',label='IMU control')
                axes[0].plot(oracle_xy[:,0],oracle_xy[:,1],color='blue',label='Heading oracle: diagnostic')
                axes[0].axis('equal'); axes[0].set(xlabel='X (m)',ylabel='Y (m)')
                for hh,color,label in [(d['gt_heading'],'k','C3D'),(heading,'r','IMU control')]:
                    hh = np.rad2deg(np.angle(np.exp(1j*(hh-d['gt_heading'][0])))); hh = hh.copy()
                    if color == 'k': hh[~d['gt_valid']] = np.nan
                    hh[np.r_[False,np.abs(np.diff(hh))>180]] = np.nan
                    axes[1].plot(d['t'],hh,color,label=label)
                axes[1].set(xlabel='Time (s)',ylabel='Relative wrapped yaw (deg)')
                for ax in axes: ax.grid(alpha=.2); ax.legend()
                fig.suptitle(ident); fig.tight_layout(); (OUT/'figures').mkdir(exist_ok=True)
                fig.savefig(OUT/'figures'/f'{ident}.png',dpi=140); plt.close(fig)
            print(ident,flush=True)
    assert len(rows) == 414
    for keys, name in [(('method',),'summary'),(('method','participant'),'participants'),(('method','condition'),'maneuvers')]:
        p.write_csv(OUT/(name+'.csv'),aggregate(rows,keys))
    p.write_csv(OUT/'trials.csv',rows); p.write_csv(OUT/'closures.csv',closures)
    summary = aggregate(rows,('method',))
    control = next(r for r in summary if r['method']=='control')
    assert abs(control['position_rmse_m']-.14774650809690637)<1e-10
    closure_summary = {}
    for method in ('consistent_xy_derivative','cached_body_derivative'):
        s = [r for r in closures if r['method']==method]
        closure_summary[method] = dict(runs=len(s), duration_s=sum(r['duration_s'] for r in s),
            frame_weighted_rmse_m=float(np.sqrt(sum(r['frames']*r['rmse_m']**2 for r in s)/sum(r['frames'] for r in s))),
            endpoint_p95_m=float(np.percentile([r['endpoint_m'] for r in s],95)),endpoint_max_m=max(r['endpoint_m'] for r in s))
    p.save_json(OUT/'run.json',dict(summary=summary,local_closure=closure_summary,diagnostic_only=True,
        validation_accessed=False,test_accessed=False,runtime_s=time.perf_counter()-started))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps(closure_summary,indent=2))


if __name__ == '__main__':
    main()
