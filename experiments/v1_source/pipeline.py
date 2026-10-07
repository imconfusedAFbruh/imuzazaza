"""Offline three-IMU wheelchair reconstruction. Run --help for the CLI."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import ezc3d
import numpy as np
import scipy
from scipy import signal, optimize
from scipy.ndimage import uniform_filter1d
import yaml

ROOT = Path(__file__).resolve().parent
DATES = ('2026-09-24', '2026-09-25')
AXES = ('gx', 'gy', 'gz')


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def write_csv(path, rows):
    if not rows:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def selected_artifacts(out, name):
    paths = [out / 'calibration.json']
    if name != 'baseline':
        paths.extend([out / 'normalization.json', out / ('ridge.npy' if name == 'ridge' else name + '.pt')])
    return {p.name: digest(p) for p in paths}


def verify_selection(out, selection):
    if selection.get('artifact_sha256') != selected_artifacts(out, selection['selected']):
        raise RuntimeError('Selected artifacts changed or were not sealed after validation')
    if selection['calibration_sha256'] != digest(out / 'calibration.json'):
        raise RuntimeError('Calibration differs from the validation-selected model')


def audit_recording_identity(rows, root, out):
    seen, records, collisions = {}, [], []
    for row in rows:
        if not row['c3d']:
            continue
        record = dict(id=row['id'], partition=row['partition'])
        for kind in ('imu', 'c3d'):
            sha = digest(root / row[kind])
            record[kind + '_sha256'] = sha
            previous = seen.get((kind, sha))
            if previous and previous['partition'] != row['partition']:
                collisions.append(dict(kind=kind, first=previous['id'], second=row['id']))
            seen[(kind, sha)] = record
        records.append(record)
    save_json(out / 'input_identity_audit.json', dict(records=records, cross_partition_collisions=collisions))
    if collisions:
        raise RuntimeError('Exact recording duplicates cross partitions; final evaluation refused')
    return digest(out / 'input_identity_audit.json')


def settings(root):
    config = yaml.safe_load((root / 'config/default.yaml').read_text())
    return dict(hz=100., max_lag_s=float(config['sync']['max_lag_s']),
                min_sync_corr=float(config['synchronization']['minimum_correlation']),
                min_peak_matches=2, peak_tolerance_s=.20, peak_distance_s=.4,
                peak_prominence=.35, ambiguity_margin=.025,
                max_imu_gap_s=.10, min_valid_s=3., derivative_hz=6.,
                wheel_radius_m=float(config['chair']['R']),
                track_width_m=float(config['chair']['L_hub']),
                marker_separation_m=float(config['chair']['L_hub']) + 2 * float(config['chair']['reflector_offset_m']),
                marker_tolerance_m=float(config['mocap']['axle_tol']),
                distance_intervals_m=[1., 5., 10.],
                accel_range_g=2., gyro_range_dps=2000.,
                encoding='unknown; empirical training-only calibration',
                coordinate_plane='C3D XY; verify QTM Z-up convention before publication')


def inventory(root, out):
    """Inspect filenames only: no held-out signal is opened here."""
    split_path = out / 'split.json'
    if split_path.exists():
        split = json.loads(split_path.read_text())
    else:
        rng = np.random.default_rng(42)
        assignments = {}
        for start in (1, 11):
            people = rng.permutation(np.arange(start, start + 10))
            for ids, part in ((people[:6], 'train'), (people[6:8], 'validation'), (people[8:], 'test')):
                assignments.update({f'No.{int(i)}': part for i in ids})
        split = dict(seed=42, unit='participant before windowing', assignments=assignments,
                     earlier_participants='train only; user confirms no target overlap',
                     target_identity='user confirms No.1-20 are distinct people')
        save_json(split_path, split)
    assignments = split['assignments']
    assert sorted(assignments) == sorted(f'No.{i}' for i in range(1, 21))
    rows = []
    for date_dir in sorted((root / 'imu3').iterdir()):
        if not date_dir.is_dir():
            continue
        date = date_dir.name
        for imu in sorted((date_dir / 'imu').rglob('*.csv')):
            cond = imu.parent.name
            if date in DATES:
                m = re.fullmatch(r'(.+)_Trial(\d+)_No\.(\d+)', imu.stem)
                if m:
                    person = 'No.' + m[3]
                    part = assignments[person]
                    c3d = root / 'c3d' / date / cond / (imu.stem + '.c3d')
                    rep = int(m[2])
                else:
                    person, part, rep, c3d = 'unmapped', 'quarantine', 0, None
            else:
                part, person = 'train', 'earlier-unmapped'
                m = re.search(r'(?:Trial|trial_)(\d+)', imu.stem)
                rep = int(m[1]) if m else 0
                if date == '2026-09-19':
                    person = 'earlier:' + imu.stem.rsplit('_', 1)[-1]
                    c3d = date_dir / 'c3d' / f'{cond} {rep}.c3d'
                else:
                    c3d = date_dir / 'c3d' / cond / (imu.stem + '.c3d')
            paired = c3d is not None and c3d.exists()
            rows.append(dict(id=f'{date}__{cond}__{imu.stem}', date=date,
                             setup=date, condition=cond, participant=person,
                             repetition=rep, partition=part,
                             imu=str(imu.relative_to(root)),
                             c3d=str(c3d.relative_to(root)) if paired else '',
                             status='paired_by_acquisition_name' if paired else 'quarantine_unpaired',
                             pairing_basis='canonical identity' if date in DATES else 'original acquisition condition/trial',
                             imu_bytes=imu.stat().st_size))
    write_csv(out / 'inventory.csv', rows)
    save_json(out / 'inventory.json', rows)
    for part in ('train', 'validation', 'test', 'quarantine'):
        print(part, sum(r['partition'] == part and bool(r['c3d']) for r in rows), 'paired trials', flush=True)
    return rows


def runs(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def reference(path, cfg):
    c = ezc3d.c3d(str(path))
    p = c['parameters']['POINT']
    labels = [x.strip() for x in p['LABELS']['value']]
    ids = [labels.index(name) for name in ('L_FAL', 'R_FAL')]
    unit = p['UNITS']['value'][0].strip().lower()
    if unit not in ('mm', 'm', 'cm'):
        raise ValueError(f'Unsupported C3D units: {unit}')
    scale = dict(mm=.001, cm=.01, m=1.)[unit]
    points = c['data']['points'][:3, ids, :].transpose(2, 1, 0) * scale
    residual = c['data']['meta_points']['residuals'][0, ids, :].T
    hz = float(c['header']['points']['frame_rate'])
    t = np.arange(len(points)) / hz
    sep = np.linalg.norm(points[:, 0] - points[:, 1], axis=1)
    valid = ((residual >= 0).all(axis=1) & np.isfinite(points).all(axis=(1, 2))
             & (np.abs(sep - cfg['marker_separation_m']) <= cfg['marker_tolerance_m'])
             & (np.linalg.norm(points, axis=2) > 1e-8).all(axis=1))
    xy = points[:, :, :2].mean(axis=1)
    lateral = points[:, 0, :2] - points[:, 1, :2]
    heading = np.arctan2(-lateral[:, 0], lateral[:, 1])
    speed = np.full(len(t), np.nan)
    yaw = np.full(len(t), np.nan)
    deriv_valid = np.zeros(len(t), bool)
    sos = signal.butter(2, min(cfg['derivative_hz'], .4 * hz), fs=hz, output='sos')
    for a, b in runs(valid):
        if b - a < max(20, int(.4 * hz)):
            continue
        smooth_xy = signal.sosfiltfilt(sos, xy[a:b], axis=0)
        psi = signal.sosfiltfilt(sos, np.unwrap(heading[a:b]))
        vel = np.gradient(smooth_xy, 1 / hz, axis=0)
        speed[a:b] = vel[:, 0] * np.cos(psi) + vel[:, 1] * np.sin(psi)
        yaw[a:b] = np.gradient(psi, 1 / hz)
        # Derivatives at segment boundaries are not reference labels.
        edge = max(2, int(.15 * hz))
        deriv_valid[a + edge:b - edge] = True
    return dict(t=t, xy=xy, heading=heading, speed=speed, yaw=yaw,
                valid=valid, derivative_valid=deriv_valid, hz=hz,
                raw_coverage=float(valid.mean()))


def imu_streams(path):
    codes = {'L': 0, 'R': 1, 'C': 2}
    data = np.loadtxt(path, delimiter=',', skiprows=1,
                      usecols=(1, 3, 4, 5, 6, 7, 8, 9, 10, 13),
                      converters={1: lambda x: codes[x.decode() if isinstance(x, bytes) else x]})
    streams = []
    anchor = data[:, 2].min() / 1e9
    for code in range(3):
        s = data[data[:, 0] == code]
        if len(s) < 100:
            raise ValueError('Missing or very short L/R/C IMU stream')
        device = s[:, 1] / 1e6
        if np.any(np.diff(device) <= 0):
            raise ValueError('Non-monotonic device clock; rollover/session reset requires explicit handling')
        pc = s[:, 2] / 1e9 - anchor
        last = np.r_[np.diff(pc) != 0, True]
        dt = device - device[0]
        if last.sum() < 5:
            raise ValueError('Too few packet timestamps for clock alignment')
        initial = np.polyfit(dt[last], pc[last], 1)
        fit = optimize.least_squares(lambda x: x[0] * dt[last] + x[1] - pc[last], initial,
                                     loss='soft_l1', f_scale=.01)
        if not .995 < fit.x[0] < 1.005:
            raise ValueError('Implausible device/PC clock scale')
        t = fit.x[0] * dt + fit.x[1]
        streams.append(dict(t=t, raw=s[:, 3:9], missing=int(s[:, 9].sum()),
                            hz=float(1 / np.median(np.diff(device))),
                            clock_scale=float(fit.x[0]),
                            clock_residual_ms=float(np.median(np.abs(fit.fun)) * 1000)))
    return streams


def sample_streams(streams, cfg):
    lo, hi = max(s['t'][0] for s in streams), min(s['t'][-1] for s in streams)
    t = np.arange(lo, hi, 1 / cfg['hz'])
    raw = np.column_stack([np.column_stack([np.interp(t, s['t'], s['raw'][:, j]) for j in range(6)]) for s in streams])
    valid = np.ones(len(t), bool)
    for s in streams:
        i = np.clip(np.searchsorted(s['t'], t), 1, len(s['t']) - 1)
        valid &= (s['t'][i] - s['t'][i - 1]) <= cfg['max_imu_gap_s']
    return t, raw, valid


def masked_interp(t, source_t, values, mask, gap_factor=1.5):
    idx = np.clip(np.searchsorted(source_t, t), 1, len(source_t) - 1)
    good = (mask[idx] & mask[idx - 1] & (t >= source_t[0]) & (t <= source_t[-1])
            & (source_t[idx] - source_t[idx - 1] <= gap_factor * np.median(np.diff(source_t))))
    result = np.interp(t, source_t, np.nan_to_num(values))
    result[~good] = np.nan
    return result, good


def smooth_standard(values, hz):
    x = signal.sosfiltfilt(signal.butter(2, 2., fs=hz, output='sos'), values)
    spread = np.std(x)
    return (x - np.mean(x)) / max(spread, 1e-8)


def synchronize(t, raw, imu_valid, gt, cfg):
    """Multi-peak offset candidates; absolute rates avoid unknown signs/scales."""
    choices = [('yaw', np.linalg.norm(raw[:, 15:18], axis=1), np.abs(gt['yaw'])),
               ('speed', np.linalg.norm(raw[:, 3:6], axis=1) + np.linalg.norm(raw[:, 9:12], axis=1), np.abs(gt['speed']))]
    for mode, imu_feature, gt_feature in choices:
        ref_mask = gt['derivative_valid'] & np.isfinite(gt_feature)
        if ref_mask.sum() < 100 or np.nanstd(gt_feature[ref_mask]) < (.025 if mode == 'yaw' else .03):
            continue
        a = smooth_standard(imu_feature, cfg['hz'])
        # Filled values are used for peak search only, never for metric labels.
        filled = np.interp(gt['t'], gt['t'][ref_mask], gt_feature[ref_mask])
        b = smooth_standard(filled, gt['hz'])
        pi = signal.find_peaks(a, prominence=cfg['peak_prominence'], distance=cfg['hz'] * cfg['peak_distance_s'])[0]
        pg = signal.find_peaks(b, prominence=cfg['peak_prominence'], distance=gt['hz'] * cfg['peak_distance_s'])[0]
        pi, pg = pi[imu_valid[pi]], pg[ref_mask[pg]]
        if min(len(pi), len(pg)) < cfg['min_peak_matches']:
            continue
        # Bound peak pair work on long trials; selection uses prominence rank.
        pi = pi[np.argsort(a[pi])[-100:]]
        pg = pg[np.argsort(b[pg])[-100:]]
        offsets = (t[pi, None] - gt['t'][pg][None, :]).ravel()
        offsets = offsets[np.abs(offsets) <= cfg['max_lag_s']]
        if len(offsets) == 0:
            continue
        bins = np.unique(np.round(offsets / .025) * .025)
        scores = []
        # Evaluation at 20 Hz reduces work; true sample rates govern final labels.
        stride = max(1, round(gt['hz'] / 20))
        rt, rb, rm = gt['t'][::stride], b[::stride], ref_mask[::stride]
        for lag in bins:
            query = rt + lag
            idx = np.clip(np.searchsorted(t, query), 0, len(t) - 1)
            ok = rm & imu_valid[idx] & (query >= t[0]) & (query <= t[-1])
            if ok.sum() < 60:
                continue
            ai = np.interp(query[ok], t, a)
            corr = float(np.corrcoef(ai, rb[ok])[0, 1])
            nearest = np.min(np.abs(t[pi, None] - (gt['t'][pg][None, :] + lag)), axis=0)
            matches = int((nearest < cfg['peak_tolerance_s']).sum())
            if np.isfinite(corr) and matches >= cfg['min_peak_matches']:
                scores.append((corr, float(lag), matches))
        if not scores:
            continue
        scores.sort(reverse=True)
        best = scores[0]
        runner = next((s for s in scores[1:] if abs(s[1] - best[1]) > .5), None)
        ambiguous = runner is not None and best[0] - runner[0] < cfg['ambiguity_margin']
        if best[0] >= cfg['min_sync_corr'] and not ambiguous:
            return dict(offset_s=best[1], correlation=best[0], matched_peaks=best[2], source=mode)
    raise ValueError('Synchronization rejected: insufficient peaks, correlation, or unique offset')


def prepare(row, root, out, cfg):
    path = out / 'cache' / (row['id'] + '.npz')
    meta_path = path.with_suffix('.json')
    fingerprint = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
    signature = dict(settings_sha256=fingerprint,
                     imu_sha256=digest(root / row['imu']), c3d_sha256=digest(root / row['c3d']))
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta['signature'] == signature:
            with np.load(path) as z:
                return {k: z[k] for k in z.files}, meta
    gt = reference(root / row['c3d'], cfg)
    streams = imu_streams(root / row['imu'])
    t, raw, iv = sample_streams(streams, cfg)
    sync = synchronize(t, raw, iv, gt, cfg)
    ref_t = t - sync['offset_s']
    keep = (ref_t >= 0) & (ref_t <= gt['t'][-1])
    t, raw, iv, ref_t = t[keep], raw[keep], iv[keep], ref_t[keep]
    gx, vx = masked_interp(ref_t, gt['t'], gt['xy'][:, 0], gt['valid'])
    gy, vy = masked_interp(ref_t, gt['t'], gt['xy'][:, 1], gt['valid'])
    # Unwrap each valid segment; angle metrics are circular, no gap label is created.
    psi = gt['heading'].copy()
    for a, b in runs(gt['valid']):
        psi[a:b] = np.unwrap(psi[a:b])
    heading, vh = masked_interp(ref_t, gt['t'], psi, gt['valid'])
    v, vm = masked_interp(ref_t, gt['t'], gt['speed'], gt['derivative_valid'])
    yaw, ym = masked_interp(ref_t, gt['t'], gt['yaw'], gt['derivative_valid'])
    valid = vx & vy & vh
    first = np.flatnonzero(valid & iv)
    if not len(first):
        raise ValueError('No valid initial reference pose')
    start = first[0]
    t, raw, iv, ref_t = t[start:], raw[start:], iv[start:], ref_t[start:]
    gx, gy, heading, v, yaw, valid, vm, ym = [x[start:] for x in (gx, gy, heading, v, yaw, valid, vm, ym)]
    label_valid = valid & vm & ym & iv
    if label_valid.sum() / cfg['hz'] < cfg['min_valid_s']:
        raise ValueError('Insufficient valid derivative labels')
    data = dict(t=t - t[0], ref_t=ref_t, raw=raw, imu_valid=iv, gt_xy=np.c_[gx, gy],
                gt_heading=heading, gt_v=v, gt_yaw=yaw, gt_valid=valid, label_valid=label_valid)
    meta = dict(signature=signature, synchronization=sync, reference_hz=gt['hz'],
                reference_raw_coverage=gt['raw_coverage'], score_coverage=float(valid.mean()),
                streams=[{k: value for k, value in s.items() if k not in ('t', 'raw')} for s in streams])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + '.tmp.npz')
    np.savez_compressed(temporary, **data)
    temporary.replace(path)
    save_json(meta_path, meta)
    return data, meta


def collect(rows, partition, root, out, cfg):
    accepted, qc = [], []
    selected = [r for r in rows if r['partition'] == partition]
    for i, row in enumerate(selected):
        record = {k: row[k] for k in ('id', 'partition', 'participant', 'condition', 'date')}
        if not row['c3d']:
            qc.append(dict(record, status='excluded', reason='No unambiguous paired C3D'))
            continue
        try:
            data, meta = prepare(row, root, out, cfg)
            accepted.append((row, data, meta))
            qc.append(dict(record, status='accepted', reason='',
                           coverage=meta['score_coverage'], sync_correlation=meta['synchronization']['correlation'],
                           sync_offset_s=meta['synchronization']['offset_s'], sync_source=meta['synchronization']['source']))
        except Exception as exc:
            qc.append(dict(record, status='excluded', reason=f'{type(exc).__name__}: {exc}'))
        if (i + 1) % 10 == 0:
            print(f'{partition}: {i + 1}/{len(selected)} processed, {len(accepted)} accepted', flush=True)
    write_csv(out / f'qc_{partition}.csv', qc)
    return accepted


def robust_line(x, y):
    finite = np.isfinite(x) & np.isfinite(y)
    x, y = x[finite], y[finite]
    if len(x) < 500 or np.std(x) < 1:
        raise ValueError('Insufficient excitation for empirical calibration')
    xs = max(float(np.std(x)), 1.)
    xx = np.c_[x / xs, np.ones(len(x))]
    beta = np.linalg.lstsq(xx, y, rcond=None)[0]
    for _ in range(6):
        residual = xx @ beta - y
        mad = max(float(np.median(np.abs(residual - np.median(residual)))) * 1.4826, .005)
        w = np.minimum(1., 1.5 * mad / np.maximum(np.abs(residual), 1e-9))
        beta = np.linalg.lstsq(xx * np.sqrt(w[:, None]), y * np.sqrt(w), rcond=None)[0]
    error = float(np.mean((xx @ beta - y) ** 2))
    return dict(scale=float(beta[0] / xs), intercept=float(beta[1]), mse=error)


def calibrate(trials, cfg):
    calibrated = {}
    for setup in sorted({r['setup'] for r, _, _ in trials}):
        selected = [(r, d) for r, d, _ in trials if r['setup'] == setup]
        raw = np.concatenate([d['raw'][d['label_valid']][::5] for _, d in selected])
        speed = np.concatenate([d['gt_v'][d['label_valid']][::5] for _, d in selected])
        yaw = np.concatenate([d['gt_yaw'][d['label_valid']][::5] for _, d in selected])
        terms = []
        for sensor_index, target in enumerate((speed - cfg['track_width_m'] * yaw / 2,
                                                speed + cfg['track_width_m'] * yaw / 2, yaw)):
            fits = []
            for axis in range(3):
                try:
                    f = robust_line(raw[:, sensor_index * 6 + 3 + axis], target)
                    fits.append(dict(f, column=sensor_index * 6 + 3 + axis, axis=AXES[axis]))
                except ValueError:
                    continue
            if not fits:
                raise ValueError(f'No identifiable calibration for setup {setup}, sensor {sensor_index}')
            terms.append(min(fits, key=lambda f: f['mse']))
        calibrated[setup] = dict(terms=terms, source='training only; empirical raw-to-motion calibration',
                                 training_trials=[r['id'] for r, _ in selected], n_labels=len(speed))
    return calibrated


def velocities(data, calibration):
    terms = calibration['terms']
    values = [data['raw'][:, f['column']] * f['scale'] + f['intercept'] for f in terms]
    return np.c_[(values[0] + values[1]) / 2, values[2]]


def quiet_intervals(data, calibration, cfg):
    """IMU-only diagnostic; never refit held-out bias or reset the estimate."""
    terms = calibration['terms']
    values = [data['raw'][:, f['column']] * f['scale'] + f['intercept'] for f in terms]
    norm = np.linalg.norm(data['raw'][:, 12:15], axis=1)
    window = int(cfg['hz'])
    mean = uniform_filter1d(norm, size=window, mode='nearest')
    spread = np.sqrt(np.maximum(uniform_filter1d(norm ** 2, size=window, mode='nearest') - mean ** 2, 0))
    candidate = ((np.abs(values[0]) < .02) & (np.abs(values[1]) < .02)
                 & (np.abs(values[2]) < .02) & (spread / np.maximum(mean, 1) < .02)
                 & data['imu_valid'])
    quiet = np.zeros(len(candidate), bool)
    for a, b in runs(candidate):
        if b - a >= window:
            quiet[a:b] = True
    return quiet


def integrate(t, motion, initial_xy, initial_heading, imu_valid):
    xy = np.full((len(t), 2), np.nan)
    heading = np.full(len(t), np.nan)
    xy[0], heading[0] = initial_xy, initial_heading
    # ponytail: stop at an IMU gap instead of inventing motion; add uncertainty-aware propagation if dropout support is needed.
    for i in range(1, len(t)):
        if not imu_valid[i - 1:i + 1].all() or not np.isfinite(xy[i - 1]).all():
            break
        dt = t[i] - t[i - 1]
        v, yaw = (motion[i] + motion[i - 1]) / 2
        heading[i] = heading[i - 1] + yaw * dt
        middle = (heading[i] + heading[i - 1]) / 2
        xy[i] = xy[i - 1] + v * dt * np.array([np.cos(middle), np.sin(middle)])
    return xy, heading


def metrics(data, xy, heading, cfg):
    valid = data['gt_valid'] & np.isfinite(xy).all(axis=1)
    if valid.sum() < 20:
        raise ValueError('Too little scorable reconstruction')
    errors = np.linalg.norm(xy[valid] - data['gt_xy'][valid], axis=1)
    hd = np.arctan2(np.sin(heading[valid] - data['gt_heading'][valid]),
                    np.cos(heading[valid] - data['gt_heading'][valid]))
    adjacent = data['gt_valid'][1:] & data['gt_valid'][:-1]
    steps = np.linalg.norm(np.diff(data['gt_xy'], axis=0), axis=1)
    path_length = float(np.sum(steps[adjacent]))
    result = dict(position_rmse_m=float(np.sqrt(np.mean(errors ** 2))),
                  heading_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(hd ** 2)))),
                  reference_coverage=float(data['gt_valid'].mean()),
                  reconstruction_coverage=float(np.isfinite(xy).all(axis=1).mean()),
                  scored_frames=int(valid.sum()), reference_path_valid_m=path_length,
                  endpoint_drift_m='', endpoint_drift_percent='', endpoint_valid=False)
    if valid[-1]:
        endpoint = float(np.linalg.norm(xy[-1] - data['gt_xy'][-1]))
        result.update(endpoint_drift_m=endpoint, endpoint_valid=True)
        # Percent is withheld when the reference path crosses gaps.
        if data['gt_valid'].all() and path_length > 1:
            result['endpoint_drift_percent'] = 100 * endpoint / path_length
    for distance in cfg['distance_intervals_m']:
        local_errors = []
        for a, b in runs(valid):
            positions = data['gt_xy'][a:b]
            travelled = np.r_[0., np.cumsum(np.linalg.norm(np.diff(positions, axis=0), axis=1))]
            start = 0
            while start < len(travelled):
                end = int(np.searchsorted(travelled, travelled[start] + distance))
                if end >= len(travelled):
                    break
                angle = data['gt_heading'][a + start] - heading[a + start]
                rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
                delta = rot @ (xy[a + end] - xy[a + start]) - (positions[end] - positions[start])
                local_errors.append(float(np.linalg.norm(delta)))
                start = end
        result[f'relative_{distance:g}m_rmse_m'] = float(np.sqrt(np.mean(np.square(local_errors)))) if local_errors else ''
        result[f'relative_{distance:g}m_segments'] = len(local_errors)
    return result


def summarize(rows):
    people = sorted({r['participant'] for r in rows})
    by_person = []
    for person in people:
        group = [r for r in rows if r['participant'] == person]
        by_person.append(dict(participant=person, trials=len(group),
                              mean_trial_position_rmse_m=float(np.mean([r['position_rmse_m'] for r in group])),
                              mean_trial_heading_rmse_deg=float(np.mean([r['heading_rmse_deg'] for r in group]))))
    summary = dict(trials=len(rows), participants=len(people),
                   equal_participant_mean_position_rmse_m=float(np.mean([r['mean_trial_position_rmse_m'] for r in by_person])) if rows else None,
                   equal_participant_mean_heading_rmse_deg=float(np.mean([r['mean_trial_heading_rmse_deg'] for r in by_person])) if rows else None)
    by_condition = []
    for cond in sorted({r['condition'] for r in rows}):
        group = [r for r in rows if r['condition'] == cond]
        means = [np.mean([r['position_rmse_m'] for r in group if r['participant'] == person])
                 for person in sorted({r['participant'] for r in group})]
        by_condition.append(dict(condition=cond, trials=len(group), participants=len(means),
                                 equal_participant_mean_position_rmse_m=float(np.mean(means))))
    return summary, by_person, by_condition


def plot_and_export(path, row, data, motion, xy, heading, result, quiet):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    path.mkdir(parents=True, exist_ok=True)
    export = np.c_[data['t'], data['ref_t'], xy, heading, motion, data['gt_xy'], data['gt_heading'], data['gt_valid'], data['imu_valid'], quiet]
    np.savetxt(path / (row['id'] + '.csv'), export, delimiter=',',
               header='time_s,c3d_time_s,x_m,y_m,heading_rad,speed_m_s,yaw_rad_s,reference_x_m,reference_y_m,reference_heading_rad,reference_valid,imu_valid,imu_quiet', comments='')
    fig, ax = plt.subplots(figsize=(6, 5))
    gt = data['gt_xy'].copy()
    gt[~data['gt_valid']] = np.nan
    ax.plot(gt[:, 0], gt[:, 1], label='Qualisys reference', lw=1.5)
    ax.plot(xy[:, 0], xy[:, 1], label='Reconstruction', lw=1.)
    ax.scatter(*xy[0], label='Initial pose', s=20)
    ax.set(xlabel='X (m)', ylabel='Y (m)', title=f"{row['id']}\nPosition RMSE {result['position_rmse_m']:.3f} m")
    ax.set_aspect('equal', adjustable='datalim')
    ax.legend()
    fig.tight_layout()
    fig.savefig(path / (row['id'] + '.png'), dpi=150)
    plt.close(fig)


def evaluate(trials, calibration, cfg, out, name='baseline', predictor=None, export=True):
    rows, failures = [], []
    for row, data, _ in trials:
        try:
            base = velocities(data, calibration[row['setup']])
            motion = predictor(data, base) if predictor else base
            xy, heading = integrate(data['t'], motion, data['gt_xy'][0], data['gt_heading'][0], data['imu_valid'])
            result = metrics(data, xy, heading, cfg)
            quiet = quiet_intervals(data, calibration[row['setup']], cfg)
            result['imu_quiet_s'] = float(quiet.sum() / cfg['hz'])
            result['initial_5s_imu_quiet_s'] = float(quiet[data['t'] < 5].sum() / cfg['hz'])
            result.update({k: row[k] for k in ('id', 'participant', 'condition', 'partition')})
            rows.append(result)
            if export:
                plot_and_export(out / name / row['partition'] / 'trajectories', row, data, motion, xy, heading, result, quiet)
        except Exception as exc:
            failures.append(dict(id=row['id'], participant=row['participant'], reason=str(exc)))
    folder = out / name
    folder.mkdir(parents=True, exist_ok=True)
    summary, by_person, by_condition = summarize(rows)
    summary['failed_reconstructions'] = failures
    partition = trials[0][0]['partition'] if trials else 'empty'
    write_csv(folder / f'{partition}_metrics.csv', rows)
    write_csv(folder / f'{partition}_participants.csv', by_person)
    write_csv(folder / f'{partition}_maneuvers.csv', by_condition)
    save_json(folder / f'{partition}_summary.json', summary)
    return summary


def validation_report(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    selection = json.loads((out / 'selection.json').read_text())
    train_qc = list(csv.DictReader((out / 'qc_train.csv').open(encoding='utf-8')))
    val_qc = list(csv.DictReader((out / 'qc_validation.csv').open(encoding='utf-8')))
    baseline = selection['candidates']['baseline']['equal_participant_mean_position_rmse_m']
    selected = selection['candidates'][selection['selected']]['equal_participant_mean_position_rmse_m']
    test_status = ('Final test has been opened under a frozen protocol; see final_test_report.md.'
                   if (out / 'final_test_lock.json').exists() else 'Final test recordings remain unopened.')
    text = ['# Validation report', '', f'**{test_status}**', '',
            f"Selected model: **{selection['selected']}**. Selection uses equal-participant mean trial position RMSE.", '',
            f"Training QC: {sum(r['status'] == 'accepted' for r in train_qc)}/{len(train_qc)} trials accepted.",
            f"Validation QC: {sum(r['status'] == 'accepted' for r in val_qc)}/{len(val_qc)} trials accepted across four reserved participants.", '',
            '| Candidate | Validation position RMSE (m) |', '|---|---:|']
    names, values = [], []
    for name, candidate in selection['candidates'].items():
        value = candidate['equal_participant_mean_position_rmse_m']
        names.append(name)
        values.append(value)
        text.append(f'| {name} | {value:.4f} |')
    text.extend(['', f'Selected-model reduction relative to baseline: **{100 * (baseline - selected) / baseline:.1f}%**.', '',
                 '## Validation exclusions', ''])
    counts = {}
    for row in val_qc:
        if row['status'] != 'accepted':
            counts[row['reason']] = counts.get(row['reason'], 0) + 1
    text.extend(f'- {count}: {reason}' for reason, count in counts.items())
    text.extend(['', '## Interpretation', '',
                 'These results guide model development. The selected checkpoint was chosen on these validation participants; this is not an independent final performance estimate. Report all QC exclusions and coverage alongside accuracy.', '',
                 'Sensor conversion is empirical because CSV integer encoding remains unverified. Reconstruction assumes a known initial pose, evaluation-only MoCap clock alignment, symmetric hub markers, and C3D XY as the horizontal plane.', '',
                 'Trial, participant, and maneuver tables and trajectory plots are available in the baseline and selected-model output folders. The participant split, calibration, normalization, model weights, and selection record must accompany any final evaluation.'])
    (out / 'validation_report.md').write_text('\n'.join(text) + '\n', encoding='utf-8')
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(names, values, color=['#64748b' if n != selection['selected'] else '#0f766e' for n in names])
    ax.bar_label(bars, labels=[f'{v:.3f}' for v in values], padding=3)
    ax.set(ylabel='Equal-participant mean position RMSE (m)', title='Validation only: 70 trials, 4 held-out participants')
    ax.set_ylim(0, max(values) * 1.18)
    fig.tight_layout()
    fig.savefig(out / 'validation_comparison.png', dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inventory', 'baseline', 'learn', 'report', 'final-test'))
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs')
    parser.add_argument('--epochs', type=int, default=12)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('--epochs must be positive')
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = inventory(root, out)
    if args.command == 'inventory':
        return
    cfg = settings(root)
    locked = out / 'final_test_lock.json'
    if locked.exists() and args.command != 'final-test':
        raise RuntimeError('Final test already opened. Development in this output directory is locked.')
    if args.command == 'baseline':
        train = collect(rows, 'train', root, out, cfg)
        calibration = calibrate(train, cfg)
        if not all(date in calibration for date in DATES):
            raise RuntimeError('Training calibration missing for a target acquisition setup')
        save_json(out / 'calibration.json', calibration)
        save_json(out / 'run.json', dict(created_utc=datetime.now(timezone.utc).isoformat(), settings=cfg,
                    split_sha256=digest(out / 'split.json'), config_sha256=digest(root / 'config/default.yaml'),
                    code_sha256=digest(Path(__file__)), python=sys.version, platform=platform.platform(),
                    numpy=np.__version__, scipy=scipy.__version__, ezc3d=getattr(ezc3d, '__version__', 'unknown'),
                    training_accepted=len(train), test_opened=False))
        validation = collect(rows, 'validation', root, out, cfg)
        result = evaluate(validation, calibration, cfg, out)
        print(json.dumps(result, indent=2), flush=True)
    else:
        stored = json.loads((out / 'run.json').read_text())
        if stored['settings'] != cfg or stored['split_sha256'] != digest(out / 'split.json'):
            raise RuntimeError('Settings or split changed: rebuild baseline in a new output directory')
        calibration = json.loads((out / 'calibration.json').read_text())
        if args.command == 'learn':
            from learning import train_and_select
            train_and_select(rows, root, out, cfg, calibration, args.epochs)
            validation_report(out)
        elif args.command == 'report':
            selection = json.loads((out / 'selection.json').read_text())
            verify_selection(out, selection)
            validation = collect(rows, 'validation', root, out, cfg)
            evaluate(validation, calibration, cfg, out, name='baseline')
            if selection['selected'] != 'baseline':
                from learning import load_predictor
                evaluate(validation, calibration, cfg, out, name=selection['selected'], predictor=load_predictor(out, selection['selected']))
            validation_report(out)
            save_json(out / 'report_provenance.json', dict(code_sha256=digest(Path(__file__)),
                      config_sha256=digest(root / 'config/default.yaml'), artifacts=selected_artifacts(out, selection['selected'])))
            print('Validation report refreshed; final test remains unopened.', flush=True)
        else:
            selection_path = out / 'selection.json'
            if not selection_path.exists():
                raise RuntimeError('Run learn to freeze validation-based model selection before final-test')
            selection = json.loads(selection_path.read_text())
            verify_selection(out, selection)
            input_audit_sha = audit_recording_identity(rows, root, out)
            freeze = dict(selection_sha256=digest(selection_path), split_sha256=digest(out / 'split.json'),
                          calibration_sha256=digest(out / 'calibration.json'), code_sha256=digest(Path(__file__)),
                          learning_code_sha256=digest(ROOT / 'learning.py'), selected=selection['selected'],
                          artifacts=selected_artifacts(out, selection['selected']),
                          inventory_sha256=digest(out / 'inventory.json'), input_audit_sha256=input_audit_sha)
            if locked.exists():
                if json.loads(locked.read_text())['freeze'] != freeze:
                    raise RuntimeError('Frozen inputs changed after final test was opened')
            else:
                save_json(locked, dict(opened_utc=datetime.now(timezone.utc).isoformat(), freeze=freeze))
            trials = collect(rows, 'test', root, out, cfg)
            baseline_result = evaluate(trials, calibration, cfg, out, name='baseline')
            selected_result = baseline_result
            if selection['selected'] != 'baseline':
                from learning import load_predictor
                selected_result = evaluate(trials, calibration, cfg, out, name=selection['selected'],
                                           predictor=load_predictor(out, selection['selected']))
            final_qc = list(csv.DictReader((out / 'qc_test.csv').open(encoding='utf-8')))
            b = baseline_result['equal_participant_mean_position_rmse_m']
            s = selected_result['equal_participant_mean_position_rmse_m']
            report = ['# Final held-out test report', '',
                      'The estimator and selection artifacts were frozen before these test signals were processed. Development in this output directory is now locked.', '',
                      f"Selected estimator: **{selection['selected']}** (chosen on validation only).", '',
                      f"QC: {len(trials)}/{len(final_qc)} test trials accepted; {selected_result['trials']} scored across {selected_result['participants']} participants.", '',
                      '| Estimator | Equal-participant mean position RMSE (m) |', '|---|---:|',
                      f'| Physics baseline | {b:.4f} |' if b is not None else '| Physics baseline | unavailable |',
                      f"| {selection['selected']} | {s:.4f} |" if s is not None else '| Selected model | unavailable |', '',
                      'QC failures, coverage, trial metrics, participant means, maneuver means, and trajectory exports are saved alongside this report. Report exclusions and the empirical calibration, known initial pose, external clock alignment, and XY-plane assumptions with these results.', '']
            (out / 'final_test_report.md').write_text('\n'.join(report), encoding='utf-8')
            validation_report(out)
            save_json(out / 'final_test_summary.json', dict(baseline=baseline_result, selected=selected_result,
                       selected_name=selection['selected'], attempted_trials=len(final_qc), accepted_trials=len(trials),
                       freeze=freeze))
            print(json.dumps(dict(baseline=baseline_result, selected=selected_result), indent=2), flush=True)
            print('Final test complete. Development is locked in this output directory.', flush=True)


if __name__ == '__main__':
    main()
