"""Same-support route diagnostics reused from v36; no fitted transforms."""
import numpy as np
from scipy.spatial.distance import cdist
from route_metrics_audit_v36 import pieces, route, sample_piece, length

METRICS = ('position_rmse_m', 'heading_rmse_deg', 'route_rmse_m', 'route_p95_m',
           'sampled_hausdorff_m', 'supported_run_frechet_max_m',
           'supported_last_endpoint_error_m', 'supported_pathlength_absolute_error_m')


def discrete_frechet(a, b):
    """Vectorized anti-diagonals implement the ordinary discrete recurrence."""
    distance = cdist(a, b)
    n, m = distance.shape
    previous = np.full(n, np.inf)
    older = previous.copy()
    for k in range(n + m - 1):
        i = np.arange(max(0, k - m + 1), min(n - 1, k) + 1)
        j = k - i
        current = np.full(n, np.inf)
        up = np.where(i > 0, previous[np.maximum(i - 1, 0)], np.inf)
        left = np.where(j > 0, previous[i], np.inf)
        diagonal = np.where((i > 0) & (j > 0), older[np.maximum(i - 1, 0)], np.inf)
        predecessor = np.minimum(np.minimum(up, left), diagonal)
        if k == 0:
            predecessor[:] = 0.
        current[i] = np.maximum(distance[i, j], predecessor)
        older, previous = previous, current
    return float(previous[n - 1])


def trajectory_metrics(data, xy, heading):
    valid = (data['gt_valid'] & np.isfinite(xy).all(axis=1)
             & np.isfinite(data['gt_xy']).all(axis=1) & np.isfinite(heading)
             & np.isfinite(data['gt_heading']))
    if not valid.any():
        raise ValueError('No common scoring support')
    ref, pred = pieces(data['gt_xy'], valid), pieces(xy, valid)
    hd = np.arctan2(np.sin(heading[valid] - data['gt_heading'][valid]),
                    np.cos(heading[valid] - data['gt_heading'][valid]))
    f = [discrete_frechet(sample_piece(r, .025), sample_piece(q, .025))
         for r, q in zip(ref, pred)]
    return dict(position_rmse_m=float(np.sqrt(np.mean(np.sum(
                    (xy[valid] - data['gt_xy'][valid]) ** 2, axis=1)))),
                heading_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(hd ** 2)))),
                supported_run_frechet_max_m=max(f),
                supported_last_endpoint_error_m=float(np.linalg.norm(
                    xy[valid][-1] - data['gt_xy'][valid][-1])),
                true_recording_endpoint_supported=bool(valid[-1]),
                supported_pathlength_absolute_error_m=abs(sum(map(length, pred)) - sum(map(length, ref))),
                supported_frames=int(valid.sum()), supported_runs=len(ref),
                **route(ref, pred, .01))


def aggregate(rows, group_keys=()):
    result = []
    for key in sorted({tuple(r[k] for k in group_keys) for r in rows}):
        subset = [r for r in rows if tuple(r[k] for k in group_keys) == key]
        people = sorted({r['participant'] for r in subset})
        item = dict(zip(group_keys, key), trials=len(subset), participants=len(people))
        for metric in METRICS:
            item[metric] = float(np.mean([np.mean([r[metric] for r in subset
                            if r['participant'] == person]) for person in people]))
        result.append(item)
    return result


if __name__ == '__main__':
    from route_metrics_audit_v36 import frechet
    rng = np.random.default_rng(59)
    for n, m in [(1, 1), (1, 7), (9, 1), (5, 7), (20, 11)]:
        a, b = rng.normal(size=(n, 2)), rng.normal(size=(m, 2))
        assert abs(discrete_frechet(a, b) - frechet(a, b)) < 1e-12
    print('Frechet recurrence checks passed')
