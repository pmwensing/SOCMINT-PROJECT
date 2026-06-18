# v27.6 Search, Watchlist, and Reporting History and Audit

Adds a unified, read-only Search, Watchlist, and Reporting History and Audit workspace across the complete v27 operational lifecycle.

The workspace consolidates an ordered operational history covering the saved-view lifecycle, watchlist monitoring, immutable monitoring runs, report definitions and packages, report revisions, and report-package generation. Events retain actors, timestamps, event families, source actions, identifiers, hashes, source bindings, access scope, event counts, change state, notification state, reasons, and direct workspace links.

Each normalized history event receives a deterministic history-event ID, source-bindings SHA-256, and raw-event SHA-256. Events remain ordered by recorded time and audit-record ID. Filters support event family, actor, and result limit.

The response includes family counts, action counts, actor counts, history SHA-256, and current projected state for saved views, active saved views, watchlists, active watchlists, report definitions, active reports, and generated report packages.

Routes:

- `GET /global-search/history`
- `GET /api/v1/global-search/history`

Both routes require authentication. This slice is read-only: underlying events remain unchanged, source records remain unchanged, prior hashes and bindings are preserved, and case access scope is not modified.

This slice introduces no migration. It performs no connector execution, external delivery, scheduling, notification sending, or collection activity.
