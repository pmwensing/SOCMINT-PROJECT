# SOCMINT v7.2.2 — Review Decision Audit Trail + Bulk Analyst Actions

## Added

- Native `review_decision_audit` table
- Alembic migration `0007_v7_2_2_review_decision_audit`
- Audit trail for review decisions
- Bulk approve/reject/uncertain API
- Batch IDs for analyst review actions
- Reviewer attribution field
- Sidecar fallback for audit entries when native table is unavailable
- `make test722`
- `make migrate722`

## API

Bulk review action:

`POST /api/v1/reports/review/bulk`

Audit trail:

`GET /api/v1/reports/review/audit`

## Validate

`make test722`

## Migrate

`make migrate722`
