import numpy as np


def test_causal_ema_has_no_future_leakage_and_resets_across_invalid_gap():
    from braking_hysteresis_folds_v56 import causal_ema

    t = np.arange(8, dtype=float) * 0.1
    x = np.zeros(8, dtype=float)
    x[3] = 1.0
    valid = np.array([1, 1, 1, 1, 0, 1, 1, 1], dtype=bool)

    y = causal_ema(x, t, valid, tau_s=0.2)

    assert np.allclose(y[:3], 0.0)
    assert y[3] > 0.0
    assert np.isnan(y[4])
    assert y[5] == 0.0
    assert np.allclose(y[5:], 0.0)


def test_hysteresis_features_are_finite_on_valid_support_and_causal():
    from braking_hysteresis_folds_v56 import hysteresis_features

    n = 80
    t = np.arange(n, dtype=float) * 0.01
    raw = np.zeros((n, 18), dtype=float)
    raw[:, 14] = 8200.0
    raw[40:, 12] = -120.0
    raw[:40, 5] = 100.0
    raw[:40, 11] = 100.0
    data = {"t": t, "raw": raw, "imu_valid": np.ones(n, dtype=bool)}
    calibration = {
        "terms": [
            {"column": 5, "scale": 0.002, "intercept": 0.0},
            {"column": 11, "scale": 0.002, "intercept": 0.0},
            {"column": 17, "scale": 0.001, "intercept": 0.0},
        ],
        "accel_counts_per_g": [8200.0, 8200.0, 8200.0],
        "center_gravity_direction": [0.0, 0.0, 1.0],
    }

    f = hysteresis_features(data, calibration)

    assert f.shape[0] == n
    assert np.isfinite(f).all()
    # The acceleration change at frame 40 cannot affect causal history before it.
    baseline = hysteresis_features(
        {"t": t, "raw": np.where(np.arange(n)[:, None] < 40, raw, np.zeros_like(raw)), "imu_valid": np.ones(n, dtype=bool)},
        calibration,
    )
    assert np.allclose(f[:40], baseline[:40])
