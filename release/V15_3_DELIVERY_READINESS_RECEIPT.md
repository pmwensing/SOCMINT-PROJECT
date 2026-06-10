# v15.3 Delivery Readiness Receipt

v15.3 adds a compact signed-style receipt that is emitted only after a v15.2
Case Delivery Handoff Verification passes.

## Route

- `POST /api/v1/case-delivery/<case_id>/readiness-receipt`

## Receipt Gate

The route and builder verify the submitted or derived v15 handoff package first.
If verification is blocked, the response returns `status: blocked` and no
receipt. If verification passes, the response returns `status: issued` with a
canonical payload hash, signature hash, and receipt id.

## Evidence

- `tests/test_v15_case_delivery_workspace.py`
- `make ci`
