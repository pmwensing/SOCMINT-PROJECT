# v13.14 — Review Queue Filters

## Purpose

Make the normalization review queue easier to narrow for analysts and API callers.

## Added

- API support for filtering by item kind.
- API support for filtering by minimum confidence.
- Helper functions for confidence parsing and queue filtering.

## Existing filters preserved

- Subject ID
- Review state
- Limit

## Route

```text
GET /api/v1/review/normalization-queue
```

## Query parameters

```text
subject_id
review_state
kind
min_confidence
limit
```

## Note

The backend/API filter support is included first. A visible filter form can be added as a follow-up UI patch.
