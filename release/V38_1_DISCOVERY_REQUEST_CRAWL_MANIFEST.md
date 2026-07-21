# v38.1 — Discovery Request and Crawl Manifest

## Objective

Create the first runtime slice of v38 as a deterministic, append-only discovery-request and crawl-manifest contract bound to the existing v29 collection-job and policy authorities.

v38.1 records an operator-approved discovery definition. It performs no DNS lookup, HTTP request, archive query, crawler execution, browser capture, artifact ingestion, source registration, observation promotion, dossier mutation, export, or publication.

## Delivered

- deterministic `discovery_request_id` and event SHA-256;
- case, purpose, operator, jurisdiction, source class, and adapter-intent metadata;
- exact binding to a non-terminal v29.1 collection job;
- exact binding to an allowing v29.2 policy evaluation and contract hash;
- normalized query terms and public HTTP/HTTPS seed URLs;
- explicit domain, page, depth, delay, concurrency, redirect, response-size, and content-type limits;
- append-only AuditLog storage;
- idempotent replay for an identical idempotency key and definition;
- conflict blocking when an idempotency key is reused with a different definition;
- explicit `execution_eligible: false` state pending v38.2;
- visible false markers for every prohibited network and downstream action.

## Validation boundaries

Registration is blocked when:

- explicit confirmation, actor, case, purpose, job, policy evaluation, source class, jurisdiction, query/seed input, limits, idempotency key, or reason is missing;
- an adapter intent is unsupported;
- a seed URL is malformed or contains credentials;
- a resource-limit field is incomplete, invalid, or negative;
- the collection job is missing or terminal;
- case, purpose, or source class differs from the collection-job contract;
- the policy evaluation is missing, denied, bound to another job or contract hash, or uses another jurisdiction.

## Authority reuse

- v29.1 remains authoritative for collection-job identity and lifecycle;
- v29.2 remains authoritative for collection-policy decisions;
- AuditLog remains the append-only storage authority;
- v38.1 creates no second policy engine, job system, execution ledger, evidence vault, source registry, or import pipeline.

## Safety invariants

- no network library is invoked;
- no collection job is transitioned or mutated;
- no policy is created or revised;
- no live-network execution path exists;
- no artifact, source, observation, identity, claim, relationship, dossier, export, or publication record is created;
- public fixtures use fictional domains only.

## Next action

`implement_v38_2_public_discovery_policy_gate`
