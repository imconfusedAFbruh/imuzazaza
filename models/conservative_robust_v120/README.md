# Conservative joint robust motion v120

Accepted TRAIN development model. Three participant-fold replicas preserve the
exact evaluated models. This bundle is not a full-data deployment refit or a
validated replacement for v34. See model_card.json for metrics and limitations.

From the research repository (local NumPy/SciPy and existing helpers required):

```python
from conservative_robust_inference_v120 import load_fold, predict_motion
model = load_fold("models/conservative_robust_v120", fold=0)
motion = predict_motion(sensor, setup, model)
```

sensor contains t (seconds), raw (N by18 IMU counts in the existing channel order)
and imu_valid (boolean). setup must match an available calibration key. Output
columns are forward m/s, zero lateral m/s, yaw rad/s. No optical values or
maneuver labels are read by motion inference. Trajectory integration separately
requires the same initial pose and inherited time/support conventions.

All207 held TRAIN motions reproduced the sealed evaluation within1e-12.
Do not average fold models or choose a fold from the true maneuver: neither
operation was evaluated. Use the recorded held_people mapping for reproduction.
