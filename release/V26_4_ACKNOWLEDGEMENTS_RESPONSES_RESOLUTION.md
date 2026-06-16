# v26.4 Acknowledgements, Responses, and Resolution

Adds an append-only response layer for collaboration notes, review requests, and task handoffs.

Supported response types:

- acknowledgement
- acceptance
- decline
- response note
- completion
- escalation
- resolution

Every response binds to the original item ID and SHA-256, the original source audit record, the previous item state, the responding user, reason, current case state, source-case-state SHA-256, and any previous response event.

Acknowledgement does not equal completion. Acceptance does not resolve an item by itself. Escalation remains unresolved until a later resolution, decline, or completion event is recorded.

Resolution events may carry a resolution code. Non-terminal responses may carry an unresolved reason. Terminal responses prevent further response events for the same target.

The response layer never rewrites the source note, request, handoff, or any earlier response. Every action is a new immutable audit event with deterministic response and event IDs and hashes.

Routes:

- `GET /cases/<case_id>/collaboration-responses`
- `GET /api/v1/cases/<case_id>/collaboration-responses`
- `POST /api/v1/cases/<case_id>/collaboration-responses`

The browser workspace exposes the current response state, unresolved response items, immutable history, target type and ID, response type, reason, unresolved reason, resolution code, and explicit confirmation.

v26.4 mutates no case, evidence, review, closure, archive, release, portfolio, cross-case, team-role, note, request, handoff, or prior response event. It performs no connector execution or collection activity and introduces no migration.
