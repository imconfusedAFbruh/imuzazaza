"""Minimal numeric checks for planar integration and gap-safe labels."""
import numpy as np
from planar_experiment import integrate_planar, lateral_labels
from pipeline import integrate


def main():
    t = np.arange(1001) / 100
    motion = np.tile([1., .2, 0.], (len(t), 1))
    valid = np.ones(len(t), bool)
    xy, heading = integrate_planar(t, motion, np.zeros(2), np.pi / 2, valid)
    assert np.allclose(xy[-1], [-2, 10])
    motion[:, 1] = 0
    xy, heading = integrate_planar(t, motion, np.zeros(2), .3, valid)
    old_xy, old_heading = integrate(t, motion[:, [0, 2]], np.zeros(2), .3, valid)
    assert np.allclose(xy, old_xy) and np.allclose(heading, old_heading)
    valid[500] = False
    xy, _ = integrate_planar(t, motion, np.zeros(2), 0, valid)
    assert np.isfinite(xy[:500]).all() and np.isnan(xy[500:]).all()
    gt_valid = np.ones(len(t), bool)
    gt_valid[400:500] = False
    gt_xy = np.c_[t, .2 * t]
    gt_xy[~gt_valid] = np.nan
    data = dict(t=t, gt_xy=gt_xy, gt_heading=np.where(gt_valid, 0., np.nan),
                gt_valid=gt_valid, label_valid=gt_valid)
    side, mask = lateral_labels(data)
    assert not mask[380:520].any() and np.isnan(side[400:500]).all()
    assert np.allclose(side[mask], .2, atol=1e-3)
    print('Planar integration, zero-lateral equivalence, IMU gap, and reference gap checks pass')


if __name__ == '__main__':
    main()
