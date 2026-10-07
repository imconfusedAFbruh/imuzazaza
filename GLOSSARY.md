# Wheelchair trajectory reconstruction

This project reconstructs wheelchair motion from three IMU recordings and evaluates it against Qualisys motion capture.

## Language

**Offline reconstruction**:
Estimation of a wheelchair trajectory from recordings after a capture trial has finished.
_Avoid_: Live tracking, real-time estimation

**Reconstructed trajectory**:
The estimated path of the wheelchair through time, derived from its IMU recordings.
_Avoid_: Ground truth

**Hub midpoint**:
The point halfway between the left and right wheel hubs. Its 2D path is the trajectory reference for this project.
_Avoid_: Marker midpoint, sensor position

**Held-out recording**:
A capture trial reserved for evaluation whose samples are excluded from fitting the estimator and its calibration parameters.
_Avoid_: Training trial

**Participant partition**:
A training, validation, or test assignment that includes every recording of the same person across capture dates.
_Avoid_: Random window split, date split

**Qualisys reference trajectory**:
The hub-midpoint path derived from optical motion-capture markers, with unavailable or unreliable reference frames marked invalid.
_Avoid_: Reconstructed trajectory, complete ground truth

**Empirical sensor calibration**:
A conversion from recorded sensor values to physical motion quantities estimated from training recordings. It is distinct from a conversion verified against the acquisition firmware.
_Avoid_: Factory calibration
