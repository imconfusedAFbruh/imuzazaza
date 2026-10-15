"""Synthetic loss/optimizer checks; never reads recording or validation data."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OPENBLAS_NUM_THREADS'] = '4'
import unittest
import numpy as np
from trial_rmse_v124 import objective, fit, ratio
from reservoir_path_v121 import prediction, self_check
from trajectory_calibration_v10 import integrate


class TrialRMSEChecks(unittest.TestCase):
    def entries(self):
        rng = np.random.default_rng(124)
        entries = []
        for person in ('A', 'A', 'B'):
            n = 121
            d = dict(t=np.r_[0., np.cumsum(rng.uniform(.006, .014, n-1))],
                     gt_xy=np.zeros((n, 2)), gt_heading=np.full(n, .4),
                     imu_valid=np.ones(n, bool))
            base = np.tile([1., .04, .2], (n, 1))
            xy, heading = integrate(d, base)
            d.update(gt_xy=xy, gt_heading=heading,
                     gt_valid=np.ones(n, bool))
            entries.append(dict(data=d, base=base, ix=np.arange(n)[::10],
                                z=np.c_[rng.normal(0, .3, (n, 16)), np.ones(n)],
                                row=dict(participant=person)))
        return entries

    def test_gradient_all_columns_including_clipped_corrections(self):
        rng = np.random.default_rng(124)
        es = self.entries()
        prior = rng.normal(0, .01, (17, 2))
        for scale in (.02, 3.):
            weights = rng.normal(0, scale, (17, 2))
            loss, _, rhs = objective(es, weights, .7, prior, True)
            self.assertTrue(np.isfinite(loss))
            for column in range(34):
                plus, minus = weights.copy(), weights.copy()
                plus[column % 17, column // 17] += 1e-6
                minus[column % 17, column // 17] -= 1e-6
                numeric = (objective(es, plus, .7, prior) -
                           objective(es, minus, .7, prior)) / 2e-6
                self.assertAlmostEqual(numeric, -2*rhs[column], delta=2e-6)

    def test_fit_is_monotone_deterministic_and_preserves_exact_prior(self):
        es = self.entries()
        prior = np.zeros((17, 2))
        exact = fit(es, 1., prior)
        np.testing.assert_array_equal(exact['weights'], prior)
        for e in es:
            e['data']['gt_xy'][:, 0] += .015*e['data']['t']
        fitted = fit(es, 1., prior)
        self.assertEqual(fitted, fit(es, 1., prior))
        values = [objective(es, prior, 1., prior)] + [r['objective'] for r in fitted['history']]
        self.assertTrue(np.all(np.diff(values) <= 0))
        self.assertLess(values[-1], values[0])
        motion = prediction(es[0], np.array(fitted['weights']))[0]
        self.assertTrue(np.isfinite(motion).all())

    def test_existing_trajectory_jacobian_and_zero_baseline_guard(self):
        self_check()
        self.assertEqual(ratio(0., 0.), 1.)
        self.assertGreater(ratio(.001, 0.), 1.05)
        self.assertEqual(ratio(.5, 1.), .5)


if __name__ == '__main__':
    unittest.main()
