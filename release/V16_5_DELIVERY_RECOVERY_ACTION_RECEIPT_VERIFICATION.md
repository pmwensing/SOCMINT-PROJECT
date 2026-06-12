# v16.5 Delivery Recovery Action Receipt Verification

The v16.5 layer verifies v16.4 Delivery Recovery Action Receipts against the v16.3 recovery queue.

- `POST /api/v1/case-delivery/<case_id>/recovery-action-receipt/verify`

The verifier recomputes canonical receipt ids, checks queue linkage, verifies each action receipt id, and confirms that action fields match the corresponding v16.3 `operator_recovery_queue` item.

## Verification checks

- `receipt_id` must match the canonical receipt payload.
- `queue_id`, `case_id`, and `recovery_state` must match the recovery queue.
- Each action `recovery_id` must exist in the v16.3 recovery queue.
- Each `action_receipt_id` must match the canonical action payload.
- Decision, category, attempt, queue state, and recommendation fields must match the recovery queue item.
- Completed flags must match the action status.
- Verification blocks when the underlying recovery queue is blocked or when receipt content is tampered.

## Validation

- Focused regression coverage in `tests/test_v16_5_case_delivery_recovery_action_receipt_verification.py`.
- No database schema mutation or migration is introduced.
