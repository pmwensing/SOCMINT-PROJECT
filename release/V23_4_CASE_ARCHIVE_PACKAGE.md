# v23.4 Case Archive Package

Requires the latest valid retention assignment before an archive package can be generated.

The deterministic package assembles closure, retention, dossier, release, delivery, and audit references. It includes the v23.1 readiness review, v23.2 supervisor closure decision, v23.3 retention assignment and disposition, latest v21.6 final dossier export, v22.6 release and delivery closure summary and timeline, and ordered audit-record references for the case.

The package calculates component hashes for closure, retention, dossier, release and delivery, and audit references, then calculates a deterministic archive-package ID and SHA-256 over the complete package content and integrity metadata.

Route:

- `POST /api/v1/case-closure/<case_id>/archive-package`

The generated package records the generator identity and timestamp as a separate immutable audit event without changing any source event. Closure, retention, dossier, release, delivery, receipt, acknowledgement, recovery, and audit records remain unchanged.

Existing audit-log storage is reused and no migration is introduced.
