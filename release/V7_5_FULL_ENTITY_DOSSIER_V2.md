# SOCMINT v7.5 — Full Entity Profile Dossier Builder v2

## Added

- Full Entity Profile Dossier v2 service
- Subject-scoped dossier payload
- Markdown, HTML, JSON, and ZIP dossier export
- Dossier UI page
- Dossier sections:
  - Identity summary
  - Identity graph
  - Timeline / observations
  - Findings
  - Enrichment summary
  - Contradictions
  - Analyst review decisions
  - Linked evidence
  - Chain-of-custody / hash status
  - Prior exports
- `make test75`

## Routes

- `GET /api/v1/spine/subjects/{subject_id}/dossier-v2`
- `POST /api/v1/spine/subjects/{subject_id}/dossier-v2/export`
- `GET /spine/subjects/{subject_id}/dossier`
- `POST /spine/subjects/{subject_id}/dossier-v2/export/run`
- `GET /spine/subjects/{subject_id}/dossier-v2/export/{name}/download`

## Validate

`make test75`
