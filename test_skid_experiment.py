"""python test_skid_experiment.py: group balance, causal proxy and robust boundary checks."""
import numpy as np
from skid_experiment import balanced_weights, fit_ridge, skid_features

w = balanced_weights(['a', 'a', 'a', 'b'])
assert np.isclose(w[:3].sum(), w[3:].sum())
rng = np.random.default_rng(42)
x = rng.normal(size=(100, 2)); y = x @ np.array([[2.], [3.]]) + 4
coef = fit_ridge(x, y, np.ones(100), 0)
np.testing.assert_allclose(coef[:, 0], [2, 3, 4], atol=1e-10)
p = rng.normal(size=(100, 20)); yaw = rng.normal(size=100); motion = rng.normal(size=(100, 2))
before = skid_features(p, yaw, motion, .1)
p[50:] += 100; yaw[50:] += 100; motion[50:] += 100
np.testing.assert_array_equal(before[:50], skid_features(p, yaw, motion, .1)[:50])
assert np.isfinite(before).all()
print('Group balance, causal skid proxies and training regression checks passed.')
