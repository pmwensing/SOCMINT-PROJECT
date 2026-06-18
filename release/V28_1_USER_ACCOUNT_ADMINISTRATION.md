# v28.1 User and Account Administration

Adds controlled User and Account Administration over the existing user table and audit log.

The slice supports account provisioning, activation, suspension, role updates, administrator-state updates, user listings, and immutable account audit history. Provisioned accounts begin inactive and require separate secure credential onboarding before activation.

All write routes require authentication, administrator required authorization, CSRF validation, explicit confirmation, and an administrative reason. Account events bind actor, target username, reason, before state, after state, event ID, event SHA-256, audit-record ID, timestamp, and source IP address.

The service prevents suspension or demotion of the last active administrator. It blocks duplicate usernames, invalid roles, unchanged updates, missing reasons, and unconfirmed writes.

Credentials are never returned, credential hashes are never returned, and neither credentials nor hashes are written into account audit events. The case access scope is unchanged by account provisioning, activation, suspension, or role updates.

Routes:

- `GET /administration/users`
- `GET /api/v1/administration/users`
- `POST /api/v1/administration/users`
- `POST /api/v1/administration/users/<username>/activate`
- `POST /api/v1/administration/users/<username>/suspend`
- `POST /api/v1/administration/users/<username>/update`

Preservation boundaries:

- prior audit events remain unchanged
- prior user snapshots embedded in events remain unchanged
- `case_access_scope_changed: false`
- no connector execution
- no session termination
- no permission or case grant mutation

This slice introduces no migration. It uses the existing `users` and `audit_logs` tables.
