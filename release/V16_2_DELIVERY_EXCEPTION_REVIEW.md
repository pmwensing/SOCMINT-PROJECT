# v16.2 Delivery Exception Review

The v16.2 layer classifies failed delivery attempts from the v16.1 Delivery
Attempt Ledger into operator-actionable exception categories.

- `POST /api/v1/case-delivery/<case_id>/exception-review`

The review emits stable exception ids, retryable exception counts, escalation
state, and recommended operator actions. It returns a blocked result when the
underlying attempt ledger is blocked.

## Validation

- Focused regression coverage in `tests/test_v15_case_delivery_workspace.py`.
