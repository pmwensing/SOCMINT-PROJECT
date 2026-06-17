# v27.4 Watchlists and Scheduled Search Monitoring

Adds Watchlists and Scheduled Search Monitoring on top of active saved views.

Each watchlist binds to one active saved view and records owner, name, description, monitoring cadence, notification rule, saved-view ID, saved-view event ID, saved-view event SHA-256, definition SHA-256, watchlist event ID, and watchlist event SHA-256. Supported cadence values are manual, hourly, daily, and weekly.

Creation, pause, resume, and immutable monitoring runs are append-only audit events. Pause and resume require explicit confirmation and a reason; prior watchlist events are never rewritten.

Every run executes the bound saved view using the requesting user’s current case access scope. The monitor records ordered result IDs, result count, result-set SHA-256, previous result-set SHA-256, added and removed results, added and removed counts, change state, executed access scope, and run sequence.

Supported notification rules are any change, new results, removed results, and result-count change. A triggered notification is recorded in the monitoring event; this slice does not send external messages.

Routes:

- `GET /global-search/watchlists`
- `GET /api/v1/global-search/watchlists`
- `POST /api/v1/global-search/watchlists`
- `POST /api/v1/global-search/watchlists/<watchlist_id>/pause`
- `POST /api/v1/global-search/watchlists/<watchlist_id>/resume`
- `POST /api/v1/global-search/watchlists/<watchlist_id>/run`

All writes require authentication, CSRF validation, and explicit confirmation where applicable. watchlists do not grant access, freeze saved-view access, expose inaccessible cases, mutate saved views, or change case permissions.

This slice is append-only and introduces no migration. It performs no connector execution, external notification delivery, or collection activity.
