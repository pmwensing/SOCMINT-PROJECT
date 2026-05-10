# SOCMINT v7.2 — Report UX + Enrichment Review Console

## Added

- /reports/review
- /api/v1/reports/review/summary
- /api/v1/reports/review/items
- /api/v1/reports/review/items/{item_id}
- /api/v1/reports/runs
- Enrichment review queue
- Approve / reject / uncertain analyst decisions
- Confidence and source quality badges
- Full-report run history / manifest listing
- Sidecar review decisions when the underlying DB table has no review-status columns

## Validate

make test72
