# v16.1 Delivery Attempt Ledger

The v16.1 layer adds a deterministic delivery attempt ledger on top of the
v16.0 Delivery Operations Snapshot.

- `POST /api/v1/case-delivery/<case_id>/attempt-ledger`

The ledger records attempt rows with stable attempt ids, channel, operator,
status, retry eligibility, and detail. It summarizes delivery state as
`ready_for_attempt`, `attempt_recorded`, `retry_ready`, `delivered`, or
`blocked`.

The endpoint returns a blocked result when the underlying operations snapshot
is not dispatchable.

## Validation

- Focused regression coverage in `tests/test_v15_case_delivery_workspace.py`.
