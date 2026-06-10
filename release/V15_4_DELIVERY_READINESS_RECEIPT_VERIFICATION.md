# v15.4 Delivery Readiness Receipt Verification

v15.4 verifies v15.3 Delivery Readiness Receipts before they are used as
delivery authorization evidence.

## Route

- `POST /api/v1/case-delivery/<case_id>/readiness-receipt/verify`

## Verification Checks

- Recomputes the receipt payload SHA-256 from canonical receipt fields.
- Recomputes the signed-style signature SHA-256 and receipt id.
- Confirms the receipt case id and package id match the handoff package.
- Confirms the referenced handoff package still passes v15.2 verification.
- Rejects receipts that are not marked verified or accepted for delivery.

## Evidence

- `tests/test_v15_case_delivery_workspace.py`
- `make ci`
