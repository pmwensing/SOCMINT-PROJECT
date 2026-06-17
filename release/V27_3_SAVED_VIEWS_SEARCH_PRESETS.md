# v27.3 Saved Views and Search Presets

Adds Saved Views and Search Presets as persistent named query and filter definitions over the v27 search stack.

Each saved view records owner identity, name, description, visibility, query, advanced filter definition, definition SHA-256, revision number, event ID, event SHA-256, and source audit record. Creation, revision, and deactivation are append-only events. Revisions create new immutable revisions and bind to the superseded saved-view ID, event ID, event SHA-256, definition SHA-256, and revision.

Active names use duplicate-safe naming per owner with case-insensitive comparison. Visibility supports private and shared visibility: private views are owner-only, while shared views are visible to other authenticated users. Only owners can revise or deactivate a view.

Running a saved view always re-executes its query and filters using the current case access scope of the requesting user. saved views do not grant access, freeze prior access, expose inaccessible results, or modify case permissions.

Routes:

- `GET /global-search/saved-views`
- `GET /api/v1/global-search/saved-views`
- `POST /api/v1/global-search/saved-views`
- `POST /api/v1/global-search/saved-views/<view_id>/revise`
- `POST /api/v1/global-search/saved-views/<view_id>/deactivate`
- `GET /api/v1/global-search/saved-views/<view_id>/run`

All write operations require explicit confirmation. Revision and deactivation require an active owner-controlled view and a reason. Search source records and prior saved-view events remain unchanged.

This slice introduces no schema migration. It stores append-only saved-view events in the existing audit log, performs no connector execution or collection activity, and changes no case access scope.
