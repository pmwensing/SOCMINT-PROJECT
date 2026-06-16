# v26.0 Collaboration Workspace

Introduces a read-only collaboration workspace that aggregates participating cases, the assigned role on each case, active collaborators, pending collaboration requests, pending handoffs, unresolved review requests, unread mentions or updates, blocked collaboration items, and unresolved collaboration actions.

Participation is inferred from existing reviewer assignments, case decision activity, current team-role events, and collaboration events visible within the current access scope.

Each participating case exposes direct links into:

- case and review workspaces
- evidence and dossier assembly
- closure workspace
- archive and closure history
- release workspace
- cross-case intelligence workspace
- cross-case relationship graph

The workspace understands the append-only v26 collaboration action family for future case-team assignments, requests, handoffs, notes, mentions, and update-read events. Until those write slices are introduced, it safely aggregates existing assignment and review activity.

A mention never grants access. Cases, collaboration events, requests, handoffs, and updates are filtered against the current session case scope before aggregation.

Core output:

- `participating_cases`
- `active_collaborators`
- `pending_requests`
- `pending_handoffs`
- `unread_updates`
- `unresolved_review_requests`
- `blocked_collaboration_items`
- `unresolved_collaboration_actions`
- `access_scope`

Routes:

- `GET /collaboration`
- `GET /api/v1/collaboration`

v26.0 is read-only. It creates no collaboration record, mutates no case, assignment, review, evidence, closure, archive, release, or cross-case event, performs no connector execution or collection activity, and introduces no migration.
