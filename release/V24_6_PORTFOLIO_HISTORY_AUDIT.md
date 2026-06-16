# v24.6 Portfolio History and Audit

Consolidates portfolio snapshots, stage transitions, reviewer assignments, blockers, overdue detections, supervisor escalation controls, and operational metrics checkpoints into one ordered operational history.

The history includes persisted audit events for stage transitions, assignments, and escalation controls, plus deterministic read-only checkpoints for the current portfolio snapshot, stage snapshot, assignment snapshot, blocked/overdue detection, and metrics checkpoint.

Every event exposes:

- event type
- timestamp
- actor
- case ID when applicable
- source action
- source audit-record ID
- source binding
- source-binding SHA-256
- event details
- whether the event is a derived checkpoint

The summary reports total event count, event counts by type, actor counts, represented case count, source-bound event count, the complete current portfolio state, and a SHA-256 of that current state.

Routes:

- `GET /portfolio-operations/history`
- `GET /api/v1/portfolio-operations/history`

The current portfolio state includes portfolio counts, normalized stage counts, assignment workload state, blocked/overdue counts and thresholds, and operational case-volume, completion, and rate metrics.

v24.6 is read-only. It creates no portfolio-history record, mutates no portfolio, stage, assignment, blocker, overdue, escalation, or metrics source data, and introduces no migration.
