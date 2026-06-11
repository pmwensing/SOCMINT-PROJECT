# v15.5 Delivery Authorization Record

v15.5 adds a compact delivery authorization record emitted only after the v15.4
Delivery Readiness Receipt Verification passes.

## Route

- `POST /api/v1/case-delivery/<case_id>/authorization-record`

## Authorization Gate

The authorization record verifies the delivery readiness receipt and the
referenced handoff package before issuing an authorization object. Failed
receipt or package verification returns `status: blocked` and no authorization.

## Evidence

- `tests/test_v15_case_delivery_workspace.py`
- `make ci`
