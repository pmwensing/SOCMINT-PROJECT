# v13.27 - Full Report History Runtime Safety

## Purpose

Harden full-report export history so runtime pages and APIs degrade cleanly when the dossier root is unavailable.

## Added

- Safe `full_report_export_history` behavior when `dossier_root()` raises an `OSError`.
- Structured unavailable response payloads with `available: false`, an empty export list, and the captured error.

## Verification

- `tests/test_v13_27_full_report_history_runtime_safe.py`

## Value

Operators get a controlled empty-history response instead of a runtime failure when the export history directory cannot be read.
