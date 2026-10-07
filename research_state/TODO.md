# Next priorities

1. Diagnose No.8 v43 guard failure by maneuver, velocity/yaw components and native support.
2. Separate No.8 clock change from refit using matched old-clock and same-clock fold controls.
3. Test conservative training-selected damping after arbitration; preserve frozen guard and exact fit IDs.
4. Build full participant-fold calibration, normalization and base-model refits across all dates.
5. Finish primary-source unit/firmware/receiver and device timebase/ODR audit; evidence still missing.
6. Validate optical marker geometry and physical-front convention without oracle flips.
7. Isolate No.18 PS2 braking travel deficit with counterfactual velocity/yaw integration and confidence.
8. Test uncertainty-aware wheelchair interval fusion / SE(2) smoothing, no C3D resets.
9. Independently review newest v42-v44 conclusions and PDF; retain all failed trials and route tails.
10. Define a new independently frozen acquisition with verified reference uncertainty and hardware synchronization.

Completed: affine/offset audit, multichannel clock arbitration, v42 refit, v43 folds, v44 loader, all71 route/image audit and83-page PDF.

## Superseding priorities after v53-v55 — 2026-10-05
1. **TRAIN-only No.18-type forward-travel model:** v55 proves No.18 PS2 is speed/travel dominated (~0.485m deficit; 405.191->60.344mm with GT speed; yaw-only unchanged). Test a continuous bounded braking/hysteresis or interval-speed residual, not the already-failed broad braking bridge.
2. **Uncertainty-aware interval fusion / SE(2):** include ~9.6ms ODR-vs-poll sensor-age uncertainty plus device/packet clock uncertainty; no C3D reset/alignment.
3. **Participant-fold robustness:** every new model selects on TRAIN folds only with worst-person ratio<=1.05. Validation may only evaluate frozen candidates; historical test remains closed/non-blind.
4. **Optical front/mounting geometry:** independently resolve No.5 AR2/AR3 physical-front convention and full sensor mounting/pitch; no oracle flips.
5. **New independent acquisition:** preserve exact firmware version, range/ODR register readback, raw journal START/STOP/SYNC, and hardware-shared IMU-MoCap timing event.

Completed now: primary-source firmware/receiver audit v53; accepted544 sequence audit; v50 completion check; v52 TRAIN projected-yaw result; v54 frozen validation; v55 PS counterfactual. Firmware audit is no longer a blocker.
