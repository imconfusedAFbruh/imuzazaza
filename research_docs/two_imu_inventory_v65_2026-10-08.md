# Historical two-IMU inventory — 8 October 2026

Command: `python inventory_two_imu_v65.py` (completed; do not rerun into its existing output).
Artifacts: `outputs_two_imu_inventory_v65/inventory.json`, `run.json`.

258 files hashed; 49 metadata-bearing recordings, each with left_raw.csv and right_raw.csv and no center_raw.csv. Filenames identify exported L/R roles; July metadata additionally records sides L/R. This does not verify physical mounting or calibration.

| Session | Metadata recordings | C3Ds | Contents |
|---|---:|---:|---|
| 2026-07-31 | 30 | 39 | 37 with R_WC/L_WC, two with zero points |
| 2026-09-05 | 19 | 20 | 19 with zero points; one static L_FAL/R_FAL pair |

July references report 100 Hz. Point count is not a validity/coverage check. The 30-versus-39 mismatch needs a per-pair ledger; do not equate reference files with usable labelled recordings. September's archived capture notes accurately warn that its dynamic C3Ds have no reconstructed hub markers.

July athlete names are null. September names are Witty (8), Pluem (7), Mook (4); their relationship to numbered target participants is unknown. None is authorized for strict-track fitting or pretraining until overlap can be ruled out using existing evidence.

Both export schemas use time_us, acceleration in g and gyro in deg/s, unlike the current raw int16 schema. July example gyro values and September example gyro values have different quantization; conversion provenance needs a separate check. July metadata contains firmware 1.7.0 and large receiver drift residuals in the inspected example; current three-IMU timing assumptions cannot simply be inherited.

Size-filtered SHA256 comparison against files listed in outputs_amended_v2/inventory.json found zero exact byte matches. This does NOT establish acquisition independence: combined, scaled or re-exported CSVs can differ bytewise. All acquisitions remain preserved; no training split changed, no center signal fabricated, no C3D scored.

Next: resolve July pairing, observed marker support, existing participant clues, conversion/timebase and semantic duplication. Unknown identities stay exploratory, even if labels are usable.
