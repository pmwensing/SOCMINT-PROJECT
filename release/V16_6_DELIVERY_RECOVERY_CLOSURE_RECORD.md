# v16.6 Delivery Recovery Closure Record

The v16.6 layer closes the v16 delivery recovery workflow after v16.5 verifies the v16.4 receipt.

- `POST /api/v1/case-delivery/<case_id>/recovery-closure-record`

The closure record requires verified receipt input and only closes when the receipt status is `completed` or `no_action_required`. It emits a deterministic `closure_id` from canonical JSON and blocks pending or unverifiable receipts.

## Closure checks

- v16.5 receipt verification must pass.
- Receipt status must be complete or require no action.
- Receipt and queue linkage must remain valid through verification.
- Pending receipts block closure.
- The record captures queue id, receipt id, verification status, receipt status, action counts, closer, payload hash, and closure id.

## Validation

- Focused regression coverage in `tests/test_v16_6_case_delivery_recovery_closure_record.py`.
- No database schema mutation or migration is introduced.
