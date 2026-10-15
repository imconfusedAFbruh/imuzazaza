# Reservoir path v121

Callable full-TRAIN candidate, frozen after selection on three participant folds.
Held-fold ATE129.739811mm versus matched retainedv34 132.240200mm; all original
guards pass. No validation/test result or universal superiority claim.

```python
from reservoir_inference_v121 import load_reservoir_model
predict = load_reservoir_model()
motion = predict(sensor)
```

Run CPU with CUDA_VISIBLE_DEVICES=-1 before importing torch. sensor contains
setup,t,raw(Nx18),imu_valid and initialization or original startup_imu history.
Motion columns: forwardm/s,lateralm/s,yawrad/s. No optical or maneuver inputs.
Use the existing dynamic_blend_inference_v34.integrate_motion with a separately
supplied initial pose. Original clocks/crop/support assumptions still apply.
Inherited base models and their local sealed artifacts are required. Model is
offline (base uses future context), and inherited calibration includes legacy data.
New residual fits use only207 identified TRAIN recordings. No deployment promotion.
