# Braking dynamics and temporal context, v17

## Hardware/timing evidence

No executed acquisition firmware or timestamp implementation exists among the supplied source files. CSVs include device microsecond timestamps and batched PC packet-arrival timestamps; the pipeline maps the last arrival sample of each packet to device time using a robust affine clock fit, then resamples100Hz. This removes dependence on packet arrival cadence for individual intersample spacing, but does not independently establish absolute cross-device timing accuracy or channel acquisition simultaneity.

The official [Seeed Arduino LSM6DS3 source](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/master/LSM6DS3.cpp) provides separate register reads for accelerometer and gyro axes, unit conversions, and timestamp/FIFO functions. The acquisition application chooses which calls/settings and timestamp assignment to use; the library alone cannot prove the CSV behavior. Its current public version may differ from the executed acquisition version. No timestamp/latency claim should be inferred from a nominal sensor/library name.

For21 accepted **training** PS recordings, median L/R/C device-to-packet-clock residuals are **4.815/3.684/3.120ms**; the largest absolute fitted clock-scale departure from1 is0.001816. That scale difference produces approximately1.8ms per second, which cannot by itself explain the roughly0.8second braking tail seen in the earlier inspected validation image. Residuals do not rule out a constant cross-device offset, batching convention, internal filtering latency or processing error. Saved training metadata: `outputs_braking_clock_diagnosis_v17/training_clock_diagnosis.json`. No validation lag is optimized.

## Empirical comparison

V17 directly regresses a **forward velocity residual** over the frozen ridge, retaining exactly its yaw/lateral channels. The raw center-sensor features use the v14 first-five-second IMU initialization audit, with declared date fallback. Three symmetric contexts are predeclared: ±0.25, ±0.5 and ±1seconds, each represented by five temporal samples. Penalties0.1/1/10 and gains0.25/0.5 plus the zero control are evaluated on the fixed training participant fold. Fits normalize/cap/weight using fit data only; selection requires no participant's path mean worsen by more than5%.

The selected context is **±0.5seconds, penalty0.1, gain0.5**. It improves inner-fold participant-mean path RMSE162.362→156.438mm, with all four fold participants improving. ±1second is close but did not win: best156.545mm, compared with156.438mm. This is evidence for temporal residual modeling, not a diagnosed hardware clock correction. Timestamps and optical poses never shift.

After all-training refit and a single final candidate evaluation:

| Model | Overall RMSE | PS RMSE | SL RMSE |
|---|---:|---:|---:|
| Paired CPU ridge | 116.899mm | 195.814mm | 145.487mm |
| Forward-only temporal residual | **111.077mm** | **184.298mm** | 145.464mm |

All four validation participant position averages improve: No10≈84.54mm, No14≈102.44mm, No18≈138.41mm, No5≈118.91mm. Heading outputs and metrics remain exactly the CPU ridge. Therefore this model does not repair the separately diagnosed long-turn heading drift. It also does not establish that all PS braking tails are fixed.

## Interpretation and artifacts

The direct velocity target is less vulnerable to differentiating optical position twice than the v11 acceleration target. Its temporal inputs can learn braking history without forcing an unknown raw specific-force vector to act as calibrated body-forward acceleration. The earlier v12 fold showed positive acceleration bias on braking frames even with center-only temporal inputs; its gravity/mount evidence remains unresolved. Together these measurements favor a supervised temporal residual before a stronger acceleration smoother or an invented lag correction.

Source: `braking_context_experiment_v17.py`; sealed outputs: `outputs_braking_context_v17/`. All473 training feature/motion caches are saved under `training_features/` with targets and observation labels explicitly named separately from input features. They are safe to reuse for conditional training-fold comparisons; they must not enter inference as label features. `braking_context_inference_v17.load_braking_context()` consumes IMU-only setup/t/raw/imu_valid and optional startup initialization. Missing startup history explicitly uses the training-date fallback. Supplied initialization must come from that recording's native initial IMU, never its optical reference.

No test recordings were opened. Selection is conditional because inherited calibration/base saw these training-fold people previously. Repeated validation is exploratory. A useful next comparator is a predeclared training-fold combination of this forward head with an independently conservative heading correction, reporting each channel's contribution and all participant regressions. Selecting a combination after inspecting validation scores would not supply independent evidence.

## Image read and subsequent fixed-fold blend

The reproduced No18 PS2 trajectory/timeline (`outputs_braking_context_diagnostic_plots_v17/`) still shows velocity dropping too soon through braking. RMSE447.955→418.768mm and endpoint544.460→517.608mm are modest improvements; the large braking deficit remains. All diagnostics reproduce sealed candidate scores within1e-8m. Heading is unchanged. The picture does not support claiming the braking mechanism has been corrected.

The follow-up `motion_blend_experiment_v20.py` independently refits v16 endpoint and v17 point heads **excluding the same four fold participants** before scoring24 unique global convex channel combinations. Forward weights are normalized to sum<=1, preventing doubled residual magnitude; yaw receives an independent0/0.5/1 weight, and lateral remains the ridge. Zero and unchanged v16 are included. The fold selects **unchanged v16**: forward16=1, yaw16=1, forward17=0. Thus v17 is not shown to add complementary value to v16. Full-training coefficients reproduce both parent fits (v16maximumweightdifference8.8e-17;v17zero), and final71-recording scores reproducev16 **104.452mm**. See `outputs_motion_blend_v20/report.md`; inference factory `motion_blend_inference_v20.load_motion_blend()`.
