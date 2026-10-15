# Independent recorded-data verification - 2026-10-08

Source audit: [firmware_primary_audit_2026-10-08.md](firmware_primary_audit_2026-10-08.md).

Hypothesis: the historical acquisition audit could have hidden dropped samples,
changed raw inputs, or an assumed sample rate. Recompute those claims from the
frozen accepted recordings before accepting the source-audit conclusions.

Command: `python verify_firmware_data_v57.py`.
Outputs: `outputs_firmware_verification_v57/run.json` and `input_evidence.json`.

## Fresh results

- Exactly 473 TRAIN and 71 validation recordings opened; no test signals opened.
- Every raw CSV SHA256 matches its sealed v7 cache signature.
- Every file has the Windows raw-register-count export schema.
- All 544 recordings contain L, R and C streams.
- Zero direct sequence gaps, duplicates, backwards sequence values,
  `missing_before` counts or nonmonotonic device timestamps.
- All 15 date/sensor groups have median device interval 9766 us,
  giving 102.39606799 Hz. This is recorded polling cadence, not sensor ODR.
- All 15 date/sensor file counts, row counts and sequence-loss totals agree
  exactly with the historical v53 accepted-set audit.

This fresh verification covers every accepted recording individually, with
identities and hashes retained. Broader-folder loss statistics in v53 remain
historical evidence; they were not recomputed here. No C3D signals were opened.

## Conversion impact

The source trace establishes that Windows packet decoding and journal CSV
export preserve raw int16 values. The canonical estimator reads those values
and learns calibration on TRAIN. Repository search found the wrong firmware
scale constants in neither canonical Python motion conversion nor model input
preparation. Physical constants used in diagnostic plots are not the firmware
Info table. Correcting the Info table therefore changes no stored raw input,
cached prediction or reported metric in this pipeline: conversion-specific
numerical effect is zero; no conversion-triggered rerun is required.

The current metadata correction changes only `accel_range_g` and `encoding`
in `pipeline.settings`; a comparison against Git HEAD confirmed all estimator
and timebase settings unchanged. Existing sealed outputs were not rewritten.
Historical mobile physical-unit exports would require the 1.14688 gyro
correction; none of the accepted CSVs use that export schema.

## Remaining requirement and external evidence

A file inventory of `imu3`, `samplerawdata` and `c3d` found 739 CSVs,
934 C3Ds, eight videos and five other files. It found no `.waj`, `.bin`,
`.hex`, `.elf`, acquisition `.log`, session JSON or metadata JSON.
The firmware supports live SET_RANGE and the exported CSV omits the board Info
snapshot. Consequently exact flashed patch, resolved unpinned dependencies and
per-session range register state cannot be proven from these preserved files.

The source/data audit supports +/-4g and +/-2000dps; it cannot convert that
inference into recorded range evidence. Completing that explicit requirement
needs an original acquisition journal/metadata snapshot, serial log or archived
binary with deployment provenance. The mandatory goal is not marked complete.

## Installed receiver provenance search

The receiver source (`pc_gui/controller.py`) names the default journal root as
`~/Documents/WheelAthlete/PC Sessions`. On this computer that folder contains
only an empty `hi` directory and no journal files. No `gui_settings.json`
exists at the source-defined settings location.

The installed log at
`C:/Users/poon1/Documents/WheelAthlete/Logs/wheelathlete-windows.log`
was inspected in full (2410 bytes). It records daemon starts and disconnects
from September13 through September27, but no connected-board firmware version,
range state or session Info snapshot. Bundled `SOURCE.json` describes the
BiWheel3D model runtime, not acquisition firmware deployment.

The older project at `C:/Users/poon1/Desktop/imu` contains no `.waj`,
`.hex`, `.elf`, `.bin`, `.log` or `gui_settings.json` files in its filename
inventory. Its processed `metadata.json` files contain derived calibration and
clock information; a search found no firmware-version, range-code, board-Info
or SET_RANGE fields. No additional trajectory signals or test data were read.

The same exact-provenance blocker remains after these additional source-guided
searches. Repeating model fits, CSV scans or release comparisons cannot establish
which binary and live range settings were used. External acquisition evidence
is required before the full mandatory goal can be completed.

Conclusion: keep timestamp-based loading and raw-count calibration. Reject
rescaling existing inputs by 1.14688 or constructing acquisition time from
row/100, seq/100 or seq/104. Retained development RMSE remains 100.702119 mm;
this acquisition verification makes no new accuracy claim.
