# v16.0 Delivery Operations Snapshot

The v16.0 line starts post-authorization delivery operations without adding a
new v15 gate. It consumes the v15.6 Delivery Execution Envelope and emits an
operator-facing delivery operations snapshot.

- `POST /api/v1/case-delivery/<case_id>/operations`

The snapshot reports dispatch state, execution id, authorization id, event
rollup, deterministic operation id, blockers, and next action. It returns a
blocked result when the execution envelope is not ready or when the operator
event log records a blocking exception.

## Validation

- Focused regression coverage in `tests/test_v15_case_delivery_workspace.py`.
