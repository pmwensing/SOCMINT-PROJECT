# v25.4 Cross-Case Link Impact Analysis

Adds a read-only impact analysis for each visible confirmed cross-case link.

The analysis calculates affected cases, entities, evidence packages, review queues, closure states, and archive records. It also identifies the graph nodes and edges associated with the confirmed link.

Every result preserves a confirmed-link binding containing the confirmed-link ID and SHA-256, registry record ID, accepted review decision ID and SHA-256, and source-occurrence snapshot SHA-256.

Every result also preserves a graph binding containing the current graph SHA-256 and the affected graph node and edge IDs.

The deterministic impact payload receives an impact SHA-256 covering the affected cases, graph entities, evidence and delivery package records, queue entries, closure states, archive records, and graph references.

Routes:

- `GET /cross-case-intelligence/confirmed-links/<confirmed_link_id>/impact`
- `GET /api/v1/cross-case-intelligence/confirmed-links/<confirmed_link_id>/impact`

Access filtering is applied before analysis. A user must be able to access every case represented by the confirmed link.

v25.4 keeps the confirmed-link and graph records unchanged. It is read-only, creates no impact record, mutates no case, review, archive, package, registry, or graph event, performs no connector execution or collection activity, and introduces no migration.
