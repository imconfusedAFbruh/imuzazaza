import numpy as np
from clock_consistency_v94 import pareto, passing_range


def test_tradeoff_and_missing_values():
    x = np.array([[.9,.7],[.8,.8],[.7,.9],[.6,.6],[np.nan,.99],[.9,.7]])
    assert pareto(x).tolist() == [True,True,True,False,False,True]
    assert passing_range(np.arange(6)/1000, np.array([0,1,1,0,1,0], bool)) == [
        {'lower_s':.001,'upper_s':.002,'grid_points':2},
        {'lower_s':.004,'upper_s':.004,'grid_points':1}]
    assert passing_range(np.arange(3)/1000, np.zeros(3,bool)) == []
    assert len(passing_range(np.array([0.,.001,.5,.501]),np.ones(4,bool))) == 2
