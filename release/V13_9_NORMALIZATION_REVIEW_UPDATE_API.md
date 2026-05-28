# v13.9 — Normalization Review Update API

## Purpose

Expose the v13.8 normalization review update service through an API route.

## Added

- `src/socmint/normalization_review_update_routes_v13.py`
  - Adds an authenticated update route for normalized review queue items.

- Route:
  - `POST /api/v1/review/normalization-update`

- Tests:
  - `tests/test_normalization_review_update_routes_v13.py`

## Supported review states

```text
confirmed
rejected
suppressed
unreviewed
```

## Payload shape

```json
{
  "kind": "observation",
  "id": 123,
  "review_state": "confirmed",
  "actor": "analyst",
  "note": "Verified from evidence."
}
```

## Value

The normalization review queue is now actionable through API calls instead of being read-only.
