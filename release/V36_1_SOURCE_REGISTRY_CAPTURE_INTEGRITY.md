# v36.1 — Source Registry and Capture Integrity

## Objective

Create append-only source-origin and capture-integrity records over accepted evidence artifacts without creating a second evidence vault, assigning truth, approving claims, or mutating observations or dossiers.

## Delivered

- deterministic `SourceRecord` identifiers;
- exact case and accepted-artifact bindings;
- SHA-256 equality between the source record and authoritative capture artifact;
- canonical and retrieved URL separation;
- published and captured time metadata;
- publisher or operator, jurisdiction, source type, and original-versus-derived classification;
- public, archive, import, API, and explicitly authorized account access metadata;
- mandatory authorization references for authenticated collection;
- adapter name and version bindings;
- terms and collection notes;
- empty source-independence placeholder pending v36.4;
- append-only claim-type-specific source reliability assessments;
- visible authority, directness, authenticity, capture-integrity, and temporal-relevance components;
- reliability bands A, B, C, D, E, and U with reasons and limitations;
- administrator-only inventory, detail, registration, and assessment APIs;
- registration through the existing analytic-review route chain.

## Routes

- `GET /api/v1/entity-accuracy/sources`
- `POST /api/v1/entity-accuracy/sources`
- `GET /api/v1/entity-accuracy/sources/<source_id>`
- `GET /api/v1/entity-accuracy/sources/<source_id>/reliability-assessments`
- `POST /api/v1/entity-accuracy/sources/<source_id>/reliability-assessments`

## Authoritative reuse

v36.1 uses:

- accepted artifacts from `evidence_ingestion_v29_4`;
- existing artifact case and acquisition bindings;
- existing SHA-256 content hashes;
- the existing append-only `AuditLog`;
- existing administrator authorization;
- the existing analytic-review route chain.

No migration, source-content copy, second evidence backend, connector execution, or hidden collection process is introduced.

## Safety boundary

- source registration does not prove the source's statements are true;
- source reliability is assessed for a defined claim type, never globally;
- platform or domain identity cannot assign a reliability band;
- source count does not establish independence;
- independence grouping remains unset until v36.4;
- no claim is created, approved, or made dossier-eligible;
- no artifact, observation, identity graph, claim, review, or dossier is mutated;
- URL credentials are rejected;
- authenticated collection requires an authorization reference.

## Verification

Focused coverage includes:

- accepted-artifact, case, and content-hash binding;
- deterministic URL normalization and source identity;
- duplicate blocking;
- authenticated-access authorization requirements;
- claim-type-specific reliability profiles;
- component range and completeness checks;
- append-only duplicate assessment blocking;
- administrator-only route behavior;
- GET/POST surface contracts;
- analytic-review route registration;
- explicit false flags for truth assignment, claim approval, and downstream mutation.

## Next action

Implement v36.2 Canonical Observation Contract over accepted v29 observations without replacing or mutating the authoritative observation records.
