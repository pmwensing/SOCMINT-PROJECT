# v28.3 Team and Organizational Structure

Adds controlled Team and Organizational Structure management for teams, supervisors, memberships, organizational scopes, ownership boundaries, workload groups, and immutable team history.

Team definitions are append-only and include name, description, revision, definition SHA-256, team-event ID, and team-event SHA-256. Revisions create a new team ID bound to the prior immutable team version.

Membership, supervisor, organizational-scope, ownership-boundary, and workload-group changes create separate immutable audit events. Team projections preserve the ordered history while showing current active structure.

The workspace identifies teams without supervisors, unknown or inactive supervisors, unknown or inactive members, missing organizational scopes, missing workload groups, and users assigned to unusually many teams.

All write routes require authentication, administrator required authorization, CSRF validation, explicit confirmation, and an administrative reason.

team membership does not grant case access. Organizational scopes and ownership boundaries are descriptive governance metadata. Case permissions remain controlled independently by v28.2 access-policy rules.

Routes:

- `GET /administration/teams`
- `GET /api/v1/administration/teams`
- `POST /api/v1/administration/teams`
- `POST /api/v1/administration/teams/<team_id>/revise`
- `POST /api/v1/administration/teams/<team_id>/members/add`
- `POST /api/v1/administration/teams/<team_id>/members/remove`
- `POST /api/v1/administration/teams/<team_id>/supervisor`
- `POST /api/v1/administration/teams/<team_id>/scope`
- `POST /api/v1/administration/teams/<team_id>/workload-group`

Preservation boundaries:

- immutable team history
- prior team events remain unchanged
- team membership grants no permissions
- ownership boundaries do not alter case access
- `case_access_scope_changed: false`
- no connector execution
- no credential or secret exposure

This slice introduces no migration. It uses the existing `audit_logs` and `users` tables.
