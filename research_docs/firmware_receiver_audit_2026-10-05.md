# Mandatory firmware + receiver audit — redo in kight_recover

Date: 2026-10-05  
Workspace: `C:\Users\poon1\Desktop\kight_recover`

2026-10-08 verification: see `firmware_primary_audit_2026-10-08.md` for
correct peeled release-tag identities and requirement-level evidence. The
commits below include intermediate release preparations, not always the tagged
release commit. Exact flashed binary/runtime range provenance remains unresolved;
the source/data audit does not prove that provenance.

This report supersedes the unresolved acquisition-source conclusions in
`research_docs/sensor_timebase_v46.md`. The earlier v46 document correctly
separated recorded cadence from sensor ODR, but it did not have the actual
acquisition firmware/receiver implementation and therefore preserved an
incorrect +/-2 g assumption. The primary-source code is now available from the
WheelAthelse repository and changes that conclusion.

## Frozen research rules preserved

- Retained conditional development reference remains v34 at 100.702119 mm.
- v42 at 94.834759 mm own-clock / 94.661740 mm common-native remains
  **not promoted** because No.8 ratio 1.058004869 exceeds the frozen 1.05 guard.
- No historical test data was accessed during this redo.
- No clock or threshold was selected from validation position RMSE.
- Old sealed result folders were not overwritten.

## Primary-source repository and version provenance

Primary repository:
`https://github.com/NnopponS/WheelAthelse`

Relevant release commits:
- v1.8.1: `30e99d83ae9d0da072721306f65501a35024813a`, 2026-09-08.
- v1.8.2: `667a7e09ba75526a901e8648281b69539ada139a`, 2026-09-10.
- v1.8.3: `795e146613cf4f2d32f59f087082812921d3d2b6`, 2026-09-17.
- v1.8.4 release preparation: `eab67ca23edfa078cd866008e2e1f1c81648b08c`, 2026-09-24.
- v1.8.4 candidate: `245f616c9b04e562824ddedd6643359a9de968cc`, 2026-09-25.

The acquisition core files `imu_reader.cpp`, `imu_reader.h` and
`imu_types.h` have identical Git blob SHAs across the inspected v1.8.1,
v1.8.2, v1.8.3 and v1.8.4-era commits. Therefore the range defaults, sensor
ODR mapping, raw packet contents and polling/timestamp implementation described
below are stable across the September 9/11/19/24/25 acquisition dates.

The exact binary flashed on each physical board is still not cryptographically
recoverable from the exported CSV alone because the CSV does not contain the
Info characteristic firmware version. The date-compatible release attribution
is strong, but an original .waj journal/session metadata file, serial log, or
firmware artifact is required to prove the exact flashed patch version.

## Actual accelerometer / gyroscope range

The XIAO firmware calls:

`imu().begin(configStore().rateHz())`

without explicit range arguments. `ImuReader::begin` defaults to:
- `AccelRange::G4`
- `GyroRange::DPS2000`

The Windows acquisition GUI also defaults its range selectors to:
- accel index 1 = **+/-4 g**
- gyro index 3 = **+/-2000 dps**

`ConfigStore` persists board name, wheel and sample rate, but **does not
persist the accel/gyro range**. A live `SET_RANGE` command could change them,
so the CSV alone does not contain an explicit range code.

However the recorded data independently supports the firmware defaults:
- across every September acquisition date, median raw acceleration norm is
  about 8.16k–8.25k counts;
- the ST sensitivity at +/-4 g is 0.122 mg/LSB, predicting about 8197 counts/g;
- +/-2 g would predict about 16393 counts/g and is incompatible with the raw
  register values now that the receiver path is proven to preserve raw int16
  counts;
- the existing TRAIN-only phase audit estimates approximately
  0.07025–0.07298 dps per gyro CSV count, strongly supporting the +/-2000 dps
  70 mdps/LSB interpretation.

**Audit conclusion:** the September dataset is supported as raw LSM6DS3 register
counts acquired at approximately **+/-4 g and +/-2000 dps**. The older
`config/default.yaml` / `pipeline.settings()` +/-2 g text is stale metadata,
not a numerical conversion used by the trajectory estimator.

## Raw -> physical conversion and the firmware scale-table bug

ST LSM6DS3TR-C datasheet sensitivities:
- +/-2 g: 0.061 mg/LSB
- +/-4 g: 0.122 mg/LSB
- +/-8 g: 0.244 mg/LSB
- +/-16 g: 0.488 mg/LSB
- +/-250 dps: 8.75 mdps/LSB
- +/-500 dps: 17.5 mdps/LSB
- +/-1000 dps: 35 mdps/LSB
- +/-2000 dps: **70 mdps/LSB**

The Seeed LSM6DS3 library implements those datasheet sensitivities.

The historical WheelAthelse firmware Info table instead used:
- accel: full_scale / 32768
- gyro: full_scale / 32768

For +/-2000 dps this reports:
`2000 / 32768 = 0.06103515625 dps/LSB`

instead of the correct:
`0.070 dps/LSB`

