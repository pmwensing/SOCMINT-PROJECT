# v16.3 Delivery Recovery / Retry Resolution Layer

The v16.3 layer converts v16.2 delivery exceptions into an operator recovery queue.

- `POST /api/v1/case-delivery/<case_id>/recovery`

The recovery queue emits deterministic recovery ids, retry/hold/escalate/remediate decisions, queue states, recommendation strings, and a stable queue id. It returns a blocked result when the underlying exception review is blocked.

## Decision mapping

- Retryable recipient or timeout exceptions become `retry` work items.
- Retryable channel failures become `remediate` work items.
- Delivery rejections and unclassified exceptions become `escalate` work items.
- Non-retryable recipient or timeout exceptions become `hold` work items.

## Validation

- Focused regression coverage in `tests/test_v16_3_case_delivery_recovery.py`.
