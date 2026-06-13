# v19.0 Persistent Case Review Decisions

The v19.0 layer makes validated v18.5 analyst review decisions durable by reusing the existing `audit_logs` table.

## Persistent behavior

Every successful analyst decision now records:

- case id
- authenticated actor
- decision
- analyst note
- source decision timestamp
- persistence timestamp
- source IP address when available

The existing decision endpoint continues to return the v18 session history and now also returns a `persistent_decision` result.

Persistent case-scoped history is available at:

- `GET /api/v1/case-intelligence-review/<case_id>/decisions/persistent`

Persistent history survives Flask session clearing and is isolated by case id.

## Safety and schema

- Only decisions already validated with `status: recorded` may be persisted.
- Unsupported or blocked decisions are never written.
- The implementation reuses the existing `AuditLog` model and `audit_logs` table.
- No new database table, schema mutation, or migration is introduced.

## Validation

Focused regression coverage is provided in:

- `tests/test_v19_0_persistent_case_review_decisions.py`
