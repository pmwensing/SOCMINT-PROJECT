# v13.7 — Connector Normalization Review Queue

## Purpose

Give operators a clean review queue for normalized connector output before it becomes dossier material.

## Added

- `src/socmint/normalization_review_queue_v13.py`
  - Builds a read-only queue from observations and account discoveries.
  - Normalizes rows into a shared shape.
  - Supports subject and review-state filters.

- `src/socmint/normalization_review_queue_routes_v13.py`
  - Adds the queue API route.

- Route:
  - `GET /api/v1/review/normalization-queue`

- Tests:
  - `tests/test_normalization_review_queue_v13.py`

## Queue row fields

```text
kind
id
subject_id
run_id
type
value
confidence
source
evidence_ref
review_state
created_at
```

## Value

This is the bridge between connector output and analyst-reviewed dossier claims.
