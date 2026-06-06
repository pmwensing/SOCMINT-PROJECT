# v13.43 - Export Blocker Manifest Hashes and Upload

## Scope

This build adds hash refresh support for export blocker screenshot artifacts and CI upload wiring for manually requested runtime screenshot artifacts.

## Included

- Screenshot artifact manifest now records `exists`, `size_bytes`, and `sha256`
- Manifest refresh script: `scripts/refresh_export_blocker_screenshot_manifest_v13_43.py`
- Makefile target: `refresh-export-blocker-screenshot-manifest`
- `make export-blocker-runtime-screenshots` refreshes the manifest after capture
- Manual CI input `upload_runtime_screenshots`
- CI artifact upload for `runtime_screenshots_v13_40/**` and the screenshot manifest
- Regression tests for manifest refresh, Makefile wiring, and CI upload wiring

## Operator Result

After a runtime screenshot capture, operators can refresh and upload a manifest that records the exact screenshot file sizes and SHA-256 hashes.
