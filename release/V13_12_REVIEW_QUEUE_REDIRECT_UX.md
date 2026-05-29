# v13.12 — Review Queue Redirect UX

## Purpose

Make normalization review form actions feel like normal UI actions.

## Changed

- JSON callers still receive JSON from `POST /api/v1/review/normalization-update`.
- HTML form callers are redirected back to the review queue.
- The redirect preserves the browser referer when available.

## Value

Analysts can click a review action and return to the queue instead of landing on raw JSON.
