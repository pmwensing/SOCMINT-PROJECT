# v25.5 Cross-Case Intelligence History and Audit

Consolidates candidate discovery, analyst decisions, confirmed-link registrations, graph projections, and impact analyses into one ordered history.

The history combines immutable audit events for analyst decisions and confirmed-link registrations with deterministic read-only checkpoints for candidate discovery, relationship-graph projection, and each visible confirmed-link impact analysis.

Every history event exposes:

- event type and timestamp
- actor
- correlation ID and confirmed-link ID when applicable
- represented case IDs
- source action and source audit-record ID
- complete source bindings and SHA-256
- access scope
- event details
- whether the event is a derived checkpoint

The summary reports event counts by type, actor counts, represented correlation, confirmed-link and case counts, source-bound event count, and the current cross-case intelligence state.

The current cross-case intelligence state includes candidate-discovery counts, review disposition counts, accepted decisions pending registration, confirmed-link IDs, graph counts and graph SHA-256, impact-analysis IDs and hashes, and the active access scope. The complete state receives a deterministic SHA-256.

Routes:

- `GET /cross-case-intelligence/history`
- `GET /api/v1/cross-case-intelligence/history`

Access filtering is applied to every persisted decision, confirmed-link event, graph projection, and impact checkpoint before it enters the history.

v25.5 is read-only. It creates no history record, mutates no candidate, review history, confirmed-link registry, graph, impact, or source event, performs no connector execution or collection activity, and introduces no migration.
