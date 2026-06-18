# v28.2 Role, Permission, and Access Policy Management

Adds Role, Permission, and Access Policy Management with controlled role definitions, permission matrices, inherited permissions, explicit deny rules, case-level access grants, least-privilege checks, and immutable access-policy history.

Role definitions contain a unique name, description, direct permissions, inherited role IDs, revision, definition SHA-256, policy-event ID, and policy-event SHA-256. Role revisions create a new role record and preserve the prior role binding and immutable revision history.

The effective-permission resolver combines direct and inherited permissions, detects inheritance cycles, records inherited role IDs, and produces a deterministic resolution SHA-256.

Case-level rules may target a user or active role and may allow or deny selected permissions for one case. explicit deny overrides allow after inherited permissions and direct grants are combined. Rule revocation creates a new audit event and never rewrites the original grant or deny record.

Least-privilege checks identify inheritance cycles, unusually broad non-administrator roles, administration permissions assigned to non-privileged roles, and duplicate active access rules.

All write routes require authentication, administrator required authorization, CSRF validation, explicit confirmation, and an administrative reason. access views do not grant access and the evaluation endpoint only reports projected effective permissions.

Routes:

- `GET /administration/access-policy`
- `GET /api/v1/administration/access-policy`
- `GET /api/v1/administration/access-policy/evaluate`
- `POST /api/v1/administration/access-policy/roles`
- `POST /api/v1/administration/access-policy/roles/<role_id>/revise`
- `POST /api/v1/administration/access-policy/case-rules`
- `POST /api/v1/administration/access-policy/case-rules/<access_rule_id>/revoke`

Preservation boundaries:

- role and access-policy history is append-only
- prior role and rule events remain unchanged
- policy views do not mutate case access
- grant, deny, and revoke actions explicitly record `case_access_scope_changed: true`
- no connector execution
- no credential or secret exposure

This slice introduces no migration. It uses the existing `audit_logs` and `users` tables.
