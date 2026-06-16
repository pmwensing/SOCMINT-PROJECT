# v25.3 Cross-Case Relationship Graph

Projects confirmed links into a read-only graph of cases, entities, identifiers, infrastructure, evidence, and temporal relationships.

The graph is built only from v25.2 confirmed-link registry entries visible within the current access scope. Candidate correlations, rejected decisions, deferred decisions, split decisions, and unreviewed candidates are not projected.

Every node and edge retains:

- confirmed-link IDs and SHA-256 values
- accepted-review bindings, including decision ID and SHA-256
- source occurrences and source-occurrence snapshot hashes
- access scope from the accepted review
- registry record ID, registrar identity, and registration timestamp
- case-level provenance
- deterministic node or edge SHA-256

Node types:

- case
- entity
- identifier
- infrastructure
- evidence
- temporal

Edge types:

- `case_confirmed_link`
- `case_observed_at`
- `linked_value_observed_at`

The browser view renders an interactive SVG projection and exposes node and edge inspection, graph counts, node-type counts, edge-type counts, the complete graph payload, and a deterministic graph SHA-256.

Routes:

- `GET /cross-case-intelligence/graph`
- `GET /api/v1/cross-case-intelligence/graph`

v25.3 is read-only. It preserves every node and edge binding, source occurrence, accepted review, access scope, and provenance. Viewing the graph creates no graph record, mutates no confirmed link or source event, performs no connector execution or collection activity, and introduces no migration.
