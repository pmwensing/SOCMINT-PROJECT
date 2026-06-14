# v21.5 Supervisor Dossier Approval

Adds an explicit supervisor decision surface for approve, return, or hold actions over the current v21.4 quality review.

Approval requires an explicit ready review. Return and hold remain available when the review is not ready so supervisors can send the dossier back for revision or pause release.

Each decision records reviewer identity, decision, note, source review id and hash, source draft and citation mapping identities, timestamp, and a deterministic decision hash as an immutable audit event.

An approved dossier becomes eligible for final export package preparation. Return routes the dossier back to assembly, while hold pauses release.

The draft and quality-review snapshot remain unchanged. Existing audit-log storage is reused, and no migration is introduced.
