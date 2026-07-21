# v38.0 — Schema Ownership Map

| Concern | Authoritative owner | v38 responsibility |
|---|---|---|
| Case, purpose, privacy, minimization, retention and sensitive context | existing case/security/privacy controls | require exact bindings and block scope drift; do not replace |
| 46 Montreal terms, identifiers and negative filters | existing search-pack configuration | consume reviewed query inputs; do not create an unrelated query authority |
| Public source tiers, allowlist intent, crawler limits and rejection rules | existing crawler configuration plus v29 policy records | evaluate and version operational decisions; do not weaken configured boundaries |
| Collection request identity, state and idempotency | v29.1 collection-job contracts | bind each discovery request and adapter execution to one existing job |
| Authorization, source scope, deny rules, validity and expiry | v29.2 collection policy | require a current allowing evaluation before queue or execution |
| Adapter identity and normalization envelope | v29.3 | define v38 adapter profiles through the existing adapter contract |
| Durable action execution and ambiguous outcomes | v35 action contracts and execution ledger | invoke approved adapters once, record result envelopes, and use existing reconciliation/recovery controls |
| Raw capture, content hash, acquisition and custody | v29.4 evidence ingestion | submit captures for acceptance; never create a second capture vault |
| Collection completeness and quality | v29.6 | expose existing findings and require quality review where applicable |
| Source provenance, canonical/retrieved URLs and capture integrity | v36.1 | register accepted captures through existing source APIs only |
| Mirror, archive and dependent-source grouping | v36.4 | submit dependency evidence and display current group decisions; do not self-count copies |
| Import envelopes, staged records, duplicate detection and quarantine | v37.1–v37.2 | hand off explicitly selected capture candidates through the existing import pipeline |
| Case review and observation promotion | v37.3–v37.4 plus v29 observation authority | expose status; never promote automatically |
| Entity, claim, conflict, relationship, chronology and dossier review | v30 and v36, orchestrated by v37 | preserve current review decisions and warnings; do not assign truth or causation |
| Search, watchlist and reporting history | existing v27 services | reuse reporting/history where needed; do not create a second monitoring authority |
| Redaction, quality, approval, export and publication | existing release/export services | expose readiness only; do not export or publish |
| Audit history | append-only AuditLog and exact event hashes | record discovery, gate, execution, capture and handoff events without mutation |

## v38-owned records

v38 may introduce append-only, hash-bound records for:

- discovery-request definitions;
- crawl-manifest definitions;
- source/scope/robots/terms/query/resource gate decisions;
- passive archive/index candidate results;
- adapter execution bindings and capture result summaries;
- robots snapshots and response provenance manifests;
- capture-to-artifact and capture-to-source bindings;
- duplicate/change/relevance triage projections;
- explicit v37 handoff decisions.

These are workflow and provenance records. They are not evidence artifacts, canonical observations, identity facts, approved claims, relationships, dossiers, exports, or publications.

## Non-duplication rules

- no parallel case registry;
- no second search-pack authority;
- no second collection-job or policy engine;
- no second durable action ledger;
- no second artifact or WARC evidence vault;
- no second source registry or reliability model;
- no second import or quarantine pipeline;
- no second observation or identity authority;
- no mutable canonical fact or truth table;
- no alternate claim, relationship, dossier, export, or publication pipeline;
- all v38 projections must be reproducible from exact request, policy, execution, capture, artifact, source and import hashes.
