# v22.6 Release and Delivery History / Case Closure Summary

Provides one consolidated timeline of authorization, preview, dispatch, delivery receipt, recipient acknowledgement, failed-delivery review, recall, and reissue events.

The history view calculates the current release outcome, unresolved actions, closure readiness, and a closure-ready summary containing the key authorization, distribution, receipt, acknowledgement, recall, and reissue identifiers.

Routes:

- `GET /dossier-release/<case_id>/history`
- `GET /api/v1/dossier-release/<case_id>/history`

This slice is read-oriented and derives its result from the existing immutable audit events without creating another narrow integrity wrapper. It does not mutate source records and introduces no migration.
