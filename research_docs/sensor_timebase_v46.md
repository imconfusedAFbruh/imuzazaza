# Sensor conversion and timebase evidence v46

> **SUPERSEDED 2026-10-05:** primary-source acquisition firmware and receiver code were recovered and audited. Use `research_docs/firmware_receiver_audit_2026-10-05.md` for current range, conversion, BLE and timestamp conclusions. In particular, the older +/-2 g preservation below is no longer current: the raw Windows CSV path plus firmware defaults and ~8200-count gravity support +/-4 g / +/-2000 dps.

Reviewed 2026-10-04, Asia/Bangkok. Read-only evidence review: `imu_units_phase_audit_v42.py`, its existing training-only outputs, `pipeline.py`, `config/default.yaml` and prior acquisition notes. No acquisition data, time mappings, fitted models, evaluated predictions or prior artifacts were changed. No validation/test signals were accessed. Current upstream source is a reference, not proof of the firmware executed in September.

## Conclusions

1. Preserve the researcher's acquisition statement: **accelerometer ±2 g; gyro ±2000 degrees/s**. The older 16 g entry and current library defaults do not override it. Independently verifying the hardware registers and CSV transform still requires firmware/register evidence.
2. The stored device-time sequence is approximately **102.4 Hz**. It is not proof that the sensor itself was configured with a 102.4 Hz ODR; that setting is absent from the manufacturer's ODR table.
3. The gyro/phase audit is compatible with approximately 70 mdps per CSV unit. It does not certify raw-register encoding, clock units, all-axis conversion, acceleration encoding or actual sensor ODR.
4. Raw integer CSV fields, library floating readings, BLE packing and final CSV decoding are distinct stages. Their missing mapping prevents a verified SI conversion or acquisition-time uncertainty claim.

## Manufacturer and library facts

The LSM6DS3TR-C supports a nominal **104 Hz** ODR for accelerometer and gyro; adjacent settings are 52 and 208 Hz. ODR and range fields live in `CTRL1_XL` and `CTRL2_G`. Nominal sensitivity is **0.061 mg/LSB at ±2 g**, **0.122 mg/LSB at ±4 g**, and **70 mdps/LSB at ±2000 degrees/s**. Its internal timestamp is a 24-bit value with **25 microseconds or 6.4 ms** resolution selected by `TIMER_HR`. These specifications apply to configured register data. [ST datasheet, Table 3, Tables 52/55 and timestamp register descriptions](https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf).

The current Seeed library constructor sets accelerometer range **16 g**, gyro range **2000 degrees/s**, and both sample rates **416 Hz**. It disables timestamp collection by default. Settings can be changed before `.begin()`, which writes sensor configuration. An unsupported sample-rate argument follows the switch fallback to 104 Hz; this is distinct from the constructor's 416 Hz setting. `readRawAccel*`/`readRawGyro*` return `int16_t` register values; `readFloatAccel*`/`readFloatGyro*` apply configured-range conversion. [Seeed maintained source](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/master/LSM6DS3.cpp), [raw implementation](https://raw.githubusercontent.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/master/LSM6DS3.cpp).

The library's `calcAccel` formula is `raw * 0.061 * (accelRange >> 1) / 1000`, giving **g**. `calcGyro` is `raw * 4.375 * divisor / 1000`, where the 2000-range divisor is 16, giving **degrees/s**. At the researcher-stated ranges, genuine unscaled register counts would therefore convert as `a_g = raw * 0.000061` and `gyro_deg_s = raw * 0.070`; g to m/s² and degrees/s to rad/s are later conversions. These formulas do not determine which values the acquisition code serialized. Changing software settings after initialization can change float conversion without proving a hardware register change. [Seeed conversion code](https://raw.githubusercontent.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/master/LSM6DS3.cpp).