Thus firmware Info metadata under-reports +/-2000 dps gyro values by about
12.81% relative to the correct value; values converted with the old scale
require a factor of about **1.14688** to recover the datasheet sensitivity.

At +/-4 g, `4/32768 = 0.0001220703125 g/LSB` is only about 0.058% above the
datasheet nominal 0.000122 g/LSB, so the important scale-table error is gyro.

### Does this invalidate the September research CSVs?

No. The research CSVs have the exact Windows `JournalReader.export_csv` raw
schema:

`session_id,wheel,seq,timestamp_device_us,timestamp_pc_monotonic_ns,ax_raw,ay_raw,az_raw,gx_raw,gy_raw,gz_raw,packet_id,sequence_class,missing_before`

The Windows BLE parser decodes `<IIhhhhhh` and the journal exporter writes
those raw integers unchanged. The firmware Info scales are not applied to these
CSV fields.

The mobile app is different: it parses the same raw packet, then
`ImuSample.toReading` multiplies raw axes by the device Info
`accelScale/gyroScale`, and its physical-units CSV schema is different.
Therefore a mobile physical-units export created with the historical firmware
Info scale could contain the gyro-scale error, but the kight_recover research
CSVs are **not** that format.

## Sensor ODR, polling and effective sample rate

Firmware maps requested rates to LSM6DS3 ODR:
- requested 50 -> sensor 52 Hz
- requested 100 -> sensor **104 Hz**
- requested 200 -> sensor 208 Hz

The IMU task is a polling loop with period:

`pdMS_TO_TICKS(1000 / rate_hz_)`

For the Adafruit nRF52 FreeRTOS core used by this platform,
`configTICK_RATE_HZ = 1024`. A requested 100 Hz therefore becomes a
10-tick polling period:

`10 / 1024 s = 9.765625 ms = 102.4 Hz`

The raw data independently matches this:
- dominant `t_device_us` increments are 9765/9766 us;
- median increment is 9766 us;
- reciprocal median rate is **102.3961 Hz** on L/R/C and on all five inspected
  acquisition dates.

So there are three distinct rates:
1. configured application request: 100 Hz,
2. sensor output-data rate: 104 Hz,
3. firmware polling / recorded sample cadence: approximately 102.4 Hz.

The firmware does not use FIFO or DRDY for this acquisition path. It reads one
current 12-byte accel+gyro output block per poll. Therefore sensor updates can
occur between polls without generating an IMU sequence gap. At the nominal
rates, 104 - 102.4 = 1.6 sensor updates/s are not individually observed. The
relative sensor-update age can sweep over approximately one 104-Hz period
(~9.6 ms). This is a real acquisition-time uncertainty term and should be
carried into future uncertainty-aware fusion; it is not BLE packet loss.

## Device timestamp behavior

For each poll, firmware:
1. records `read_started_us = micros()`;
2. performs the contiguous 12-byte register burst;
3. records `read_finished_us = micros()`;
4. stores the midpoint as per-sample `t_device_us`.

The sample contains:
- uint32 `seq`
- uint32 `t_device_us`
- six raw int16 axes

Total wire sample size is 20 bytes. `micros()` is uint32 and wraps, but the
accepted recordings are far shorter than its ~71.6-minute wrap period and the
accepted audit found no non-monotonic device-time records.

Sequence is reset at START. It identifies samples produced by the firmware
polling task; it cannot detect sensor ODR frames overwritten before a poll.

## BLE batching and receiver timestamp semantics

At a requested 100 Hz, firmware targets about 10 notifications/s and normally
packs 10 samples into a BLE notification.

Observed raw data:
- modal packet size = 10 across all dates;
- about 90% of adjacent CSV rows share the same PC arrival timestamp;
- all samples in one notification receive the **same**
  `time.perf_counter_ns()` callback timestamp on Windows. This is a monotonic
  performance-clock reading; the CSV column is named `timestamp_pc_monotonic_ns`.

Thus `timestamp_pc_monotonic_ns` is a packet-arrival timestamp, not an
independent physical sample time for every row.

The kight_recover `pipeline.py:imu_streams` already handles this sensibly:
- it retains `timestamp_device_us` as the high-resolution within-device time;
- it chooses the last row of each repeated PC timestamp group as the
  packet-level anchor for device->PC affine fitting;
- it reconstructs full sample times from device timestamps;
- it later resamples to a 100 Hz **model grid**.

Therefore the model's 100 Hz grid must not be confused with acquisition
cadence. Replacing recorded device time by row/100 would be wrong. On just
Sep 9/11, that mistake would lengthen a median stream by about 0.400 s and
1.919 s respectively (median duration ratio 1.024).

## Sequence gaps / dropped samples

A scan of **all raw recordings** found substantial gap records among some
Sep-24 files:
- L: missing_before sum 13160; direct sequence missing 18544
- R: 13340; direct missing 18653
- C: 13320; direct missing 18463

Those files include rejected/unselected recordings.

