# Sensor encoding evidence and verification path

Research date: 2026-10-03. User-confirmed actual acquisition remains **accelerometer ±2 g, gyro ±2000°/s**. No acquisition range, raw file, model or frozen calibration was changed. This note distinguishes hardware configuration, library conversion, packet encoding and CSV serialization.

## What the local folder establishes

A workspace-wide file search, including hidden files, found no acquisition `.ino`, `.cpp`, `.c`, `.h`, `.hex`, `.uf2`, `.bin`, firmware archive or logger source. Python reconstruction/experiments, sensor CSVs and research notes are present. Searching `readFloatAccel`, `readRawAccel`, `LSM6DS3`, `ax_raw`, `gx_raw` and range/scale terms found analysis references, not the executed logger/packet-packing implementation. Thus the September firmware version and CSV integer transform cannot be recovered from the uploaded source evidence alone.

`config/default.yaml` explicitly records `accel_range_g: 2`, `gyro_range_dps: 2000`, `format: integer_encoding_unknown`, and `verified: false`. `pipeline.settings` likewise labels conversion empirical. CSV field names `_raw` do not identify what entered the integer field. Prior packet analysis establishes batched timing, but contains no packet byte layout or serialization expression. See `research_docs/acquisition-evidence-status.md` and `research_docs/deep-research-report.md`.

Training-fitted v7 calibration records the following rest acceleration norm scales (counts per empirical g), from `outputs_observed_reference_v7/calibration.json`:

| Setup | Left | Right | Center | Center yaw rad/s per CSV count |
|---|---:|---:|---:|---:|
| Sep09 |8189.89|8224.72|8158.96|0.001231558|
| Sep11 |8189.89|8216.99|8162.56|0.001219571|
| Sep19 |8186.87|8212.98|8167.78|0.001224484|
| Sep24 |8188.31|8211.56|8175.24|0.001246669|
| Sep25 |8195.85|8222.13|8182.67|0.001256344|

These are trained effective scales, not verified register sensitivities. Wheel term scales additionally include radius and joint midpoint fitting and are not directly gyro rad/s scales.

## Manufacturer facts, conditional on register-count storage

ST Table3 specifies acceleration sensitivity0.061/0.122/0.244/0.488 mg/LSB for ±2/4/8/16 g, respectively; nominal1 g register norms are16393/8197/4098/2049. Gyro ±2000°/s sensitivity is0.070°/s/LSB =0.001221730 rad/s/LSB. Outputs are signed16-bit two's-complement words. `CTRL1_XL`0x10 full-scale bits3:2 encode00/01/10/11 as2/16/4/8 g. `CTRL2_G`0x11 bits3:2 select gyro range;2000°/s uses11 with125°/s override disabled. [ST datasheet Tables3,50–54 and output-register sections](https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf).

The approximate8200 rest norm disagrees with direct, unscaled ±2 g register storage. It is compatible numerically with ±4 g register storage **or** an encoding transform; that ambiguity does not establish a different acquisition setting. Gyro effective scale agreement likewise supports a plausible raw-gyro interpretation but proves neither acceleration encoding nor unchanged gyro serialization.

## What the Seeed library actually does

Current Seeed source distinguishes `readRawAccelX` returning a signed register value and `readFloatAccelX` applying `calcAccel`. Its conversion multiplies raw acceleration by0.061 times half the configured range, then divides1000, giving g. `calcGyro` similarly gives degrees/s using the configured range. Constructor defaults are16 g and2000°/s; acquisition code can override settings before `.begin()`, which writes corresponding register bits. Therefore the library default is not proof of actual acquisition. Updating settings after initialization can also change float conversion without establishing that hardware registers changed. No uploaded executed acquisition code demonstrates either case. [Seeed maintained implementation](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/master/LSM6DS3.cpp), [raw source](https://raw.githubusercontent.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/master/LSM6DS3.cpp).

These are current upstream `master` references read on the research date, not a pinned September acquisition dependency revision. The library's read functions do not specify this logger's BLE packing or PC CSV integer conversion.

## Existing extrema constrain simple hypotheses

`outputs_acceleration_diagnosis_v10/raw_extrema.csv` shows PS No.18 Trial2 right `ay_raw` minimum−19045, maximum15490, and only one occurrence of each extreme. Each other sensor/axis also lacks repeated extreme plateaus. No test acquisition was opened for this note.

For a hypothetical direct ±2 g register interpretation,19045 counts converts to1.161745 g on that axis; empirical8200 normalization gives2.32256 g equivalents. Thus the two interpretations materially change a clipping diagnosis. A vector norm above2 g is insufficient evidence that any axis clips.

The simplest alternative “CSV equals register divided by2, without offset” would have a signed16-bit-register output bound of approximately±16384 CSV counts. The−19045 value contradicts that specific global transform on the right acceleration stream. It does **not** exclude different transforms, offsets, float scaling, range-dependent packing, mixed metadata or decoding errors. It is useful to reject one oversimplified explanation without declaring the actual hardware range. Sparse samples and unknown encoding mean lack of plateaus cannot definitively rule out physical clipping.

## Concrete verification action

Obtain the actual executed acquisition firmware and PC receiver source, library commit/version and September build/flash identity. Identify, in order: range assignment before initialization; register writes/readback; raw versus float read calls; arithmetic before cast; integer type and rounding; BLE byte order/packet layout; PC unpacking; saved scale values and CSV expression. A settings file alone does not establish that path.

For a repeat using the same firmware/device, log simultaneous raw register words, library floats, BLE-decoded values and final CSV fields for L/R/C. Save configuration register bytes after initialization and at recording end, software settings, firmware/library hashes and sensor ID. Six stationary orientations per sensor identify affine axis scale/bias; known rotations identify gyro scale/sign and integration units. A new repeat validates the current chain; connecting it to September data still requires firmware identity or archived provenance.

Decode acceleration range with `(CTRL1_XL >> 2) & 3`, and gyro range with `(CTRL2_G >> 2) & 3`, checking the separate125°/s override bit. Record ODR/filter settings and endianness/block-data-update configuration as well. Compare the actual serialized integer against both raw and float samples, fitting no arbitrary trajectory-based correction to choose an encoding.

## Measurable impacts available without inventing units

1. Report per-sensor training-only effective rest scales and axis extrema against candidate encoding bounds. Keep each candidate conditional; do not silently choose±4 g or multiply by2 because its norm is convenient.
2. The existing supervised predictor normalizes acceleration by its fitted counts-per-g and refits raw gyro conversion. A consistent constant raw rescale accompanied by identical refitting can cancel algebraically; changing the declared range alone is not an expected trajectory improvement. Retraining features must be consistent.
3. Physical acceleration integration, gravity subtraction, noise models, clipping gates and SI skid thresholds are different: an unverified factor2 changes their physical interpretation and can invalidate them. Resolve encoding before claiming calibrated Wheel-INS, TLIO-style physical preintegration, or a2.5 m/s² skid threshold.
4. Independent six-face/known-angle calibration could measure anisotropy, bias and misalignment that scalar rest normalization hides. Any resulting estimator amendment needs a versioned training/validation comparison on the unchanged observed-reference scoring protocol. No numerical RMSE gain is claimed by this evidence review.
