# v27.0 Global Investigation Search

Introduces a read-only, access-scoped Global Investigation Search across cases, entities, identifiers, infrastructure, evidence, findings, timelines, reviews, collaboration, closure, archive, and cross-case intelligence.

The workspace normalizes heterogeneous portfolio and audit records into normalized results with one common contract: result type, case ID, title, summary, actor, timestamp, matched terms, ranking metadata, source binding and SHA-256, access scope, and direct links into the relevant case, evidence, review, collaboration, closure, archive, or cross-case workspace.

Search supports free-text terms, result-type filtering, deterministic ordering, result limits, per-type counts, visible-case counts, and a deterministic search SHA-256. Exact case matches, phrase matches, and token coverage contribute to ranking metadata; ranking is an operational retrieval indicator and not factual confidence.

Routes:

- `GET /global-search`
- `GET /api/v1/global-search`

Both routes require authentication and preserve the existing case access scope. Results from inaccessible cases are excluded before ranking and rendering.

This slice is read-only. It creates no saved search, watchlist, report, or search database record; mutates no case, evidence, finding, collaboration, closure, archive, portfolio, or cross-case source event; changes no access scope; performs no connector execution or collection activity; and introduces no migration.
