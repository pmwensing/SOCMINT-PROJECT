# v27.5 Report Builder and Export Packages

Adds Report Builder and Export Packages on top of saved views, watchlists, and advanced search.

Report definitions are append-only immutable report definitions with owner, name, description, visibility, ordered sections, export formats, revision, definition SHA-256, event ID, and event SHA-256. Revisions create a new report ID and preserve the superseded report binding and reason.

Sections may contain text, an active saved view, or an active watchlist. Generated sections retain source bindings and source-binding SHA-256 values. Every saved-view or watchlist section is executed against the requesting user’s current case access scope at generation time.

Supported export formats are JSON, CSV, and HTML. Each generated file records filename, media type, byte size, and SHA-256 in a file manifest. The manifest receives its own SHA-256, and the immutable generation event records a package SHA-256, report revision binding, section count, result count, requested formats, generator identity, and executed access scope.

Routes:

- `GET /global-search/reports`
- `GET /api/v1/global-search/reports`
- `POST /api/v1/global-search/reports`
- `POST /api/v1/global-search/reports/<report_id>/revise`
- `POST /api/v1/global-search/reports/<report_id>/generate`

Write operations require authentication, CSRF validation, and explicit confirmation. Only report owners may revise definitions. Shared reports expose their definition but do not expand source visibility.

reports do not grant access, freeze prior access, expose inaccessible case records, mutate source records, or change case permissions. Report generation and revision remain append-only.

This slice introduces no migration. It stores report and package events in the existing audit log and performs no connector execution, external delivery, or collection activity.
