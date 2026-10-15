"""Freeze the selected axis-prior fit and verify the existing public loader."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OPENBLAS_NUM_THREADS'] = '4'
import json
import time
import numpy as np
import torch
import pipeline as p
import trial_rmse_v124 as previous
from axis_prior_v125 import OUT as SCREEN, CONFIGS, fit
from reservoir_path_v121 import prediction
from reservoir_inference_v121 import load_reservoir_model

OUT = p.ROOT/'models/axis_prior_v125'


def main():
    started = time.perf_counter()
    torch.set_num_threads(4)
    previous.check_stop()
    inputs = {}
    run = previous.sealed(SCREEN, 'run.json', inputs)
    protocol = previous.sealed(SCREEN, 'protocol.json', inputs)
    expected_sources = dict(protocol['sources'])
    expected_sources['package_axis_prior_v125.py'] = p.digest(p.ROOT/'package_axis_prior_v125.py')
    assert all(p.digest(p.ROOT/name) == sha for name, sha in expected_sources.items())
    inputs.update(expected_sources)
    selected = run['selected']
    if selected['candidate'] == 'v124':
        print('No eligible v125 winner: retain the frozen v124 bundle', flush=True)
        return
    assert selected['eligible'] and selected['candidate'] in CONFIGS
    penalties = CONFIGS[selected['candidate']]
    assert list(penalties) == protocol['configs'][selected['candidate']]
    prior_folder = p.ROOT/'models/reservoir_path_v121_completed'
    prior = previous.sealed(prior_folder, 'model.json', inputs)
    load_reservoir_model()
    entries, _ = previous.load_train(inputs)
    assert [e['row']['id'] for e in entries] == protocol['training_ids'] == prior['training_ids']
    original = previous.sealed(p.ROOT/'outputs_nonlinear_endpoint_v21', 'model.json', inputs)
    tilt = previous.sealed(p.ROOT/'outputs_dynamic_tilt_v33', 'tilt_0.3_model.json', inputs)
    es = previous.prepare(entries, original, tilt, prior['normalization'])
    OUT.mkdir(parents=True, exist_ok=False)
    fits = {}
    for setup in prior['fits']:
        previous.check_stop()
        fits[setup] = fit([e for e in es if e['setup'] == setup], penalties,
                          np.array(prior['fits'][setup]['weights']))
        p.save_json(OUT/'fit_checkpoint.json', dict(fits=fits, status='fitting'))
        print('Full TRAIN fit completed setup', setup, flush=True)
    dependencies = dict(prior['dependencies'])
    for name in ('axis_prior_v125.py', 'package_axis_prior_v125.py',
                 'test_axis_prior_v125.py', 'trial_rmse_v124.py',
                 'research_docs/axis_prior_v125.md',
                 'models/reservoir_path_v121_completed/model.json',
                 'models/reservoir_path_v121_completed/artifact_manifest.json',
                 'outputs_axis_prior_v125/artifact_manifest.json'):
        dependencies[name] = p.digest(p.ROOT/name)
    dependencies.update(expected_sources)
    p.save_json(OUT/'model.json', dict(penalties=penalties, fits=fits,
                normalization=prior['normalization'], training_ids=protocol['training_ids'],
                baseline='frozen full-TRAIN v34 .75; v121 selected weights are fitting prior',
                selected_fold_result=selected, dependencies=dependencies,
                validation_evaluated=False, test_evaluated=False))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={'model.json': p.digest(OUT/'model.json')}))
    predict = load_reservoir_model('models/axis_prior_v125')
    checks = []
    for e in es:
        sensor = {k: e['data'][k] for k in ('t', 'raw', 'imu_valid')}
        sensor.update(setup=e['setup'], initialization=e['initialization'])
        expected = prediction(e, np.array(fits[e['setup']]['weights']))[0]
        actual = predict(sensor)
        error = float(np.max(np.abs(actual-expected)))
        assert error < 1e-7
        poisoned = dict(sensor, gt_xy=np.full((len(actual), 2), 1e9),
                        gt_heading=np.full(len(actual), -1e9), condition='poison',
                        participant='poison', id='poison')
        assert np.array_equal(predict(poisoned), actual)
        checks.append(dict(id=e['row']['id'], maximum_motion_difference=error,
                           optical_identity_poisoning_invariant=True))
        if len(checks) % 20 == 0:
            previous.check_stop()
            p.save_json(OUT/'trial_verification.json', checks)
            print('Verified public inference', len(checks), '/207', flush=True)
    assert len(checks) == 207
    for expected in (inputs, dependencies):
        assert all(p.digest(p.ROOT/name) == sha for name, sha in expected.items())
    p.save_json(OUT/'trial_verification.json', checks)
    p.save_json(OUT/'inputs.json', inputs)
    p.save_json(OUT/'verification.json', dict(recordings=207, full_train_fit=True,
                maximum_motion_difference=max(r['maximum_motion_difference'] for r in checks),
                all_optical_identity_poisoning_checks_passed=True,
                validation_accessed=False, test_accessed=False,
                note='Full TRAIN inference reproduction; not held-out accuracy',
                runtime_s=time.perf_counter()-started))
    (OUT/'README.md').write_text('''# Axis-prior reservoir v125

Selected speed/yaw prior strengths fitted once on all207 TRAIN records.
See research_docs/axis_prior_results_v125.md for participant-fold evidence.

```python
from reservoir_inference_v121 import load_reservoir_model
predict = load_reservoir_model('models/axis_prior_v125')
motion = predict(sensor)
```

Before importing torch set CUDA_VISIBLE_DEVICES=-1; exact CPU reproduction
uses torch.set_num_threads(4). Sensor inputs: setup, t, raw(Nx18), imu_valid,
and original IMU-only initialization or startup_imu history. Motion columns:
forward m/s, lateral m/s, yaw rad/s. Initial pose is separate for integration.
Local sealed parent artifacts are required. Offline filtering, original crops/
clocks/calibration and266 additional parent training records remain inherited.
Validation/test generalization and deployment approval are not established.
''', encoding='utf-8')
    p.save_json(OUT/'fit_checkpoint.json', dict(completed_setups=sorted(fits), status='complete'))
    p.save_json(OUT/'artifact_manifest.json', dict(sha256={str(f.relative_to(OUT)): p.digest(f)
                for f in OUT.rglob('*') if f.is_file() and f.name != 'artifact_manifest.json'}))
    print(json.dumps(dict(model_sha256=p.digest(OUT/'model.json'), verified_recordings=207)), flush=True)


if __name__ == '__main__':
    main()
