# v25.6 Cross-Case Intelligence Metrics and Confidence

Adds a read-only analytics layer across the current cross-case intelligence workspace.

The metrics calculate:

- candidate volume by correlation category
- review dispositions across all decisions and latest decisions
- confirmation conversion from candidates to confirmed links
- accepted-decision materialization into the registry
- graph density, edge-to-node ratio, average degree, and median degree
- cross-case reach across visible and confirmed cases
- source-occurrence coverage from candidate occurrences to confirmed-link occurrences
- impact breadth across cases, entities, evidence packages, review queues, closure states, and archive records
- analyst throughput, active review days, reviews per active day, and disposition counts
- confidence indicators derived from review coverage, accepted-link materialization, source-occurrence coverage, cross-case reach, and graph support

The confidence score is an operational indicator. It is not a probability and does not claim factual certainty about an identity, relationship, or evidentiary conclusion.

A deterministic metrics SHA-256 covers the complete metric payload. Access filtering is applied before candidate, review, link, graph, and impact data contribute to the calculations.

Routes:

- `GET /cross-case-intelligence/metrics`
- `GET /api/v1/cross-case-intelligence/metrics`

v25.6 is read-only. It creates no metrics record, mutates no candidate, review history, confirmed-link registry, graph, impact, or source event, performs no connector execution or collection activity, and introduces no migration.
