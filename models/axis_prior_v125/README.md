# Axis-prior reservoir v125

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
