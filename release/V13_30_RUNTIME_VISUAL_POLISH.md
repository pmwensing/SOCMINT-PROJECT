# v13.30 - Runtime Visual Polish

## Purpose

Document runtime visual stylesheet coverage and full-report retention input hardening.

## Added

- Runtime visual stylesheet loading from the shared base template.
- CSS wrapping guards for long runtime values in `pre` and `code` surfaces.
- Runtime utility page/card classes for the full-report retention UI.
- Guarded integer parsing for retention `keep_latest` values in UI and API paths.

## Verification

- `tests/test_v13_30_runtime_visual_polish.py`

## Value

Long artifact and runtime values remain readable in browser views, and invalid retention inputs fall back safely instead of breaking the page.
