import numpy as np


def test_counterfactual_motions_swap_only_requested_channel():
    from braking_counterfactual_v55 import counterfactual_motions

    predicted = np.array([[1.0, 0.0, 0.1], [2.0, 0.0, 0.2]])
    gt_v = np.array([1.5, 2.5])
    gt_yaw = np.array([0.3, 0.4])

    got = counterfactual_motions(predicted, gt_v, gt_yaw)

    assert np.allclose(got["predicted"], predicted)
    assert np.allclose(got["gt_speed"], [[1.5, 0.0, 0.1], [2.5, 0.0, 0.2]])
    assert np.allclose(got["gt_yaw"], [[1.0, 0.0, 0.3], [2.0, 0.0, 0.4]])
    assert np.allclose(got["gt_speed_yaw"], [[1.5, 0.0, 0.3], [2.5, 0.0, 0.4]])
