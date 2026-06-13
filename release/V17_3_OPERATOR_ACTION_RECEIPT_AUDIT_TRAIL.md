# v17.3 Operator Action Receipt / Audit Trail

The v17.3 layer adds an immutable-style action receipt to every unified operator workflow action response.

- Action API: `POST /api/v1/operator/workflow-dashboard/<case_id>/actions`

Each response now includes `action_receipt` with:

- `action_receipt_id`
- `receipt_sha256`
- selected action and label
- operator identity
- confirmation state
- whether the action represents a state change
- action-plan type and target
- result status and next action
- blocker count
- UTC `recorded_at` timestamp

The receipt id is derived from the canonical receipt payload and receipt hash. A fixed timestamp produces a deterministic receipt id for the same action result.

Receipts are returned for launched, confirmation-required, and blocked actions. They document the operator decision path without automatically executing or persisting the underlying delivery state.

## Validation

- Focused regression coverage in `tests/test_v17_3_operator_workflow_action_receipt.py`.
- Existing v17.2 action endpoint status codes remain unchanged.
- No database schema mutation or migration is introduced.
