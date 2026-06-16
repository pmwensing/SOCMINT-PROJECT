# v26.2 Collaboration Notes and Mentions

Adds append-only collaboration notes and mentions for visible cases.

Supported targets include a case-level note, evidence-specific note, review-specific note, closure and archive note, release record, confirmed cross-case link, and relationship graph.

Every note records:

- author identity
- case ID
- body
- target type and target ID
- mentions
- visibility
- priority
- acknowledgement requirement
- current source case state and SHA-256
- deterministic note and event IDs and hashes
- immutable audit-record metadata

Each mentioned user receives a separate immutable mention event bound to the collaboration note ID and SHA-256. A mention never grants access or changes the case-access scope.

A correction creates a superseding note with a reason, previous note binding, previous note ID and SHA-256, and current source case-state binding. The original note remains unchanged and is projected as superseded.

Acknowledgement and read status are separate append-only events bound to the original note ID and hash. They do not alter the note event.

Routes:

- `GET /cases/<case_id>/collaboration-notes`
- `GET /api/v1/cases/<case_id>/collaboration-notes`
- `POST /api/v1/cases/<case_id>/collaboration-notes`
- `POST /api/v1/cases/<case_id>/collaboration-notes/<note_id>/correct`
- `POST /api/v1/cases/<case_id>/collaboration-notes/<note_id>/acknowledge`
- `POST /api/v1/cases/<case_id>/collaboration-notes/<note_id>/read`

The browser workspace shows current and superseded notes, unread mentions, acknowledgement-required items, immutable history, correction controls, acknowledgement controls, and read controls.

v26.2 mutates no case, evidence, review, closure, archive, release, portfolio, cross-case, or prior collaboration event. It performs no connector execution or collection activity and introduces no migration.
