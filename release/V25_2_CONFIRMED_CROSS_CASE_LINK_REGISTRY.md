# v25.2 Confirmed Cross-Case Link Registry

Creates a separate immutable registry from only accepted analyst decisions.

A link can be registered only when the latest v25.1 decision is `accept`. Unreviewed candidates and latest decisions of `reject`, `defer`, or `split` cannot be registered.

Each registry entry binds:

- accepted decision ID and SHA-256
- accepted decision audit-record ID and timestamp
- reviewer identity and decision reason
- candidate SHA-256
- category and normalized match value
- participating case IDs
- all source occurrences and provenance
- source-occurrence snapshot SHA-256
- accepted-decision access scope
- registrar identity, timestamp, note, registry record ID, and link SHA-256

Registration requires explicit confirmation and access to every represented case. Repeating registration for the same accepted decision returns the existing registry record instead of creating a duplicate.

The workspace retains rejected, deferred, and split history, reports decision counts, lists accepted decisions pending registration, and shows confirmed links allowed by the current access scope. Viewing the registry is read-only.

Routes:

- `GET /cross-case-intelligence/confirmed-links`
- `GET /api/v1/cross-case-intelligence/confirmed-links`
- `POST /api/v1/cross-case-intelligence/<correlation_id>/confirmed-link`

v25.2 preserves the candidate, all source occurrences, case provenance, and complete review history. It creates only an immutable confirmed-link audit event, performs no collection or connector execution, and introduces no migration.
