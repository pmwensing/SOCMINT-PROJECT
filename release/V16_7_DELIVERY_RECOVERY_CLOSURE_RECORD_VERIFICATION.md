# v16.7 Delivery Recovery Closure Record Verification

The v16.7 layer verifies v16.6 closure records for the v16 delivery recovery workflow.

- `POST /api/v1/case-delivery/<case_id>/recovery-closure-record/verify`

The verifier recomputes the closure payload hash and closure id, checks receipt and queue linkage, and confirms that the embedded receipt verification remains valid.

## Verification checks

- `payload_sha256` must match the canonical closure payload.
- `closure_id` must match the canonical closure payload plus payload hash.
- `queue_id`, `case_id`, and `receipt_id` must match the recovery queue and receipt.
- Receipt verification status must remain verified.
- Closure status fields and action counts must match the receipt.
- Pending or incomplete receipts block verification.

## Validation

- Focused regression coverage in `tests/test_v16_7_case_delivery_recovery_closure_record_verification.py`.
- No database schema mutation or migration is introduced.
