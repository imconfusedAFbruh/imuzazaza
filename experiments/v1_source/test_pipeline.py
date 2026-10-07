"""Small runnable checks for the numerical and leakage boundaries."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from pipeline import integrate, masked_interp, robust_line, synchronize, settings, inventory, digest, selected_artifacts, verify_selection, quiet_intervals, audit_recording_identity
from learning import ResidualTCN


class PipelineChecks(unittest.TestCase):
    def test_planar_integration_and_gap(self):
        t = np.arange(0, 2.01, .01)
        motion = np.c_[np.ones(len(t)), np.ones(len(t))]
        xy, heading = integrate(t, motion, [0, 0], 0., np.ones(len(t), bool))
        np.testing.assert_allclose(xy[-1], [np.sin(2), 1 - np.cos(2)], atol=1e-4)
        self.assertAlmostEqual(heading[-1], 2.)
        valid = np.ones(len(t), bool)
        valid[50] = False
        xy, _ = integrate(t, motion, [0, 0], 0., valid)
        self.assertTrue(np.isfinite(xy[:50]).all())
        self.assertTrue(np.isnan(xy[50:]).all())

    def test_reference_gaps_are_not_interpolated(self):
        t = np.arange(6.)
        mask = np.array([True, True, False, False, True, True])
        values, valid = masked_interp(np.array([.5, 1.5, 3.5, 4.5]), t, t, mask)
        np.testing.assert_array_equal(valid, [True, False, False, True])
        self.assertTrue(np.isnan(values[1:3]).all())

    def test_empirical_fit(self):
        rng = np.random.default_rng(10)
        x = rng.normal(0, 1000, 2000)
        y = .0015 * x - .02
        y[::20] += 5
        fitted = robust_line(x, y)
        self.assertAlmostEqual(fitted['scale'], .0015, places=5)
        self.assertAlmostEqual(fitted['intercept'], -.02, places=2)

    def test_multi_peak_clock_offset(self):
        cfg = settings(Path(__file__).parent)
        t = np.arange(0, 25, .01)
        offset = .775
        def pulse(time):
            return sum(height * np.exp(-((time - peak) / .3) ** 2)
                       for peak, height in ((3, 1), (7, 2), (12, .8), (18, 1.5), (22, .9)))
        yaw = pulse(t)
        raw = np.zeros((len(t), 18))
        raw[:, 15] = 1000 * pulse(t - offset)
        gt = dict(t=t, yaw=yaw, speed=np.ones(len(t)), hz=100., derivative_valid=np.ones(len(t), bool))
        sync = synchronize(t, raw, np.ones(len(t), bool), gt, cfg)
        self.assertLess(abs(sync['offset_s'] - offset), .04)
        self.assertGreaterEqual(sync['matched_peaks'], 2)

    def test_tcn_cannot_see_future(self):
        torch.manual_seed(12)
        model = ResidualTCN(16).eval()
        # Nonzero output weights are needed to exercise the causal dependency.
        torch.nn.init.normal_(model.output.weight)
        x = torch.randn(1, 20, 300)
        changed = x.clone()
        changed[:, :, 200:] += 100
        with torch.no_grad():
            original, modified = model(x), model(changed)
        torch.testing.assert_close(original[:, :, :200], modified[:, :, :200])
        with torch.no_grad():
            chunk = model(x[:, :, 26:])[:, :, 124:]
        torch.testing.assert_close(original[:, :, 150:], chunk, atol=1e-4, rtol=1e-5)

    def test_stationarity_requires_both_wheels_to_stop(self):
        cfg = settings(Path(__file__).parent)
        raw = np.zeros((200, 18))
        raw[:, 14] = 8192
        d = dict(raw=raw, imu_valid=np.ones(200, bool))
        c = dict(terms=[dict(column=j, scale=1., intercept=0.) for j in (3, 9, 15)])
        self.assertTrue(quiet_intervals(d, c, cfg).all())
        raw[:, 3], raw[:, 9] = 1, -1
        self.assertFalse(quiet_intervals(d, c, cfg).any())

    def test_split_freezes_before_signal_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            rows = inventory(Path(__file__).parent, out)
            before = (out / 'split.json').read_bytes()
            inventory(Path(__file__).parent, out)
            self.assertEqual(before, (out / 'split.json').read_bytes())
            groups = {p: {r['participant'] for r in rows if r['partition'] == p and r['date'] in ('2026-09-24', '2026-09-25')}
                      for p in ('train', 'validation', 'test')}
            self.assertEqual([len(groups[p]) for p in groups], [12, 4, 4])
            self.assertTrue(groups['train'].isdisjoint(groups['validation'] | groups['test']))
            self.assertTrue(groups['validation'].isdisjoint(groups['test']))
            self.assertFalse((out / 'cache').exists())

    def test_artifact_tampering_is_rejected_before_test_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / 'calibration.json').write_text('{}')
            selection = dict(selected='baseline', calibration_sha256=digest(out / 'calibration.json'),
                             artifact_sha256=selected_artifacts(out, 'baseline'))
            verify_selection(out, selection)
            (out / 'calibration.json').write_text('{"changed":true}')
            with self.assertRaises(RuntimeError):
                verify_selection(out, selection)
            (out / 'a.csv').write_text('same capture')
            (out / 'a.c3d').write_text('same reference')
            rows = [dict(id='one', partition='train', imu='a.csv', c3d='a.c3d'),
                    dict(id='two', partition='test', imu='a.csv', c3d='a.c3d')]
            with self.assertRaises(RuntimeError):
                audit_recording_identity(rows, out, out)


if __name__ == '__main__':
    unittest.main()
