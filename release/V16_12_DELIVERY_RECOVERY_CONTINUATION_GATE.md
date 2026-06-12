# v16.12 Delivery Recovery Continuation Gate

The v16.12 layer opens the continuation gate after v16.11 verifies the delivery recovery finalization record.

- `POST /api/v1/case-delivery/<case_id>/recovery-continuation-gate`

The continuation gate requires verified finalization verification, emits a deterministic `continuation_gate_id`, and marks the recovery chain ready to resume delivery operations.

## Gate checks

- v16.11 finalization verification must be verified.
- Finalization verification must be ready for delivery continuation.
- Recovery and finalization queue linkage must remain consistent.
- Finalization id and audit package id must match the verification artifact.
- Blocked or failed finalization verification prevents gate opening.
- Open gates return `next_action: resume_delivery_operations`.

## Validation

- Focused regression coverage in `tests/test_v16_12_case_delivery_recovery_continuation_gate.py`.
- No database schema mutation or migration is introduced.
