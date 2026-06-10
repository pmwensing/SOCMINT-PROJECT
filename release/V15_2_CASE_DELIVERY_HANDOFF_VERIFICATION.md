# v15.2 Case Delivery Handoff Verification

v15.2 adds an explicit verification layer for v15.1 Case Delivery Handoff
Packages before they are treated as deliverable artifacts.

## Route

- `POST /api/v1/case-delivery/<case_id>/handoff-package/verify`

## Verification Checks

- Required handoff manifest files are present.
- Manifest content type, size, and SHA-256 rows match derived package content.
- The package gate matches the embedded workspace gate.
- The package gate decision and deliver/hold disposition remain consistent.
- The package case id matches the embedded workspace case id.

## Evidence

- `tests/test_v15_case_delivery_workspace.py`
- `make ci`
