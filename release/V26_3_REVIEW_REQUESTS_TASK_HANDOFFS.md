# v26.3 Review Requests and Task Handoffs

Adds append-only review request and task handoff workflows for visible cases.

Supported review request types include evidence review, correlation review, closure review, archive verification, supervisor decision, and general task review. Supported task handoff types include case ownership, evidence custody, review task, and unresolved task.

Each review request records requester and recipient identity, request type, reason, priority, due date, source bindings and SHA-256, current source case state and SHA-256, deterministic request/event IDs and hashes, and immutable audit metadata.

Each task handoff records handoff-from and handoff-to identity, handoff type, reason, priority, due date, source bindings and SHA-256, current source case state and SHA-256, deterministic handoff/event IDs and hashes, and immutable audit metadata.

Both workflows support acknowledged, accepted, declined, completed, and cancelled transitions. Every transition is a new immutable event bound to the current request or handoff ID, hash, source audit record, and previous workflow state. Terminal items cannot be transitioned again.

acknowledgement does not equal completion. Acceptance does not erase the original request or handoff. All prior events remain append-only and unchanged.

Routes:

- `GET /cases/<case_id>/collaboration-requests`
- `GET /api/v1/cases/<case_id>/collaboration-requests`
- `POST /api/v1/cases/<case_id>/collaboration-requests`
- `POST /api/v1/cases/<case_id>/collaboration-handoffs`
- `POST /api/v1/cases/<case_id>/collaboration-requests/<item_id>/<decision>`
- `POST /api/v1/cases/<case_id>/collaboration-handoffs/<item_id>/<decision>`

The workspace displays pending requests, pending handoffs, full immutable history, creation controls, priorities, due dates, and direct navigation back to collaboration notes and the central collaboration workspace.

v26.3 mutates no case, evidence, review, closure, archive, release, portfolio, cross-case, team-role, note, or prior collaboration event. It performs no connector execution or collection activity and introduces no migration.