A second audit restricted to the exact 544 v42 accepted recordings
(473 train + 71 validation) found:
- **0 affected accepted trials**
- missing_before sum = 0 for every date/role
- direct sequence-gap missing samples = 0
- duplicates = 0
- out-of-order = 0

This reconciles the apparently conflicting raw-folder and accepted-dataset
observations: packet/sample loss existed in the broader Sep-24 acquisition
folder, but the frozen accepted research set excludes those recordings.

## START / STOP / SYNC event handling

Firmware START:
- clears replay/pending transport state;
- resets queue and sequence;
- starts immediately or waits for a scheduled device-time target;
- sends START_FIRED with device micros and optional UTC information.

Firmware STOP:
- stops the IMU polling task;
- records stop device micros;
- drains queued/pending BLE samples;
- waits for a short drained/quiet condition;
- sends health and STOP_FIRED.

SYNC_PING:
- captures current device `micros()`;
- returns device time with the app ping token/counter.

Windows recording:
- performs multiple pre-start clock sync observations;
- stores the fitted clock model in the .waj journal;
- resets sequence epoch before scheduled START;
- records START event metadata;
- waits for STOP acknowledgements and queue drain;
- performs optional post-stop clock refinement;
- stores health/QC and STOP events;
- exports raw samples to CSV.

The exported CSV does **not** contain the journal's START/STOP/SYNC event
records or firmware-version Info snapshot. That provenance was discarded when
only the CSV export was preserved.

## Impact on existing v34-v52 results

The important distinction is **raw model features vs physical-unit metadata**.

The trajectory pipeline uses raw integer axes plus empirically fitted
calibration. It does not multiply the September raw CSV gyro fields by the
incorrect firmware `GYRO_SCALE_TABLE`. The current pipeline timebase also
uses recorded device timestamps, not row number / 100 Hz.

Consequently:
- do **not** multiply existing v34/v42/v49/v50/v52 inputs by 1.14688;
- do **not** replace their timestamps with sequence/104 or sequence/100;
- the firmware Info gyro bug does **not** by itself invalidate the retained
  v34 score or v42 conditional score;
- a wholesale ML rerun for a scale conversion error is **not justified**.

The stale +/-2 g text formerly in `config/default.yaml`, `pipeline.settings()` and the
older v46 report is documentation/provenance debt. It is not the numerical
conversion used by these models. Historical sealed source/artifacts are left
unchanged so their hashes and reproducibility remain intact. New work should
reference this audit rather than the stale range metadata. Current config and
pipeline metadata were corrected on 2026-10-08; sealed copies remain unchanged.

## Continued research after the audit

The state files were stale: v50 had already completed, and a later TRAIN-only
v52 experiment also exists.

v50:
- simple point/endpoint alternatives did not pass the intended robustness
  objective; the physics baseline remained selected.

v52:
- dynamic gravity-projected center yaw was selected on held-participant TRAIN
  folds at weight 1.0;
- TRAIN fold physics: 219.002 mm;
- TRAIN fold projected yaw: 147.747 mm;
- worst participant ratio: 0.961159, within the frozen 1.05 guard;
- validation/test were not used for selection.

A fixed, no-retuning validation run was added as
`outputs_projected_yaw_validation_v54`:
- 71 validation trials / 4 participants;
- refit-physics: **229.801 mm**, heading 5.4068 deg;
- projected yaw: **153.607 mm**, heading 2.0493 deg;
- worst validation participant ratio vs the same refit-physics baseline:
  **0.843576**;
- validation retuning: false;
- test accessed: false.

This strongly supports the physical usefulness of gravity-projected center yaw
for the simple fold-refitted physics estimator, but **does not beat retained
v34 (100.702 mm)** and is not a new best candidate. Also, v33/v34 already use
related projected-gravity features, so simply adding the same feature again
would repeat an existing idea.

## Updated next research direction

The firmware audit removes sensor conversion as the main explanation for the
remaining trajectory error. The highest-value unresolved mechanisms remain:

1. No.18 PS2 braking/travel deficit: timing alone cannot explain the roughly
   half-meter longitudinal deficit.
2. Full mounting / pitch observability: two optical axle markers do not supply
   full 3D body attitude; low-pass acceleration is only a gravity proxy.
3. No.5 AR2/AR3 physical-front ambiguity: must be resolved by independent
   geometry evidence, never by oracle flipping.
4. ODR-vs-poll sample-age uncertainty: include approximately one sensor-period
   timing uncertainty in interval fusion instead of pretending timestamps are
   exact sensor-update times.
5. Uncertainty-aware wheel/body SE(2) fusion using train-only selection and the
   frozen 1.05 participant guard.

## Evidence files produced by this redo

- `outputs_firmware_audit_v53/dataset_timing_audit.json`
- `outputs_firmware_audit_v53/all_dates_acquisition_audit.json`
- `outputs_firmware_audit_v53/accepted_sequence_audit.json`
- `outputs_projected_yaw_validation_v54/run.json`
- `outputs_projected_yaw_validation_v54/protocol.json`

No historical test data was accessed.
