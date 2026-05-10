# SOCMINT v7.2.1 — Review Decision Persistence + Native Schema Migration

## Added

- Native `review_decisions` table
- Alembic migration `0006_v7_2_1_review_decisions`
- Optional native review columns on `spine_observations` and `findings`
- Native review decision persistence with sidecar fallback
- `make test721`
- `make migrate721`

## Validate

`make test721`

## Migrate

`make migrate721`