The XIAO nRF52840 **Sense** is documented with an LSM6DS3TR-C six-axis IMU. Naming the board does not establish that a particular firmware build, range or sampling path was used. [Seeed hardware documentation](https://wiki.seeedstudio.com/XIAO_BLE/).

## Stored timing evidence

The executed v42 audit covers **473 accepted training recordings × 3 sensors = 1,419 streams**. It computes timestamp deltas only where sequence numbers differ by exactly one; these are stored sequence-contiguous samples. The following values are arithmetic aggregations of existing `outputs_imu_units_v42/native_fields_timing.csv`, not a new experiment:

| Existing audit statistic | Value |
|---|---:|
| Weighted mean contiguous device delta | 9,765.624274 microseconds |
| Weighted fraction with 9,765 microseconds | 37.4374% |
| Weighted fraction with 9,766 microseconds | 62.3956% |
| Combined fraction of those two deltas | 99.8330% |
| Per-stream mean-delta range | 9,764.985602–9,765.847080 microseconds |
| Reciprocal rates from that range | 102.39767–102.40671 Hz |
| Nonpositive timestamp deltas | 0 |
| Streams with exclusively integer-valued six-channel CSV fields | All 1,419 |

For an exact interval of **9,765.625 microseconds**, `1,000,000 / interval = 102.4 Hz`. Quantizing an equally spaced sequence to integer microseconds produces 9,765/9,766 microsecond increments, with expected proportions 3/8 and 5/8. The observed weighted proportions are close. This establishes strong regularity of the **recorded time sequence**; it cannot tell whether timestamps were measured per acquisition, generated from sequence numbers, assigned before/after polling, or reconstructed in the receiver.

### Plausible MCU scheduler explanation, explicitly an inference

Nordic documents the nRF52840 RTC on a **32.768 kHz** low-frequency clock, with prescaling or compare events. A schedule spaced by **320 LFCLK ticks** has interval `320 / 32768 s = 9,765.625 microseconds`, exactly 102.4 Hz. Thus a firmware/RTOS scheduler using this tick count is a plausible explanation for the recorded cadence. It is not evidence that this firmware actually used RTC ticks, a particular prescaler, or an accurate oscillator. [Nordic nRF52840 RTC specification](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/rtc.html).

The near-exact MCU-compatible sequence and the sensor's different nominal ODR support distinguishing **logger cadence** from **hardware data generation**. Plausible paths include polling a faster sensor, reading the latest 104 Hz sample at about 102.4 Hz, FIFO draining/decimation, or synthetic per-sample timestamps. The current files cannot choose among them. A converted/interpolated sensor timestamp could also be present; the 9,765/9,766 pattern alone cannot identify direct use of the sensor's 25-microsecond/6.4-ms counter.

## What the gyro/phase and acceleration evidence means

`outputs_imu_units_v42/run.json` reports wheel phase-to-CSV-gyro scale magnitudes of **0.07025–0.07298 degrees/s per unit**, or **1.0036–1.0425 times** nominal 70 mdps/LSB. The phase fit itself uses no C3D target or wheel radius. However, selected axes and empirical acceleration normalization are inherited from optical-trained calibration, and phase extraction assumes a rotating gravity signal contaminated by translation, tilt, lever arms and filtering. Derivatives also depend on the inherited timebase. Agreement supports a candidate gyro conversion; it is not an independent firmware or timebase certificate.

The same audit's empirical gravity scales are **8,186.45–8,224.97 CSV units per g**. Conditional on genuinely unscaled ±2 g register storage, nominal 1 g would be approximately **16,393 counts**, which disagrees by about a factor of two. A ±4 g register interpretation predicts approximately 8,197 counts, but the user confirmed ±2 g: matching a number does not authorize changing their acquisition setting. Float-to-integer transforms, saved scale mismatches, offsets and receiver decoding can also produce such values. Acceleration and gyro may have different packing transforms.

Every native six-channel field is integer-valued. No field equals ±signed-16-bit endpoint values in the v42 audit. Neither fact establishes register encoding or excludes sensor clipping. Repeated identical gyro triples reach 11.42% in one stream, while complete six-vector repetition remains at most 0.147%; stationary/quantized signals can repeat naturally. These observations cannot prove hardware sample reuse, unique DRDY acquisitions or absence of aliasing.

## Existing reconstruction time mapping

`pipeline.py:imu_streams` takes device microseconds and PC monotonic nanoseconds, selects the last row of each group sharing PC arrival time, and fits a robust affine device-to-PC mapping separately for L/R/C. `sample_streams` then interpolates onto the configured 100 Hz modeling grid. The 100 Hz grid is a processing choice, distinct from both the recorded device cadence and sensor ODR.

Grouped PC times are consistent with batched packet reception, as documented in prior packet analysis. Packet arrivals contain BLE/receiver scheduling latency; their affine residuals describe agreement with arrivals, not independent acquisition-time accuracy. A fine lag-search grid similarly describes numerical resolution, not timing uncertainty. Shared motion peaks can support alignment, but do not identify firmware timestamp assignment, per-axis read delay or fixed packet latency.

Do not replace native timestamps by `sequence / 104`, nor by `sequence / 100`, on the basis of a nominal ODR or model grid. Doing so is an unverified change to elapsed time. At nominal rates, 104 vs 102.4 differs by 1.5625% in rate; if one were wrongly substituted for the other it would affect integration and derivative scales. That calculation does not establish a 1.5625% error in the current reconstruction.

## Still unknowable from these files

| Stage | Unresolved evidence |
|---|---|
| Executed device configuration | Exact firmware/library version; register readback; ODR, power mode, filters, FIFO/decimation, BDU and DRDY handling |
| Register-to-library conversion | Whether raw or float methods were used; software settings matching actual range registers; stale reads/read order |
| Packing and decoding | Integer multipliers/offsets, truncation/rounding, saturation/wrap, signedness, endianness, per-channel transforms and saved sensor scales |
| Timestamp semantics | Clock source, counter frequency, rollover extension, synthetic versus acquired times, before/after sensor read, individual versus FIFO/batch assignment |
| Sensor freshness and delay | Whether each row represents new hardware data; accel/gyro sample phase, filter latency, sequential-axis acquisition delay |
| Cross-system uncertainty | Packet latency distribution and device/PC/MoCap clock drift/offset independently verified through a shared timing event |

A fresh workspace search found no acquisition `.ino`, `.cpp`, `.c`, `.h`, `.uf2`, `.hex` or `.bin`, or matching firmware/receiver/logger implementation. This establishes that evidence is absent from this workspace, not that the original acquisition code never existed.

## Evidence that would settle the conversion and clock questions

Recover the original acquisition and receiver/packing sources and their versions. For an identical retained build, record simultaneous **raw register words → library floats → transmitted bytes → receiver-decoded values → final CSV fields**, plus sensor configuration-register readbacks at start/end. Record timer source, timestamp assignment line, DRDY/FIFO behavior and packet index semantics. A shared trigger/event observed by both IMU logging and optical recording is needed for an independent time-alignment measurement.

A current repeat can characterize the present chain, but connecting it to the September recordings requires matching firmware/build provenance. Until then, preserve researcher-stated ranges and explicitly empirical training-only conversion. This review supplies no new RMSE improvement and does not justify a factory-unit substitution or ODR-based time rescaling.
