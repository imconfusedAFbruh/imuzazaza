"""Independent finite-difference and scalar-equivalence checks on synthetic paths."""
import unittest
import numpy as np
import trial_rmse_v124 as previous
from axis_prior_v125 import objective, fit


class AxisPriorChecks(unittest.TestCase):
    def entries(self):
        from test_trial_rmse_v124 import TrialRMSEChecks
        return TrialRMSEChecks().entries()

    def test_asymmetric_gradients_all_columns_with_saturation(self):
        rng = np.random.default_rng(125)
        es = self.entries()
        prior = rng.normal(0, .01, (17, 2))
        for penalties in ((1., 10.), (10., 1.)):
            for scale in (.02, 3.):
                weights = rng.normal(0, scale, (17, 2))
                _, _, rhs = objective(es, weights, penalties, prior, True)
                for column in range(34):
                    plus, minus = weights.copy(), weights.copy()
                    plus[column % 17, column // 17] += 1e-6
                    minus[column % 17, column // 17] -= 1e-6
                    numeric = (objective(es, plus, penalties, prior)-
                               objective(es, minus, penalties, prior))/2e-6
                    self.assertAlmostEqual(numeric, -2*rhs[column], delta=3e-6)

    def test_equal_axes_exact_scalar_equivalence(self):
        es = self.entries()
        rng = np.random.default_rng(125)
        prior, weights = rng.normal(0, .05, (2, 17, 2))
        actual = objective(es, weights, (3., 3.), prior, True)
        expected = previous.objective(es, weights, 3., prior, True)
        for a, b in zip(actual, expected):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(fit(es, (3., 3.), prior), previous.fit(es, 3., prior))

    def test_fit_monotone_deterministic_and_exact_prior(self):
        es = self.entries()
        prior = np.zeros((17, 2))
        np.testing.assert_array_equal(fit(es, (1., 10.), prior)['weights'], prior)
        for e in es:
            e['data']['gt_xy'][:, 0] += .015*e['data']['t']
        fitted = fit(es, (1., 10.), prior)
        self.assertEqual(fitted, fit(es, (1., 10.), prior))
        values = [objective(es, prior, (1., 10.), prior)]+[r['objective'] for r in fitted['history']]
        self.assertTrue(np.all(np.diff(values) <= 0))
        self.assertLess(values[-1], values[0])


if __name__ == '__main__':
    unittest.main()
