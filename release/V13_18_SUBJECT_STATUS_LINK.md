# v13.18 — Subject Status Link

## Purpose

Expose the existing subject handoff/status API from the visible dossier readiness page.

## Changed

- The dossier readiness page now links to:
  - `GET /api/v1/subjects/<subject_id>/handoff-status`

- The readiness summary now includes a subject status checklist card.

## Value

Analysts can move from readiness review to the combined status checklist covering readiness, claim coverage, report availability, and verification rows.

## Note

A dedicated status UI page can be added later; this release makes the existing status contract visible immediately.
