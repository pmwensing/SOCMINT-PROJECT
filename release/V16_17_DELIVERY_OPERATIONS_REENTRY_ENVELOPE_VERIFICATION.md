# v16.17 Delivery Operations Re-Entry Envelope Verification

The v16.17 layer verifies v16.16 delivery operations re-entry envelopes.

- `POST /api/v1/case-delivery/<case_id>/operations-reentry-envelope/verify`

The verifier recomputes the re-entry envelope payload hash and re-entry envelope id, checks v16.15 resume snapshot verification linkage, confirms the envelope is ready for operations dispatch, and enforces `next_action: dispatch_delivery_operations`.

## Verification checks

- `payload_sha256` must match the canonical re-entry envelope payload.
- `reentry_envelope_id` must match the canonical re-entry envelope payload plus payload hash.
- v16.15 resume snapshot verification must remain verified and safe to re-enter operations.
- Queue, case, and resume snapshot linkage must remain consistent.
- `ready_for_operations_dispatch` must be true.
- `next_action` must be `dispatch_delivery_operations`.
- Tampered or non-dispatchable re-entry envelopes block verification.

## Validation

- Focused regression coverage in `tests/test_v16_17_case_delivery_operations_reentry_envelope_verification.py`.
- No database schema mutation or migration is introduced.
