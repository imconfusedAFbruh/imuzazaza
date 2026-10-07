"""Small checks for offline context, assembly, and label masking."""
import numpy as np
import torch
from ronin_experiment import OfflineResNet, window_predictions, loss_for_core


def test_windows_and_model():
    class Echo(torch.nn.Module):
        def forward(self, x): return x[:, :2]
    x = np.random.default_rng(42).normal(size=(777, 20)).astype(np.float32)
    actual = window_predictions(Echo(), x, 'cpu', batch_size=2)
    assert actual.shape == (777, 2)
    np.testing.assert_array_equal(actual, x[:, :2])
    model = OfflineResNet().eval()
    assert model(torch.zeros(2, 20, 512)).shape == (2, 2, 512)
    np.testing.assert_array_equal(window_predictions(model, x, 'cpu'), np.zeros((777, 2)))
    model.train(); inputs = torch.randn(2, 20, 512)
    output = model(inputs)
    loss = loss_for_core(output, torch.ones_like(output), inputs,
                         torch.ones(2, 512, dtype=torch.bool), torch.ones(1, 2, 1))
    loss.backward()
    assert model.output.weight.grad.abs().sum() > 0
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)


def test_core_loss_ignores_context_labels():
    torch.manual_seed(42)
    pred = torch.randn(2, 2, 512, requires_grad=True); target = torch.zeros_like(pred)
    physical = torch.zeros(2, 20, 512); mask = torch.ones(2, 512, dtype=torch.bool)
    scale = torch.ones(1, 2, 1)
    loss = loss_for_core(pred, target, physical, mask, scale)
    changed = target.clone(); changed[:, :, :128] = 999; changed[:, :, 384:] = -999
    torch.testing.assert_close(loss, loss_for_core(pred, changed, physical, mask, scale))
    loss.backward(); assert torch.isfinite(pred.grad).all()
    assert not pred.grad[:, :, :128].any() and not pred.grad[:, :, 384:].any()


if __name__ == '__main__':
    test_windows_and_model(); test_core_loss_ignores_context_labels()
    print('2 RoNIN experiment checks passed')
