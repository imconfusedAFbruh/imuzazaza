"""Dual-control safeguards with synthetic rows; never opens data or a model."""
import unittest
import numpy as np
from frozen_validation_v126 import dual_decision, metric_match
from test_frozen_validation_v123 import rows


class DualValidationContract(unittest.TestCase):
    def test_both_controls_must_pass(self):
        base = rows()
        candidate = [dict(r, position_rmse_m=.9) for r in base]
        self.assertTrue(dual_decision({'v34': base, 'v121': base}, candidate)['eligible'])
        stronger = [dict(r, position_rmse_m=.8) for r in base]
        self.assertFalse(dual_decision({'v34': base, 'v121': stronger}, candidate)['eligible'])
        with self.assertRaises(ValueError):
            dual_decision({'v34': base}, candidate)

    def test_either_control_guard_failure_rejects_candidate(self):
        base = rows()
        candidate = [dict(r, position_rmse_m=.9) for r in base]
        stronger_tail = [dict(r, Position_P95_mm=.9) for r in base]
        self.assertFalse(dual_decision({'v34': base, 'v121': stronger_tail}, candidate)['eligible'])
        broken = candidate[:-1]+[dict(candidate[-1], scored_frames=99)]
        with self.assertRaises(ValueError):
            dual_decision({'v34': base, 'v121': base}, broken)

    def test_historical_metric_missing_boolean_numeric_and_identity(self):
        score = dict(x=.25, missing=None, flag=False, id='A')
        saved = dict(x='.25', missing='', flag='False', id='A')
        metric_match(score, saved)
        for key, value in (('x', '.3'), ('missing', '0'), ('flag', 'True'), ('id', 'B')):
            with self.assertRaises(ValueError):
                metric_match(score, dict(saved, **{key: value}))
        with self.assertRaises(ValueError):
            metric_match(dict(score, x=np.nan), saved)


if __name__ == '__main__':
    unittest.main()
