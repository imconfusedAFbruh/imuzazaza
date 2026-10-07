import numpy as np


def test_projected_proxy_returns_bias_corrected_gyro_along_gravity():
    from projected_yaw_validation_v54 import projected_proxy

    n = 200
    raw = np.zeros((n, 18), dtype=float)
    raw[:, 14] = 8192.0
    raw[:, 17] = 100.0
    data = {"raw": raw, "imu_valid": np.ones(n, dtype=bool)}
    calibration = {
        "center_gravity_direction": [0.0, 0.0, 1.0],
        "gyro_bias_counts": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 10.0]],
    }

    got = projected_proxy(data, calibration, cutoff_hz=0.3, sample_rate_hz=100.0)

    assert got.shape == (n,)
    assert np.allclose(got, 90.0, atol=1e-8)
