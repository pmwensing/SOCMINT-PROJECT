# v28.5 Connector and Integration Administration

Adds controlled Connector and Integration Administration for connector registration, authorization scopes, authentication readiness, enable and disable state, rate-limit policy, health summaries, findings, and immutable connector history.

Connector definitions record a name, type, description, authorization scopes, rate-limit policy, revision, definition SHA-256, connector event ID, and connector event SHA-256. Revisions create a new connector definition bound to the prior immutable version.

Authentication readiness is tracked only as non-sensitive metadata: `not_configured`, `configured`, `expiring`, `expired`, `invalid`, or `rotation_required`, plus an optional expiry timestamp. sensitive values are excluded from events, API responses, and browser output.

The workspace combines configured connector definitions with existing connector-run summaries, including run counts, latest status, latest run time, and error counts. It identifies enabled connectors that are not authentication-ready, expired authentication state, missing authorization scopes, missing rate-limit policy, and recent run errors.

All write routes require authentication, administrator required authorization, CSRF validation, explicit confirmation, and an administrative reason.

This layer performs no connector execution. Registration, revision, state changes, and authentication-readiness updates are governance records only.

Routes:

- `GET /administration/connectors`
- `GET /api/v1/administration/connectors`
- `POST /api/v1/administration/connectors`
- `POST /api/v1/administration/connectors/<connector_id>/revise`
- `POST /api/v1/administration/connectors/<connector_id>/enable`
- `POST /api/v1/administration/connectors/<connector_id>/disable`
- `POST /api/v1/administration/connectors/<connector_id>/auth-readiness`

Preservation boundaries:

- immutable connector history
- prior connector definitions remain unchanged
- sensitive values are excluded
- no connector execution
- no case-access mutation
- no external delivery

This slice introduces no migration. It uses the existing `audit_logs` and `connector_runs` tables.
