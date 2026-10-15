"""Synthetic decision/support failures; never load recordings or fitted models."""
import unittest
import numpy as np
import frozen_validation_v123 as v


def rows():
    return [dict(id=str(i), participant=p, condition=c, scored_frames=100,
                 position_rmse_m=1., heading_rmse_deg=1., Position_P95_mm=1.,
                 Last_Supported_Endpoint_Error_mm=1.)
            for i, (p, c) in enumerate([('A','X'), ('A','Y'), ('B','X'), ('B','Y')])]


class ValidationContract(unittest.TestCase):
    def test_guarded_mean_improvement(self):
        base=rows(); candidate=[dict(r, position_rmse_m=.9) for r in base]
        self.assertTrue(v.decision(base,candidate)['eligible'])
        self.assertFalse(v.decision(base,base)['eligible'])

    def test_person_maneuver_and_tail_regressions(self):
        base=rows()
        for dimension in ('participant','condition'):
            candidate=[dict(r,position_rmse_m=1.06 if r[dimension]==base[0][dimension] else .5) for r in base]
            self.assertFalse(v.decision(base,candidate)['eligible'])
        for key in v.GUARD_KEYS:
            candidate=[dict(r,position_rmse_m=.9,**{key:1.06}) for r in base]
            self.assertFalse(v.decision(base,candidate)['eligible'])

    def test_zero_baseline_and_nonfinite(self):
        self.assertEqual(v.ratio(0.,0.),1.)
        self.assertIsNone(v.ratio(.001,0.))
        base=rows(); candidate=[dict(r,position_rmse_m=.9) for r in base]
        base[0]['heading_rmse_deg']=float('nan')
        with self.assertRaises(ValueError): v.decision(base,candidate)

    def test_missing_duplicate_relabeled_and_changed_counts(self):
        base=rows()
        for candidate in (base[:-1],base+[base[0]],
                          [dict(base[0],participant='C')]+base[1:],
                          [dict(base[0],scored_frames=99)]+base[1:]):
            with self.assertRaises(ValueError): v.decision(base,candidate)

    def test_equal_counts_do_not_excuse_different_masks(self):
        reference=np.ones(4,bool); xy=np.zeros((4,2)); h=np.zeros(4)
        base=xy.copy();base[1]=np.nan
        candidate=xy.copy();candidate[2]=np.nan
        with self.assertRaises(ValueError): v.check_support(reference,base,h,candidate,h,np.zeros((4,3)))

    def test_nonfinite_heading_or_motion_cannot_shrink_support(self):
        reference=np.ones(4,bool);xy=np.zeros((4,2));h=np.zeros(4);motion=np.zeros((4,3))
        v.check_support(reference,xy,h,xy,h,motion)
        bad=h.copy();bad[2]=np.nan
        with self.assertRaises(ValueError): v.check_support(reference,xy,h,xy,bad,motion)
        motion[2,0]=np.nan
        with self.assertRaises(ValueError): v.check_support(reference,xy,h,xy,h,motion)


if __name__=='__main__': unittest.main()
