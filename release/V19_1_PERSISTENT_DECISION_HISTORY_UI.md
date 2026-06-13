# v19.1 Persistent Decision History UI

The v19.1 layer presents durable case-review decisions directly inside the existing v18 Case Intelligence Review Workspace.

## Durable history panel

The new **Persistent Decision History** section is visually separated from the temporary **Case Review Session History** section.

Each durable record displays:

- actor
- decision
- analyst note
- source timestamp from the original v18.5 decision
- persistence timestamp from the existing `audit_logs` record

The section includes an independent durable-history refresh control and a persistent record count.

## Workspace behavior

- Server-rendered workspace responses include `persistent_decision_history`.
- Case-review API payloads include durable history alongside temporary session history.
- Successful decision responses return both updated histories.
- The client refreshes both sections immediately after a decision is recorded.
- Durable records remain visible after the Flask session history is cleared.

Persistent history continues to use:

- `GET /api/v1/case-intelligence-review/<case_id>/decisions/persistent`

## Safety and schema

- Durable history is read-only in this UI.
- Decisions remain case-scoped and actor-attributed.
- No automatic delivery-state mutation is introduced.
- No new table, schema mutation, or migration is introduced.

## Validation

Focused regression coverage is provided in:

- `tests/test_v19_1_persistent_decision_history_ui.py`
