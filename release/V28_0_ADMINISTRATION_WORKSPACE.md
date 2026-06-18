# v28.0 Administration Workspace

Adds an Administration Workspace as a read-only aggregation layer over existing account, role, team, session, access, policy, connector, job, health, and governance records.

Core output:

- `user_summary`
- `role_summary`
- `team_summary`
- `active_sessions`
- `access_grant_summary`
- `policy_summary`
- `connector_summary`
- `system_health`
- `pending_admin_actions`
- `recent_governance_events`
- `access_scope`

The workspace summarizes active and inactive users, administrator count, role distribution, recent team and access events, inferred recent authenticated sessions, policy activity, connector run health, scan-job state, database readiness, pending governance actions, and recent administration-related audit events.

Connector output exposes names, run counts, statuses, timestamps, and error counts only. It returns no secret values, passwords, tokens, credential material, raw connector commands, or raw results.

Routes:

- `GET /administration`
- `GET /api/v1/administration`

Both routes require authentication. This initial slice is read-only and allows no user, role, team, access, policy, connector, session, job, or case-access mutation.

Preservation boundaries:

- `read_only: true`
- `source_records_mutated: false`
- `user_records_mutated: false`
- `permission_records_mutated: false`
- `connector_records_mutated: false`
- `case_access_scope_changed: false`
- administrative access scope reports `secrets_visible: false`
- administrative access scope reports `mutations_allowed: false`

This slice introduces no migration. It performs no connector execution, credential rotation, session termination, permission grant, policy update, scheduling, external delivery, or collection activity.
