# v19.3 Persistent Decision Review Summary / Supervisor Queue

Adds a read-only cross-case queue for durable analyst decisions.

The queue shows:

- counts for unreviewed, needs follow-up, reviewed, and accepted
- total outstanding decisions
- oldest outstanding age
- assigned reviewer visibility
- per-case review totals
- direct links to `/case-intelligence-review/<case_id>`

Filters are available for case id, review state, and assigned reviewer.

Routes:

- `GET /case-intelligence-review/supervisor-queue`
- `GET /api/v1/case-intelligence-review/supervisor-queue`

The view projects existing decision records and latest review annotations. Original records remain unchanged. The existing `audit_logs` table is reused, with no new migration.

Tests:

- `tests/test_v19_3_persistent_decision_supervisor_queue.py`
- `tests/test_v19_3_persistent_decision_supervisor_queue_routes.py`
