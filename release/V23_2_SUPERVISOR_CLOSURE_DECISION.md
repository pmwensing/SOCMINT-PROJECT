# v23.2 Supervisor Closure Decision

Adds an immutable supervisor closure decision bound to the latest readiness review.

The latest readiness review must be `ready` and explicitly marked ready for a supervisor closure decision. The supervisor may record `close`, `hold`, or `return` with explicit confirmation and an optional note.

The decision stores supervisor identity, timestamp, decision, note, the readiness-review ID and hash, readiness-review record ID, reviewer identity and timestamp, source closure summary, source SHA-256, closure-decision ID, and closure-decision SHA-256.

Route:

- `POST /api/v1/case-closure/<case_id>/closure-decision`

A `close` decision prepares the case for retention assignment. A `hold` decision keeps closure pending. A `return` decision sends the case back for further closure review.

The decision is recorded without assigning retention or generating the archive package. It does not mutate the readiness review or any investigation, dossier, release, delivery, receipt, acknowledgement, recall, or reissue record.

Existing audit-log storage is reused and no migration is introduced.
