# v21.6 Package Generation

Builds a deterministic dossier package from the latest approved review.

The package includes dossier content, citation catalog, source manifest, supervisor approval record, export metadata, and integrity hashes.

Generation is blocked when approval is missing or stale, when the current dossier is not ready, or when the latest supervisor decision is returned or held.

The generated package is recorded as a separate immutable audit event. Source records remain unchanged, and no migration is introduced.
