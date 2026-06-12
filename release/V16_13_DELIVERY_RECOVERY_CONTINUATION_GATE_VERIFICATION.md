# v16.13 Delivery Recovery Continuation Gate Verification

The v16.13 layer verifies v16.12 delivery recovery continuation gates.

- `POST /api/v1/case-delivery/<case_id>/recovery-continuation-gate/verify`

The verifier recomputes the continuation gate payload hash and continuation gate id, checks finalization verification linkage, confirms the gate is open and ready for delivery continuation, and enforces `next_action: resume_delivery_operations`.

## Verification checks

- `payload_sha256` must match the canonical continuation gate payload.
- `continuation_gate_id` must match the canonical gate payload plus payload hash.
- v16.11 finalization verification must remain verified and ready for delivery continuation.
- Queue, case, finalization, and audit package linkage must remain consistent.
- `gate_open` and `ready_for_delivery_continuation` must be true.
- `next_action` must be `resume_delivery_operations`.
- Tampered or closed continuation gates block verification.

## Validation

- Focused regression coverage in `tests/test_v16_13_case_delivery_recovery_continuation_gate_verification.py`.
- No database schema mutation or migration is introduced.
