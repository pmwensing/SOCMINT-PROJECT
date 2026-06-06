# V13.46 Export Blocker Manifest Download Audit

## Summary

- Added an explicit `screenshot_manifest_downloaded` audit action for the export blocker screenshot manifest attachment route.
- Added Export Blockers support copy that names the manifest JSON route, the audited download route, and the dedicated workflow artifact naming pattern.
- Extended route coverage so the manifest support links and workflow artifact hint stay visible in the operator UI.

## Verification

- Focused coverage: `tests/test_export_blocker_manifest_routes_v13_44.py`
- Full regression: `.venv/bin/pytest -q`
