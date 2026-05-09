
# SOCMINT v7.3 — Report Export Center + Review-Gated Dossier Builder

## Added

- `/reports/export-center`
- `/api/v1/reports/export-center`
- `/api/v1/reports/export-center/review-gated`
- `/reports/export-center/review-gated/run`
- Review-gated dossier export manifests
- Markdown export summaries
- Export history panel
- Gate modes:
  - `approved_only`
  - `approved_and_uncertain`
  - `exclude_rejected`
  - `all_reviewed`

## Purpose

v7.3 connects analyst review decisions to dossier/export behavior. The builder
records which review gate was applied, what was included, what was excluded, and
where the resulting manifest/summary were written.

## Validate

`make test73`
