"""Runnable causality and uncertainty-filter checks: python test_alternatives.py."""
import numpy as np
import torch
import tempfile
from pathlib import Path
from unittest.mock import patch
from alternatives import ResidualGRU, rate_filter, gru_predictor

torch.set_num_threads(4)
torch.manual_seed(12)
model = ResidualGRU().eval()
torch.nn.init.normal_(model.output.weight)
x = torch.randn(1, 20, 300)
changed = x.clone(); changed[:, :, 200:] += 100
with torch.no_grad():
    a, b = model(x), model(changed)
torch.testing.assert_close(a[:, :, :200], b[:, :, :200])
with tempfile.TemporaryDirectory() as folder:
    out = Path(folder)
    torch.save(dict(state=model.state_dict(), gain=1.), out / 'gru32.pt')
    sample = torch.randn(1, 20, 777)
    norm = dict(mean=[0.] * 20, std=[1.] * 20, target_scale=[1.] * 2, residual_cap=[1e6] * 2)
    with torch.no_grad():
        expected = []
        for start in range(0, 777, 256):
            left = max(0, start - 256)
            expected.append(model(sample[:, :, left:start + 256])[0, :, start - left:].T.numpy())
    with patch('alternatives.features', return_value=sample[0].T.numpy()):
        actual = gru_predictor(out, {}, norm)({}, np.zeros((777, 2)))
    np.testing.assert_allclose(actual, np.concatenate(expected), atol=1e-5, rtol=1e-5)
motion = np.zeros((300, 2)); motion[100] = 10
variance = np.ones_like(motion); variance[100] = 1e6
filtered = rate_filter(motion, variance, [.01, .01])
assert abs(filtered[100]).max() < .001, 'High-uncertainty spike must be discounted'
future = motion.copy(); future[200:] = 5
np.testing.assert_array_equal(filtered[:200], rate_filter(future, variance, [.01, .01])[:200])
np.testing.assert_allclose(rate_filter(np.ones_like(motion), variance, [.01, .01]), 1)
try:
    rate_filter(motion, np.zeros_like(motion), [.01, .01])
except ValueError:
    pass
else:
    raise AssertionError('Nonpositive measurement variance must be rejected')
print('GRU causality and batched equivalence; filter causality, constant motion, uncertainty weighting and guards pass')
