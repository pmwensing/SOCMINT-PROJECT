# v17.4 Operator Action Receipt Verification

The v17.4 layer verifies v17.3 operator action receipts without persisting state.

- Verification API: `POST /api/v1/operator/workflow-dashboard/<case_id>/actions/verify`
- Existing action API responses also include `action_receipt_verification`.

## Verification checks

- `receipt_sha256` must match the canonical v17.3 receipt payload.
- `action_receipt_id` must match the canonical receipt payload plus receipt hash.
- `recorded_at` must be present and parse as an ISO timestamp.
- Receipt operator must be present and match the authenticated operator.
- Receipt case id must match the requested case.
- Action, label, confirmation state, state-change flag, result status, next action, and blocker count must match the action result.
- Action-plan type and target must match the action result.

A valid verification returns `status: verified` and `next_action: accept_operator_action_receipt`. Tampered or inconsistent receipts return `status: blocked` with explicit blockers.

## Validation

- Focused regression coverage in `tests/test_v17_4_operator_workflow_action_receipt_verification.py`.
- Existing v17.2 action response status codes remain unchanged.
- No database persistence, schema mutation, or migration is introduced.
