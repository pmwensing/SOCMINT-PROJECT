# v29.0 Collection Operations Workspace

Adds the first runtime slice of v29 as a read-only aggregation over existing collection inventory, connector runs, collection jobs, evidence outputs, observation outputs, provenance completeness, retry eligibility, target bindings, operator findings, and dossier-value contribution.

The workspace combines existing `scan_jobs`, `connector_runs`, `findings`, `results`, and `media` records with optional summaries from the intelligence-spine tables when those tables exist.

Collection-job reporting includes status, requesting actor, target binding, selected tools, timestamps, failure state, stale-work detection, and retry eligibility projection. Retry eligibility is advisory only and does not execute a retry.

Connector-run reporting includes connector, target, status, raw-output presence and size, linked finding counts, finding types, provenance completeness, dossier-value contribution, and human-review requirements. Raw commands and raw result bodies are not exposed.

The workspace reports duplicate connector-run groups, failed jobs, stale jobs, missing requesting actors, incomplete connector-run provenance, media checksum completeness, optional spine observation counts, and optional dossier assertion counts.

All browser and API routes require authentication and administrator required authorization.

Preservation boundaries:

- read-only aggregation
- no connector execution
- no job mutation
- no retry execution
- no credential rotation
- no secret exposure
- no case-access change
- no evidence rewrite
- no source-record mutation

Routes:

- `GET /collection-operations`
- `GET /api/v1/collection-operations`

The browser and API accept an optional `stale_after_hours` query value. The default is 24 hours.

This slice introduces no migration.
