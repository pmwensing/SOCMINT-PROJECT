# v26.1 Case Team and Role Assignment

Adds append-only case-team membership and role assignment for visible cases.

Supported roles:

- case owner
- lead analyst
- analyst
- reviewer
- supervisor
- evidence custodian
- observer

Every assignment records the case, member identity, role, assigning actor, reason, effective dates, source case state, source-state SHA-256, assignment ID and SHA-256, and immutable audit-record metadata.

Assigning the same active user and role again creates a new event that explicitly supersedes the prior assignment ID and hash. It does not overwrite or delete the prior assignment event.

Every revocation requires explicit confirmation and a reason. The revocation binds to the original assignment ID and SHA-256, the original audit record, user identity, role, and current source case state. The prior assignment remains unchanged in history.

Role assignment does not grant case access, and revocation does not independently remove underlying case access. Existing authorization and session case scope remain authoritative.

Routes:

- `GET /cases/<case_id>/team`
- `GET /api/v1/cases/<case_id>/team`
- `POST /api/v1/cases/<case_id>/team/assignments`
- `POST /api/v1/cases/<case_id>/team/assignments/<assignment_id>/revoke`

The browser workspace provides assignment controls, active and historical assignments, revocation controls, deterministic event hashes, and a direct return to the collaboration workspace.

v26.1 mutates no case, evidence, review, closure, archive, release, portfolio, or cross-case source event. It performs no connector execution or collection activity and introduces no migration.
