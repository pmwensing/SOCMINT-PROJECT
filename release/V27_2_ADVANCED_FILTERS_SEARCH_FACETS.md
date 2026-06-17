# v27.2 Advanced Filters and Search Facets

Adds Advanced Filters and Search Facets on top of the v27.0 and v27.1 search contracts.

The workspace supports record types, case IDs, actors, statuses, stages, source actions, confidence values, priorities, date windows, include and exclude terms, exact field constraints, result limits, and deterministic sort modes for relevance, newest, oldest, case, type, and actor.

facet counts are calculated from records already restricted by the current case access scope. The response exposes available facets, filtered facets, excluded counts, active-filter summaries, candidate and result counts, filter SHA-256, and result-set SHA-256.

Advanced filtering occurs after case-access enforcement and before final sorting and rendering. Exact field constraints compare normalized field values, date windows use UTC-aware boundaries, and include terms require all specified terms while exclude terms reject any matching term.

relevance is not confidence: scores remain retrieval-order indicators and do not assert factual accuracy or analytical certainty.

Routes:

- `GET /global-search/advanced`
- `GET /api/v1/global-search/advanced`

Both routes require authentication and preserve the existing case access scope.

This slice is read-only. It creates no filter record, saved view, watchlist, report, or search history; mutates no source record or access-control state; performs no connector execution or collection activity; and introduces no migration.
