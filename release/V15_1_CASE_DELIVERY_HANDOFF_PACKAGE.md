# v15.1 Case Delivery Handoff Package

v15.1 turns the v15 Case Delivery Workspace decision into a deterministic
operator handoff package.

## Routes

- `POST /api/v1/case-delivery/<case_id>/handoff-package`
- `POST /api/v1/case-delivery/<case_id>/handoff-package/markdown`

## Package Gate

The package reuses the v15 workspace gate. `READY_FOR_DELIVERY` produces a
`deliver` disposition with an accepted operator receipt. Any blocker produces a
`hold` disposition with remediation actions derived from the failed gate checks.

## Evidence

- `tests/test_v15_case_delivery_workspace.py`
- `make ci`
