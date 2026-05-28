# v13.8 — Normalization Review Updates

## Purpose

Add the backend service for marking normalized review queue rows after analyst review.

## Added

- `src/socmint/normalization_review_decisions_v13.py`
  - Supports observation review state updates.
  - Supports account discovery review state updates.
  - Uses the existing account discovery review update helper.

## Supported states

```text
confirmed
rejected
suppressed
unreviewed
```

## Next slice

The API route can be added separately after the backend service is merged and verified.
