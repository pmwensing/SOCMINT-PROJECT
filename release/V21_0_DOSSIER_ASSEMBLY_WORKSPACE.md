# v21.0 Dossier Assembly Workspace

Adds a case-level dossier assembly workspace that loads the v20 dossier promotion package, reconstructs promoted packages when necessary, and preserves the original finding and package records unchanged.

The workspace groups findings into dossier sections, lets an operator reorder sections, move findings, and write section narratives, and records each saved arrangement as a separate immutable audit event.

Gap analysis exposes:

- missing narrative
- missing evidence
- missing citation
- missing source context

The workspace connects to the existing dossier readiness API, claim/evidence ledger, export manifest draft, ultimate dossier, case findings workspace, and case delivery workspace instead of duplicating those products. Subject-level links are exposed when a numeric `subject_id` is supplied.

Routes:

- `GET /dossier-assembly/<case_id>`
- `GET /api/v1/dossier-assembly/<case_id>`
- `POST /api/v1/dossier-assembly/<case_id>/arrangement`

The existing `audit_logs` table is reused. Saving an arrangement does not mutate source records and introduces no new migration.
