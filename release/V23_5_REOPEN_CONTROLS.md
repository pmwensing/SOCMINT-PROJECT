# v23.5 Reopen Controls

Requires an existing archive package and a closed supervisor decision.

Adds a separate reopen request with requester identity, reason, note, timestamp, archive package ID and hash, closure decision ID and hash, source hash, request ID, and request hash.

Adds a separate supervisor approval or denial event bound to the reopen request, archive package, and latest closure decision.

Routes:

- `POST /api/v1/case-closure/<case_id>/reopen-request`
- `POST /api/v1/case-closure/<case_id>/reopen-authorization`

The request does not reopen the case. A denial keeps the case closed. The closed case and archive records unchanged until an approved decision is recorded.

The original archive package, closure decision, retention assignment, and reopen request are not rewritten. Existing audit-log storage is reused and no migration is introduced.
