# v29.3 Connector Normalization and Adapter Contract

Adds a narrow Connector Normalization and Adapter Contract over existing connector definitions.

Each adapter contract records a capability declaration, normalized input schema, normalized output schema, authorization requirements, rate-limit metadata, deterministic error classes, provenance requirements, health contract, dossier-value declaration, revision, definition SHA-256, adapter event ID, and adapter event SHA-256.

Adapter revisions create new immutable versions bound to the prior contract. Existing connector definitions are not rewritten.

Conformance evaluation compares observed capabilities, schemas, error classes, provenance fields, and health fields with the active adapter contract. Missing required behavior produces deterministic findings and prevents the adapter from being treated as conformant.

The deterministic error-class catalog includes authorization, scope, rate limit, network, upstream, input, output, parsing, provenance, duplicate, and unknown errors.

The workspace reports active and superseded adapter contracts, connector bindings, latest conformance state, missing contract sections, nonconformant adapters, and immutable adapter history.

All writes require an authenticated active administrator, CSRF validation, explicit confirmation, and an administrative or evaluation reason.

Preservation boundaries:

- no connector execution
- no connector-definition mutation
- no secret exposure
- no case-access mutation
- no evidence rewrite
- no connector added for breadth
- adapter and evaluation history is append-only

Routes:

- `GET /collection-operations/adapters`
- `GET /api/v1/collection-operations/adapters`
- `POST /api/v1/collection-operations/adapters`
- `POST /api/v1/collection-operations/adapters/<adapter_contract_id>/revise`
- `POST /api/v1/collection-operations/adapters/<adapter_contract_id>/evaluate`

This slice introduces no migration.
