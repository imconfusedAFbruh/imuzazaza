# Primary-source firmware and receiver audit

Date: 2026-10-08  
Authoritative repository: <https://github.com/NnopponS/WheelAthelse>  
Repository HEAD inspected: [`1e856768588ab5f107797ee665be5604cb8119e2`](https://github.com/NnopponS/WheelAthelse/commit/1e856768588ab5f107797ee665be5604cb8119e2)

Dataset totals and sequence/cadence statistics below cite the existing v53
data-audit artifacts. The source and receiver checks were repeated on
2026-10-08; those statistics should not be described as a fresh full-dataset
recomputation in this session.

Subsequent root verification independently recomputed the 544 accepted files:
see [firmware_data_verification_2026-10-08.md](firmware_data_verification_2026-10-08.md).
All accepted file/row/gap totals agree with v53 and all raw hashes match sealed
cache signatures. The broader 739-file aggregates remain historical evidence.

## Verdict

| Question | Finding | Evidence strength |
|---|---|---|
| Accel range in the September data | **Approximately ±4 g**, not ±2 g | Strong inference: firmware and Windows GUI default to range code 1, and recorded gravity is about 8.2k counts, which matches 0.122 mg/LSB at ±4 g. The CSV does not carry the range code, so the exact per-board setting is not directly proven. |
| Gyro range | **Approximately ±2000 dps** | Strong inference: firmware and GUI default to range code 3; train-only empirical count-to-yaw fits are consistent with about 0.070 dps/LSB. The CSV does not carry the range code. |
| CSV axis values | Signed raw `int16` register counts | Proven by firmware packet layout, Windows parser/journal/exporter, and the exact recorded CSV schema. |
| Correct conversion at these ranges | accel: `raw * 0.000122 g`; gyro: `raw * 0.070 dps` | Proven by the ST datasheet, ST's driver, and Seeed's conversion implementation. |
| Firmware Info gyro scale | `2000/32768 = 0.06103515625 dps/LSB`, **12.8069% too low** | Proven source bug. Values converted with it need multiplication by `1.14688`. |
| Effect on the research CSV/model results | **No numerical correction or rerun is required for this bug** | The Windows CSV contains unchanged raw counts and the research pipeline fits motion calibration from raw counts. The bad Info scale is not applied. |
| Requested rate / sensor ODR / recorded cadence | 100 Hz / 104 Hz / approximately 102.4 Hz | Proven by source for request and ODR; the 102.4 Hz cadence is independently measured in all five acquisition dates. |
| Primary sample clock | Per-sample midpoint of a firmware `micros()` register read | Proven by source and present in every CSV row as `timestamp_device_us`. |
| PC timestamp | One monotonic arrival timestamp per BLE notification, shared by every sample in the batch | Proven by receiver source and about 90% repeated adjacent timestamps in the recordings. |
| Sequence loss | Loss exists in the broader Sep-24 folder; the exact 544 accepted v42 recordings have no gaps, duplicates, or out-of-order samples | Reported by the pre-existing v53 dataset audits, which recomputed the recorded sequence fields. That full scan was not rerun on 2026-10-08. |
| Exact flashed firmware patch | **Not recoverable from the exported CSVs** | The Windows journal stored board Info metadata, including firmware and ranges, but `export_csv` omitted it. No `.waj`, serial log, or firmware binary is present with the dataset. |

This corrects the earlier ±2 g assumption. It also corrects the release identities used in the 2026-10-05 audit: the table below gives the actual peeled tag commits rather than intermediate release-preparation commits.

## 1. Version provenance

The Git tag refs and peeled commits are:

| Tag | Tag ref object | Peeled commit | Commit time |
|---|---|---|---|
| v1.8.1 | `00bb22647d6b39a70e9e17ffb4d9c89a53ddb85d` | [`30e99d83ae9d0da072721306f65501a35024813a`](https://github.com/NnopponS/WheelAthelse/commit/30e99d83ae9d0da072721306f65501a35024813a) | 2026-09-08 21:56 +07:00 |
| v1.8.2 | `c398a0fef84b1f29c1ec26c190b74638c1f7d44f` | [`be079ebf2a5c378985070452683e7b61fbec30eb`](https://github.com/NnopponS/WheelAthelse/commit/be079ebf2a5c378985070452683e7b61fbec30eb) | 2026-09-15 18:18 +07:00 |
| v1.8.3 | `9bc62677f2cf5555d00616ec8270fee8b7869368` | [`9bc62677f2cf5555d00616ec8270fee8b7869368`](https://github.com/NnopponS/WheelAthelse/commit/9bc62677f2cf5555d00616ec8270fee8b7869368) | 2026-09-19 16:15 +07:00 |
| v1.8.4 | `037824f585077498799837ac6917815aa4141201` | [`80cae399f7dd5909c93e2dd6acdc927871518c8b`](https://github.com/NnopponS/WheelAthelse/commit/80cae399f7dd5909c93e2dd6acdc927871518c8b) | 2026-09-25 20:26 +07:00 |

The three acquisition-core blobs are identical in every peeled release commit above:

- `imu_reader.cpp`: `51beb2626e3901f540b8684ae3c922c37def78d9`
- `imu_reader.h`: `020410dda81639ce58733090aefc3c085628e29e`
- `imu_types.h`: `066bd7c6c789e70193473233768ca0c501ba19aa`

`ble_types.h`, which defines the raw 20-byte wire sample, is also identical: `b2c9dd1d1ff0e34a496bd0f5ae269ee82a01d6f9`. The only `ble_service.cpp` change between v1.8.1 and later tags changes whether the UI reports a cumulative or consecutive transport-retry state; it does not change sample acquisition, packet contents, or START/STOP timestamps.

The acquisition dates are Sep 9, 11, 19, 24, and 25. Release timing supplies plausible versions, but does not prove what binary was flashed. More importantly, `platformio.ini` uses unpinned Git dependencies and the exported CSV excludes the connected-board Info snapshot. The exact firmware patch, resolved Seeed library commit, and any operator-issued `SET_RANGE` therefore remain unprovable from the preserved CSVs alone.

The narrowest defensible date mapping is: Sep 9 is compatible with v1.8.1; Sep 11 falls after the `667a7e09` v1.8.2 repair-preparation commit but before the final v1.8.2 tag; Sep 19 is compatible with v1.8.3; and Sep 24/25 are compatible with v1.8.4-era preparation/candidate source. This is source-date compatibility, not flashed-binary identification. The stable acquisition-core blobs make the range, ODR, timestamp, and raw packet conclusions insensitive to which of those compatible revisions was installed.

## 2. Range configuration

The XIAO entry point calls `imu().begin(configStore().rateHz())` without range arguments ([`main.cpp` lines 48–50](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/main.cpp#L48-L50)). `ImuReader::begin` defaults to `AccelRange::G4` and `GyroRange::DPS2000` ([`imu_reader.h` lines 12–14](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_reader.h#L12-L14)). `configureImu` maps those enum values to `accelRange=4` and `gyroRange=2000` in the Seeed driver ([`imu_reader.cpp` lines 144–171](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_reader.cpp#L144-L171)).

The Windows settings UI independently defaults to ±4 g and ±2000 dps ([`main_window.py` lines 1027–1043](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_gui/main_window.py#L1027-L1043)). Applying settings sends both range codes and then re-reads the device Info characteristic ([`service.py` lines 643–680](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/service.py#L643-L680)). The firmware accepts `SET_RANGE` at runtime ([`ble_service.cpp` lines 436–445](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_service.cpp#L436-L445)), but range is not part of the persisted `BoardConfig`; only name, wheel ID, and requested rate are persisted ([`config_store.h` lines 54–100](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/config_store.h#L54-L100)). A reboot therefore restores the firmware range defaults.

Dataset evidence strongly disambiguates ±4 g from ±2 g. Across all dates and roles, median acceleration norm is approximately 8164–8255 counts ([local all-date audit](../outputs_firmware_audit_v53/all_dates_acquisition_audit.json)). At the ST ±4 g sensitivity, 1 g is `1 / 0.000122 = 8196.7` counts. At ±2 g, 1 g would be `1 / 0.000061 = 16393.4` counts. This makes ±4 g the defensible setting for the September recordings, while preserving the limitation that no CSV row directly records a range code.

## 3. Correct raw-to-physical conversion and the scale-table defect

The official ST LSM6DS3TR-C datasheet specifies:

- ±4 g: **0.122 mg/LSB**
- ±2000 dps: **70 mdps/LSB**

See [ST LSM6DS3TR-C datasheet, Table 3, page 21](https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf). ST's own driver implements `raw * 0.122 mg` at ±4 g and `raw * 70 mdps` at ±2000 dps ([ST driver accel conversion](https://github.com/STMicroelectronics/lsm6ds3tr-c-pid/blob/83f1e3f783a9d4693705f3559afd147fca774062/lsm6ds3tr-c_reg.c#L107-L110), [gyro conversion](https://github.com/STMicroelectronics/lsm6ds3tr-c-pid/blob/83f1e3f783a9d4693705f3559afd147fca774062/lsm6ds3tr-c_reg.c#L142-L145)).

Seeed's library agrees. `calcAccel` uses `raw * 0.061 * (range >> 1) / 1000`, giving `0.000122 g/LSB` at range 4 ([Seeed `calcAccel`](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/4ceed57ef83bfa6213659fc4377612af6e38002f/LSM6DS3.cpp#L671-L674)). `calcGyro` uses `raw * 4.375 * (range/125) / 1000`, giving `0.070 dps/LSB` at range 2000 ([Seeed `calcGyro`](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/4ceed57ef83bfa6213659fc4377612af6e38002f/LSM6DS3.cpp#L732-L739)). These formulas have been unchanged since 2020, although WheelAthelse's unpinned dependency prevents proving which Seeed commit was resolved in a historical build.

WheelAthelse's Info scale table instead uses full-scale divided by 32768 for every setting ([`imu_types.h` lines 47–70](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_types.h#L47-L70)):

| Quantity | Firmware Info scale | Correct ST scale | Error |
|---|---:|---:|---:|
| accel ±4 g | 0.0001220703125 g/LSB | 0.000122 g/LSB | +0.0576% |
| gyro ±2000 dps | 0.06103515625 dps/LSB | 0.070 dps/LSB | −12.8069% |

Any physical-unit gyro values created from the firmware Info scale require `0.070 / 0.06103515625 = 1.14688` multiplication. This affects the mobile path because it multiplies samples by the Info scales ([`imu_packet.dart` lines 64–83](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_mobile/lib/ble/imu_packet.dart#L64-L83)) and exports physical-unit columns ([`csv_exporter.dart` lines 38–50](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_mobile/lib/export/csv_exporter.dart#L38-L50)).

It does **not** affect the research CSVs. The firmware transmits raw `int16` axes ([`imu_types.h` lines 37–45](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_types.h#L37-L45)); the Windows receiver decodes `<IIhhhhhh` without conversion ([`protocol.py` lines 9–43](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/protocol.py#L9-L43)); the journal stores those integers unchanged ([`journal.py` lines 234–258](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/journal.py#L234-L258)); and CSV export writes them as `*_raw` ([`journal.py` lines 440–497](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/journal.py#L440-L497)). The pre-existing v53 all-date audit reports that all 739 preserved CSVs have that exact Windows schema, not either mobile schema; this turn spot-checked one CSV from each acquisition date ([local all-date audit](../outputs_firmware_audit_v53/all_dates_acquisition_audit.json)).

## 4. Sampling, timestamps, and effective frequency

For a requested 100 Hz rate, the firmware configures both accelerometer and gyro sensor ODR to **104 Hz** ([`imu_reader.cpp` lines 161–171](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_reader.cpp#L161-L171)). It does not use FIFO or DRDY. A FreeRTOS loop waits `pdMS_TO_TICKS(1000 / rate_hz_)`, then performs one contiguous 12-byte register read ([`imu_reader.cpp` lines 187–229](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_reader.cpp#L187-L229)).

The Adafruit nRF52 core used by the selected board environment defines `configTICK_RATE_HZ 1024` ([primary core configuration](https://github.com/adafruit/Adafruit_nRF52_Arduino/blob/343ab5fe7fb3d5657d3176883dfb188d65b79f06/cores/nRF5/freertos/config/FreeRTOSConfig.h#L55-L55)). Integer `1000/100` becomes 10 ms before tick conversion, yielding 10 ticks = 9.765625 ms, or 102.4 polls/s. The recorded data independently shows a 9765/9766 µs dominant interval and 102.3961 Hz median effective cadence for every L/R/C role on all five dates ([local all-date audit](../outputs_firmware_audit_v53/all_dates_acquisition_audit.json)).

These rates must remain distinct:

1. configured application request: 100 Hz;
2. sensor output-data rate: 104 Hz;
3. polling and recorded sample cadence: about 102.4 Hz;
4. downstream model grid: 100 Hz after timestamp-based resampling.

Since the 104 Hz sensor can update between 102.4 Hz polls, roughly 1.6 sensor updates per second are never individually observed. Sequence numbers count firmware polls, not sensor ODR frames, so this overwrite cannot appear as a sequence gap. Relative sensor-update age can vary over approximately one 104 Hz period (about 9.6 ms).

For each successful burst read, firmware stores the midpoint of `read_started_us` and `read_finished_us` as `t_device_us` and increments a `uint32` sequence ([`imu_reader.cpp` lines 198–225](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/imu_reader.cpp#L198-L225)). `micros()` therefore timestamps the host-side register read, not the hidden sensor conversion instant. Its 32-bit wrap is about 71.6 minutes; the accepted recordings are shorter and contain no non-monotonic device timestamps.

## 5. BLE packet decoding, PC timestamps, and CSV writing

Each wire sample is 20 bytes: `seq u32`, `t_device_us u32`, then six raw signed 16-bit axes. Firmware packs those values unchanged and prefixes each notification with a sample count ([`ble_types.h` lines 75–93](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_types.h#L75-L93)). At requested 100 Hz it targets about ten notifications per second, normally ten samples per notification ([`ble_types.h` lines 104–112](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_types.h#L104-L112)). Ten is also the modal batch size on every acquisition date.

The Windows BLE callback records one `time.perf_counter_ns()` value when the notification arrives ([`transport.py` lines 142–151](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/transport.py#L142-L151)). The ingestor assigns that same arrival timestamp and packet ID to every decoded sample in the notification ([`engine.py` lines 190–214](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/engine.py#L190-L214)). This explains the measured approximately 90% adjacent repetition rate in `timestamp_pc_monotonic_ns`. PC timestamps are packet-arrival anchors, not physical sample timestamps.

The research pipeline correctly uses device time inside packets. It fits an affine device-to-PC mapping using the last row of each repeated packet timestamp, reconstructs all per-sample times from `timestamp_device_us`, and only then resamples to the 100 Hz model grid ([local `pipeline.py` lines 277–308](../pipeline.py#L277-L308)). Replacing this with row number divided by 100 would be wrong; the measured median duration inflation was about 2.4% in the audited Sep 9/11 recordings ([local timing audit](../outputs_firmware_audit_v53/dataset_timing_audit.json)).

## 6. Sequence gaps and dropped samples

The Windows receiver classifies each sample as first, contiguous, gap, duplicate, or out-of-order with wrap-aware sequence arithmetic ([`sequence.py` lines 26–74](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/sequence.py#L26-L74)). Those classifications and `missing_before` counts are written into every CSV row.

The pre-existing v53 full-dataset scan reports no recomputed sequence loss for Sep 9, 11, 19, or 25. It reports substantial gaps in some non-accepted Sep-24 recordings: recorded `missing_before` sums are 13,160 / 13,340 / 13,320 for L/R/C, while its direct sequence recomputation totals 18,544 / 18,653 / 18,463 missing values ([local all-date audit](../outputs_firmware_audit_v53/all_dates_acquisition_audit.json)). The 739-file scan was not rerun during this source audit.

For the exact 544 recordings used by v42 (473 train and 71 held validation), the pre-existing v53 accepted-set audit reports zero affected trials, zero missing samples, zero duplicates, and zero out-of-order rows across all roles and dates ([local accepted-set audit](../outputs_firmware_audit_v53/accepted_sequence_audit.json)). Subject to that audit artifact, BLE sequence loss is not an explanation for current accepted-set RMSE. The audit does not detect sensor frames overwritten between 104 Hz updates and 102.4 Hz polls.

## 7. START, STOP, and SYNC semantics

On START, firmware clears replay and pending state, resets the IMU queue and sequence, then either starts immediately or waits for a scheduled device-time target ([`ble_service.cpp` lines 361–385](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_service.cpp#L361-L385)). A scheduled start fires when the wrapping device clock reaches the target and emits `START_FIRED` ([`ble_service.cpp` lines 687–741](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_service.cpp#L687-L741)).

`SYNC_PING` captures a current device `micros()` value and echoes it with the host token ([`ble_service.cpp` lines 424–433](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_service.cpp#L424-L433)). The PC collects multiple round-trip observations and fits an affine clock model ([`lifecycle.py` lines 91–128](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/lifecycle.py#L91-L128)); scheduled device targets are derived from one PC T0 ([`lifecycle.py` lines 130–211](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/lifecycle.py#L130-L211)).

On STOP, firmware stops polling, records device `micros()`, drains the IMU queue and pending BLE batch, waits for a short empty condition, publishes health, and sends `STOP_FIRED` ([`ble_service.cpp` lines 388–399](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_service.cpp#L388-L399), [`ble_service.cpp` lines 836–858](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/hardware_firmware/xiao_nrf52840_sense/src/ble_service.cpp#L836-L858)). The Windows journal records pre-start clock fits, START, STOP, health, and best-effort post-stop clock refinement ([`service.py` lines 786–873](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/service.py#L786-L873), [`service.py` lines 900–939](https://github.com/NnopponS/WheelAthelse/blob/1e856768588ab5f107797ee665be5604cb8119e2/applications/wheelathlete_windows/tools/pc_acquisition/service.py#L900-L939)).

The CSV exporter writes only sample rows. It omits the journal's Info snapshot, START/STOP events, SYNC observations, and health records. Preserving only CSV therefore discarded exactly the metadata needed to prove the flashed firmware and explicit range state.

## 8. Impact on existing trajectory results

The canonical research loader reads `timestamp_device_us`, packet-level PC timestamps, raw axes, and `missing_before` directly. It retains raw counts and learns train-only empirical raw-to-motion calibration ([local `pipeline.py` lines 277–308](../pipeline.py#L277-L308), [lines 532–574](../pipeline.py#L532-L574)). Repository search finds no canonical Python model path applying the firmware Info `gyro_scale` or `accel_scale` to these CSV fields.

Therefore:

- do not multiply v34, v42, or later raw inputs by 1.14688;
- do not reinterpret rows as 100 Hz or 104 Hz samples;
- keep the current device-timestamp/packet-anchor affine timing path;
- no existing raw-count result changes numerically because of the firmware Info scale-table bug;
- no wholesale retraining is justified by this audit alone.

The stale ±2 g statements in configuration/report prose are provenance errors. They should be corrected in current documentation, but sealed historical results should remain unchanged. The remaining acquisition uncertainty is the unobserved sensor-update phase of up to roughly one 104 Hz period, plus the missing exact flashed-version/range metadata.

## Required provenance for future acquisitions

Preserve the `.waj` journal or an equivalent sidecar containing, for every board:

- firmware version and preferably binary hash;
- range codes and correct ST sensitivities;
- requested rate, sensor ODR, and observed effective rate;
- pre/post affine clock observations;
- START/STOP events and UTC/monotonic anchors;
- sequence, transport, queue, and health counters.

Pin the PlatformIO platform and Seeed library to immutable commits. Correct the firmware Info gyro table to the ST sensitivity values before using mobile physical-unit exports.

## Audit boundary

Root verification on 2026-10-08: 18 existing Windows receiver tests passed:
`python -m pytest tools/pc_acquisition/tests/test_journal_qc.py tools/pc_acquisition/tests/test_ingestion_core.py tools/pc_acquisition/tests/test_sync_lifecycle.py tools/pc_acquisition/tests/test_sequence_epoch.py -q`
from `applications/wheelathlete_windows` in the authoritative checkout. These
exercise journal/export, ingestion, event decoding/lifecycle and sequence epochs;
they do not prove which historical binary was flashed.

Current `config/default.yaml` and `pipeline.settings` metadata were corrected to
supported +/-4g and raw int16 encoding. The range field has no numerical consumer
in the canonical Python estimator. Historical sealed copies were preserved.

This report establishes the acquisition behavior shared by the source revisions compatible with the dataset and verifies the preserved CSV path from source. It directly inspected one recorded CSV from each of the five dates, but relied on the existing v53 JSON artifacts for the 739-file and accepted-544-file aggregate statistics rather than rerunning those scans. It cannot prove the exact binary flashed on each board because the required Info/journal artifacts are absent. Range conclusions are therefore explicitly reported as strong, data-supported inference rather than direct per-session metadata.
