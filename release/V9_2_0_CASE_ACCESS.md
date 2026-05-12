# SOCMINT v9.2.0 — Team/Case Access Control

## Summary

Adds an additive team and case-access policy layer for controlled multi-user workflow testing.

## Added

- Team membership table.
- Case assignment table.
- Team member upsert helper.
- Case assignment helper.
- Case access decision helper.
- Team/case/user access summaries.
- Admin case-access routes.
- Account case-access route.
- Case access check route.
- Alembic migration `0014_case_access`.
- Focused v9.2 case access tests.

## New API surfaces

- `GET /api/v1/account/case-access`
- `POST /api/v1/cases/<case_id>/access/check`
- `GET /api/v1/admin/case-access/<case_id>`
- `POST /api/v1/admin/case-access/<case_id>`
- `GET /api/v1/admin/teams/<team_key>/members`
- `POST /api/v1/admin/teams/<team_key>/members`

## Merge gate

Full CI must pass before merge.

## Next target

v9.3.0 — Production Docker/Tor Release Pipeline.
