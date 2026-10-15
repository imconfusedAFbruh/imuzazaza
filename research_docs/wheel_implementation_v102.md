# Official Wheel-INS implementation audit, v102

9 October 2026. Read-only reviewer and coordinator independently inspect official
commit `1a3cc22f61b058612e8e69f6ecdcf5ec1dc95b5f`. The complete src/config tree is
downloaded under outputs_wheel_implementation_v102/source; every downloaded
src/config file is checked against its Git blob hash. A SHA256 manifest pins all
local evidence. No upstream code is modified, built or run on research data.

The executable creates one ImuFileLoader and one WheelINS filter, src/main.cpp:75
and77. README's Wheel-INS2 link establishes a related publication, not distributed
multi-IMU implementation. Label any future use single-wheel Wheel-INS; supplying
three streams would require an additional verified algorithm.

## Concrete portability findings

- src/main.cpp:35 declares Paras without explicit initial-state values.
  src/common/types.h:68 declares initstate; src/fileio/loadanddump.h loads only
  initstate_std, while src/wheel_ins/wheelins.cpp:40/47-53 consumes position,
  velocity, Euler angles and IMU errors. No explicit initial-state assignment is
  found in this executable path. Static source shows a reproducibility gap;
  actual runtime values and build-dependent Eigen behavior are not tested.
- src/common/types.h:10 fixes200Hz; wheel_ins/wheelins.h:86 fixes20samples.
  At local100Hz a full buffer spans approximately.20s instead of.10s. YAML
  imudatarate affects the loader's nominal interval, not the buffer size.
- wheel_ins/wheelins.cpp:211-219 derives velocity from negative averaged gyro x
  times wheel radius; its vehicle-heading conversion subtracts pi/2 from IMU yaw.
  Parsed mountAngle/ifCompensateVelocity are not used by the inspected filter.
  Lever arm is used. A selected scalar gyro axis alone is not a complete 3D
  mounting transform; local physical radius/lever arm remain conditional.
- fileio/imufileloader.h:24-25 copies rates/acceleration from binary double
  columns1-6 after time. It replaces timestamp intervals>=.1s with nominal dt
  and has no validity/run-boundary interface. This cannot silently inherit local
  gap-preserving evaluation. insmech.cpp multiplies rates by dt, consistent with
  rad/s and m/s2, not raw counts or preintegrated increments.
- GPLv3 license is pinned; retain notices and applicable source/license terms
  for any later distributed modifications. No code is imported into our predictor.

## Same-data decision

Do not run this as a ready-made Wheel-INS2 competitor. A defensible single-wheel
comparator requires explicit initial state from permitted setup/initial pose,
documented units, complete mounting, rate and gap behavior, training-only noise
calibration and preserved support. Fixes would be identified as a modified
implementation rather than quietly credited to upstream. All207clock gate still
fails at199/207, so no trajectory comparison is authorized yet.

Primary sources are pinned [executable](https://github.com/i2Nav-WHU/Wheel-INS/blob/1a3cc22f61b058612e8e69f6ecdcf5ec1dc95b5f/src/main.cpp),
[configuration loader](https://github.com/i2Nav-WHU/Wheel-INS/blob/1a3cc22f61b058612e8e69f6ecdcf5ec1dc95b5f/src/fileio/loadanddump.h),
[filter](https://github.com/i2Nav-WHU/Wheel-INS/blob/1a3cc22f61b058612e8e69f6ecdcf5ec1dc95b5f/src/wheel_ins/wheelins.cpp),
[types](https://github.com/i2Nav-WHU/Wheel-INS/blob/1a3cc22f61b058612e8e69f6ecdcf5ec1dc95b5f/src/common/types.h),
and [license](https://github.com/i2Nav-WHU/Wheel-INS/blob/1a3cc22f61b058612e8e69f6ecdcf5ec1dc95b5f/LICENSE).
No competitor reproduction, new accuracy result or promotion is established.
