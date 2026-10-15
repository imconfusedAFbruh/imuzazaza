# Repository map

This map is a navigation layer for the research workspace. Historical scripts,
sealed outputs, local data, and their paths are intentionally left where they are:
many scripts and audit records refer to those exact paths.

## Start here

1. [`README.md`](../README.md) — current best results, methodology, scope and run instructions.
2. [`GLOSSARY.md`](GLOSSARY.md) — terminology used in the research.
3. [`research_state/NEXT_SESSION.md`](../research_state/NEXT_SESSION.md) — current checkpoint and next justified work.
4. [`research_state/STATUS.md`](../research_state/STATUS.md) and [`TODO.md`](../research_state/TODO.md) — current status and constraints; older sections are chronological history.
5. [`research_state/BEST_RESULTS.md`](../research_state/BEST_RESULTS.md) — retained results by evaluation scope.
6. [`models/reservoir_path_v121_completed/README.md`](../models/reservoir_path_v121_completed/README.md) — usage and limitations of the retained validation model.

## Top-level layout

| Path | Contents |
| --- | --- |
| `pipeline.py`, `learning.py` and other root Python files | Core pipeline and versioned research runners, audits, reports, and compatibility code. Root-level imports and recorded paths are relied on by existing scripts. |
| `config/` | Pipeline and acquisition configuration. |
| `c3d/`, `imu3/`, `samplerawdata/` | Local reference, sensor, and raw acquisition data; data is not included in a clean clone. |
| `models/` | Frozen callable model bundles and their usage notes. |
| `experiments/v1_source/` | Source snapshot for the original experiment. |
| `research_docs/` | Protocols, methods, results, reviews, acquisition evidence, and manuscript material. |
| `research_state/` | Handoff/checkpoint files, active constraints, run receipts, verification records, and historical state. |
| `outputs*/` | Versioned experiment outputs, including failed attempts and sealed comparisons. Keep each run paired with its scripts and reports. |
| `output/pdf/` | Curated trajectory research PDF. |
| `docs/` | Glossary, project design, build notes, ADRs, and this repository map. |
| `outdatedwithonly_2imu/` | Local historical sensor recordings, excluded from Git with the other raw data. |
| `New folder/` | Additional local material; consult contents and provenance notes before use. |
| `tmp/`, `__pycache__/`, `.pytest_cache/` | Temporary and generated files. |

## Root scripts by purpose

The root is a historical script workspace rather than an installable package.
Use the filename/version and matching state/protocol documents to locate a run.

- **Core and inference:** `pipeline.py`, `learning.py`, `reservoir_inference_v121.py`, `dynamic_blend_inference_v34.py`.
- **Versioned experiments:** `*_experiment*.py`, `*_folds*.py`, `*_vNN.py`.
- **Packaging and reports:** `package_*.py`, `finalize_*.py`, `report_*.py`.
- **Audits and verification:** `audit_*.py`, `review_*.py`, `verify_*.py`, `check_*.py`, and matching `test_*.py`.
- **Plots and exports:** `plot_*.py`, `build_*.py`, `export_*.py`.

Versioned scripts are not a single linear pipeline. Check `NEXT_SESSION.md` and
the named protocol before resuming; do not rerun sealed work into an existing
`outputs*` directory.

## Current result pointers

- Best completed matched validation: frozen v121, **99.303735 mm** equal-person
  XY ATE on 71 exposed recordings. V125 was rejected by v126. The README gives
  the method and comparison route; full details are in
  [`frozen_validation_results_v126.md`](../research_docs/frozen_validation_results_v126.md).
- Best accepted matched TRAIN model: v125, **127.531627 mm**; this is a separate
  scope and did not replace v121 on validation. See
  [`axis_prior_results_v125.md`](../research_docs/axis_prior_results_v125.md).
