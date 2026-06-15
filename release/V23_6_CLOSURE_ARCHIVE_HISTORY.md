# v23.6 Closure and Archive History

Adds one ordered case timeline for the complete closure and archive lifecycle.

The history consolidates closure-readiness reviews, supervisor closure decisions, retention-policy assignments, archive-package generations, reopen requests, and reopen authorization or denial events.

The read-only summary derives the current closure state, current archive state, retention disposition, reopen status, event count, latest event by lifecycle type, and unresolved actions.

Routes:

- `GET /case-closure/<case_id>/history`
- `GET /api/v1/case-closure/<case_id>/history`

Possible unresolved actions include missing readiness review, missing supervisor closure decision, missing retention assignment, missing archive generation, pending reopen authorization, closure hold resolution, and closure return resolution.

The history surface is read-only. It creates no new lifecycle or integrity record and does not mutate any readiness, closure, retention, archive, dossier, release, delivery, or reopen source event.

No migration is introduced.
