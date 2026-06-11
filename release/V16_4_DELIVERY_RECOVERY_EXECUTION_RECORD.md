# v16.4 Delivery Recovery Execution Record

The v16.4 layer records what the operator actually did with each item in the v16.3 recovery queue.

- `POST /api/v1/case-delivery/<case_id>/recovery-execution`

The execution record emits deterministic execution ids, an execution record id, per-item execution states, and a recovery result summary.

## Supported execution states

- `retried`
- `held`
- `escalated`
- `remediated`
- `completed`
- `failed`

## Behavior

- Recovery queue items default to execution states that match their v16.3 decision.
- Explicit execution payloads can override each item by `recovery_id`.
- Any failed execution makes the execution record state `failed`.
- A blocked recovery queue returns a blocked execution record.

## Validation

- Focused regression coverage in `tests/test_v16_4_case_delivery_recovery_execution.py`.
