"""Independent finite differences for v60's frozen-yaw displacement Jacobian."""
import numpy as np
from trajectory_calibration_v10 import integrate


def main():
    rng = np.random.default_rng(60)
    n, k = 601, 7
    t = np.r_[0., np.cumsum(rng.uniform(.009, .011, n - 1))]
    speed = .7 + .2 * np.sin(t)
    yaw = .4 * np.sin(.8 * t)
    z = rng.normal(size=(n, k))
    motion = np.c_[speed, np.zeros(n), yaw]
    data = dict(t=t, gt_heading=np.full(n, .73), gt_xy=np.tile([1.1, -2.2], (n, 1)),
                imu_valid=np.ones(n, bool))
    xy, heading = integrate(data, motion)
    dt = np.diff(t)
    h = np.r_[0., np.cumsum(dt * (yaw[1:] + yaw[:-1]) / 2)]
    mid = (h[1:] + h[:-1]) / 2
    zm = (z[1:] + z[:-1]) / 2
    jx = np.vstack((np.zeros(k), np.cumsum(dt[:, None] * np.cos(mid)[:, None] * zm, axis=0)))
    jy = np.vstack((np.zeros(k), np.cumsum(dt[:, None] * np.sin(mid)[:, None] * zm, axis=0)))
    maximum = 0.
    eps = 1e-5
    for start, end in [(0, 100), (100, 400), (37, 600)]:
        angle = h[start]
        rot = np.array([[np.cos(angle), np.sin(angle)], [-np.sin(angle), np.cos(angle)]])
        analytic = rot @ np.vstack((jx[end] - jx[start], jy[end] - jy[start])) / (t[end] - t[start])
        a = heading[start]
        world_to_start = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
        for j in range(k):
            high, low = motion.copy(), motion.copy()
            high[:, 0] += eps * z[:, j]
            low[:, 0] -= eps * z[:, j]
            ph, _ = integrate(data, high)
            pl, _ = integrate(data, low)
            numeric = world_to_start @ ((ph[end] - ph[start]) - (pl[end] - pl[start])) / (2 * eps * (t[end] - t[start]))
            maximum = max(maximum, float(np.max(np.abs(numeric - analytic[:, j]))))
    assert maximum < 1e-8, maximum
    print('21 frozen-yaw interval Jacobian columns checked; maximum error:', maximum)


if __name__ == '__main__':
    main()
