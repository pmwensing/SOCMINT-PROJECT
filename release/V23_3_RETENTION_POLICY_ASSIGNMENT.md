# v23.3 Retention Policy Assignment

Requires the latest supervisor decision to be close before a retention policy can be assigned.

The selected policy is validated against the current retention catalog. The assignment records the assigner identity, timestamp, note, policy details, closure-decision ID and hash, source SHA-256, retention-assignment ID and hash, and the calculated retention disposition.

The retention disposition includes the closure-decision timestamp used as the retention basis, retention years, calculated expiration timestamp when applicable, archive class, indefinite-retention status, legal-hold status, and disposition outcome.

Route:

- `POST /api/v1/case-closure/<case_id>/retention-assignment`

The assignment is immutable and prepares the case for v23.4 archive generation without generating the archive package. It does not mutate the supervisor closure decision, readiness review, or any investigation, dossier, release, or delivery record.

Existing audit-log storage is reused and no migration is introduced.
