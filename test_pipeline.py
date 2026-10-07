"""Small runnable checks for the numerical and leakage boundaries."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from pipeline import integrate, masked_interp, robust_line, synchronize, settings, inventory, digest, selected_artifacts, verify_selection, quiet_intervals, audit_recording_identity, fit_geometry_policy, reference, match_peaks, calibrate, velocities
from learning import ResidualTCN, features


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
            (out / 'geometry_policy.json').write_text('{}')
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

    def test_one_peak_cannot_support_two_matches(self):
        self.assertEqual(len(match_peaks(np.array([1.]), np.array([.9, 1.1]), .2)), 1)

    def test_training_geometry_recovers_wider_marker_setup(self):
        root = Path(__file__).parent
        with tempfile.TemporaryDirectory() as folder:
            rows = inventory(root, Path(folder))
            training = [r for r in rows if r['participant'] == 'No.20' and r['condition'] == 'AR']
            policy = fit_geometry_policy(training, root)
            poisoned = dict(training[0], partition='test', c3d='does-not-exist.c3d')
            self.assertEqual(policy, fit_geometry_policy(training + [poisoned], root))
            cfg = settings(root)
            cfg['reference_geometry'] = policy
            gt = reference(root / training[0]['c3d'], cfg, '2026-09-25')
            self.assertGreater(gt['raw_coverage'], .9)
            self.assertGreater(gt['diagnostics']['median_marker_separation_m'], .732)

    def test_physics_features_are_causal_and_reference_independent(self):
        raw = np.zeros((200, 18))
        raw[:, [2, 8, 14]] = 8192
        cal = dict(terms=[dict(column=j, scale=.001, intercept=0.) for j in (3, 9, 15)],
                   track_width_m=.52, wheel_radius_m=.3, accel_counts_per_g=[8192] * 3,
                   gyro_bias_counts=[[0, 0, 0]] * 3, center_gravity_direction=[0, 0, 1])
        d = dict(setup=np.array('setup'), raw=raw)
        base = np.zeros((200, 2))
        before = features(d, base, {'setup': cal})
        raw[100:] += 300
        d['gt_v'] = np.full(200, np.nan)
        after = features(d, base, {'setup': cal})
        self.assertEqual(before.shape, (200, 20))
        np.testing.assert_array_equal(before[:100], after[:100])

    def test_joint_speed_calibration_does_not_assume_actual_hub_width(self):
        rng = np.random.default_rng(23)
        v, yaw = rng.uniform(-1, 1, 5000), rng.uniform(-2, 2, 5000)
        raw = np.zeros((5000, 18))
        raw[:, [2, 8, 14]] = 8192
        raw[:, 5] = -(v - .615 * yaw / 2) / .001
        raw[:, 11] = (v + .615 * yaw / 2) / .001
        raw[:, 15] = yaw / .001
        d = dict(raw=raw, gt_v=v, gt_yaw=yaw, label_valid=np.ones(5000, bool))
        row = dict(setup='synthetic', id='training-only')
        c = calibrate([(row, d, {})], settings(Path(__file__).parent))['synthetic']
        reconstructed = velocities(d, c)
        np.testing.assert_allclose(reconstructed[:, 0], v, atol=1e-8)
        np.testing.assert_allclose(reconstructed[:, 1], yaw, atol=1e-8)


if __name__ == '__main__':
    unittest.main()
