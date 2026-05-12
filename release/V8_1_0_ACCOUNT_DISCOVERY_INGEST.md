# SOCMINT v8.1.0 - Account Discovery Ingest

This milestone adds a reviewable account-discovery layer for new account and
profile leads found by social scan style connectors.

## What Changed

- Added the `account_discoveries` table.
- Added ingestion from `account_presence` and `profile_url` spine observations.
- Added optional profile URL capture using the evidence capture pipeline.
- Added analyst review states for discovered accounts.
- Added promotion of confirmed discoveries into new seeds.
- Added UI and API routes for ingest, queue review, and promotion.

## Routes

```text
GET /spine/subjects/<subject_id>/account-discovery
POST /spine/subjects/<subject_id>/account-discovery/ingest
POST /spine/account-discovery/<discovery_id>/review
GET /api/v1/spine/subjects/<subject_id>/account-discovery
POST /api/v1/spine/subjects/<subject_id>/account-discovery/ingest
POST /api/v1/spine/account-discovery/<discovery_id>/review
```

## Validation

```bash
ruff check src tests scripts
pytest -q tests/test_account_discovery_ingest.py
```
