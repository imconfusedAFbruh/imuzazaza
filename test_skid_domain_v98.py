import numpy as np
from skid_domain_v98 import literal_weights


def test_literal_weights_and_source_singularities():
    # Equal wheels/deceleration gives .5; asymmetric same-sign case gives .75.
    result=literal_weights(np.array([2.,3.,2.,1.,1.]),np.array([2.,1.,2.,-1.,1.]),
                           np.array([-1.,-1.,0.,1.,1.]),np.array([-1.,-1.,0.,1.,-1.]))
    assert np.allclose(result['weight'][:2],[.5,.75])
    assert result['finite'].tolist()==[True,True,False,False,False]
    assert result['speed_zero'].tolist()==[False,False,False,True,False]
    assert result['acceleration_zero'].tolist()==[False,False,True,False,True]
    assert np.isnan(result['weight'][2:]).all()


def test_mixed_accelerations_can_make_nonconvex_weight():
    result=literal_weights(np.array([2.]),np.array([1.]),np.array([2.]),np.array([-1.]))
    assert result['third_near'][0] and not result['safe'][0] # cancellation may leave floating roundoff
    result=literal_weights(np.array([3.]),np.array([1.]),np.array([1.]),np.array([-1.]))
    assert not result['finite'][0] # acceleration sum cancels
    result=literal_weights(np.array([3.]),np.array([1.]),np.array([2.]),np.array([-1.]))
    assert abs(result['weight'][0]-3)<1e-12 and result['outside'][0]
