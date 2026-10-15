# Trial-RMSE reservoir v124

Full-TRAIN fit at the penalty selected on three inherited participant folds.
See research_docs/trial_rmse_results_v124.md for matched held-TRAIN evidence.
No v124 validation/test result is established.

```python
from reservoir_inference_v121 import load_reservoir_model
predict = load_reservoir_model('models/trial_rmse_v124')
motion = predict(sensor)
```

The existing loader accepts this bundle directly. Before importing torch use
CUDA_VISIBLE_DEVICES=-1; exact CPU reproduction uses torch.set_num_threads(4).
sensor contains setup, t, raw(Nx18), imu_valid and IMU-only initialization or
original startup_imu history. Motion columns are forward m/s, lateral m/s,
yaw rad/s. Supply initial pose separately to integrate_motion from
dynamic_blend_inference_v34. No optical or identity inputs enter prediction.

Existing offline filters, original crops/clocks, inherited calibration and
parent dependence on additional training records remain. Local sealed parent
artifacts are required. This is a research candidate without deployment approval.
