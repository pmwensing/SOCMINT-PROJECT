# v29.4 Evidence-Safe Ingestion and Provenance

Adds append-only artifact registration, content and acquisition hashes, collection-attempt bindings, duplicate detection, chain-of-custody checks, quarantine and rejection states, observation derivation, and immutable provenance history.

The registration layer stores metadata and deterministic hashes only; no raw artifact content is stored in audit events. The existing results, media, findings, connector outputs, and legacy jobs remain unchanged.

Artifacts bind to a current v29.1 collection-job attempt, including the job event hash, attempt number, case, entity, source, and authorization reference. Registration requires a valid SHA-256 content hash, acquisition timestamp, source reference, content type, byte size, acquisition method, explicit confirmation, and reason.

The acquisition hash is computed from the acquisition envelope. Duplicate content hashes are detected before acceptance and new duplicates enter quarantine with a binding to the earlier artifact.

Artifact states are registered, accepted, quarantined, and rejected. Only accepted artifacts may produce derived observations. State changes and observation derivations are append-only and bind back to immutable artifact hashes.

All routes require authentication and active-administrator authorization. Writes also require CSRF validation, explicit confirmation, and an administrative reason.

Preservation boundaries:

- no raw artifact content
- no existing evidence mutation
- no connector-output mutation
- no connector execution
- no case-access change
- no secret exposure
- no migration

Routes:

- `GET /collection-operations/evidence`
- `GET /api/v1/collection-operations/evidence`
- `POST /api/v1/collection-operations/evidence`
- `POST /api/v1/collection-operations/evidence/<artifact_id>/state`
- `POST /api/v1/collection-operations/evidence/<artifact_id>/observations`
