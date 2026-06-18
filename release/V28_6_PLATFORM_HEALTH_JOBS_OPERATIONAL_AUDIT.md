# v28.6 Platform Health, Jobs, and Operational Audit

Adds Platform Health, Jobs, and Operational Audit as the operational control plane for database readiness, storage readiness, background-job health, failed and stalled work, connector-run continuity, configuration state, audit-log continuity, operational incidents, and immutable operational history.

The workspace summarizes database readiness, storage path existence and writability, configured environment-key presence without exposing values, scan-job status counts, failed jobs, stalled queued or running work, connector-run counts and errors, audit-record ID continuity, open incidents, and prioritized operational findings.

Stalled work is detected from queued, pending, running, or in-progress jobs whose latest available timestamp is older than the configured threshold. The default threshold is 24 hours and the API accepts a bounded administrative query value.

Audit-log continuity reports record count, first and last audit IDs, detected ID gaps, action counts, actor counts, and the latest audit timestamp. It does not alter or repair the audit log.

Operational incident events support open, acknowledge, and resolve states. Each event binds the actor, reason, component, severity, source binding, event ID, event SHA-256, timestamp, and source IP. Incident history is append-only.

All incident writes require authentication, administrator required authorization, CSRF validation, explicit confirmation, and an administrative reason.

Operational boundaries:

- no job execution
- no service restart
- no configuration mutation
- no audit-record mutation
- no connector execution
- no secret-value exposure
- no case-access mutation

Routes:

- `GET /administration/operations`
- `GET /api/v1/administration/operations`
- `POST /api/v1/administration/operations/incidents`
- `POST /api/v1/administration/operations/incidents/<incident_id>/acknowledge`
- `POST /api/v1/administration/operations/incidents/<incident_id>/resolve`

This slice introduces no migration. It reads the existing `scan_jobs`, `connector_runs`, and `audit_logs` tables and stores incident events in the existing audit log.
