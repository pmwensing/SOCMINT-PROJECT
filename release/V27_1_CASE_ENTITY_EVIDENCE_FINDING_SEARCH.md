# v27.1 Case, Entity, Evidence, and Finding Search

Adds a focused Case, Entity, Evidence, and Finding Search layer on top of v27.0 Global Investigation Search.

The service performs field-aware matching across type-specific field catalogs. It records exact and partial matches, phrase matches, token hits, matched fields, per-field relevance contributions, deterministic result ordering, and direct links into the relevant case or evidence workspace.

Results include facets for record type, case ID, actor, and status. Facets are calculated only from records visible inside the current case access scope. Applied filters support record type, case ID, actor, status, and result limit.

Every result includes a compact result preview containing matched fields and selected context fields, plus source binding and SHA-256, actor, timestamp, status, and access scope. Relevance is not confidence: search scores only order retrieval results and do not assert factual accuracy or analytical confidence.

Routes:

- `GET /global-search/core-records`
- `GET /api/v1/global-search/core-records`

Both routes require authentication and preserve the existing case access scope before facets, matching, ranking, previews, or rendering occur.

This slice is read-only. It creates no saved view, search record, watchlist, or report; mutates no case, entity, evidence, finding, audit, or access-control record; performs no connector execution or collection activity; and introduces no migration.
