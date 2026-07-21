# v38.0 — Lawful Public-Web Discovery and Capture Roadmap

## Objective

Turn the closed v37 operational intelligence pipeline into a controlled public-source discovery and preservation workflow:

`approved search pack → discovery request → policy/robots/terms gate → passive archive candidates → explicit public-page capture → accepted artifact → source registration → reviewed v37 import candidate`

v38 does not create a new collection-job system, evidence vault, source registry, import pipeline, observation authority, identity graph, truth engine, dossier backend, or export authority. It adds public-web discovery and capture adapters behind the existing v29, v35, v36, and v37 controls.

## Program interpretation

“Public-web discovery” includes openly accessible official pages, public documents, public registries, public media pages, Common Crawl indexes, and Internet Archive indexes or snapshots when their use is permitted.

It excludes private accounts, authenticated areas, paywalled or CAPTCHA-protected content, credential or leak hunting, database dumps, Tor or hidden services, uncontrolled social scraping, and unrelated entity or address expansion.

## Entry conditions

- v37 is formally closed at merge `46d52560ea8dcd3bd5255b4afa63453c79fbb5fe`.
- The 46 Montreal case scope, entity-aware search pack, and public-source crawler policy are present on `master`.
- v29 remains authoritative for collection jobs, policy evaluation, adapters, artifacts, and collection quality.
- v35 remains authoritative for durable action execution, result envelopes, reconciliation, and recovery visibility.
- v36 remains authoritative for source provenance, capture integrity, source reliability, and source independence.
- v37 remains authoritative for import records, quarantine, scope review, observation promotion, chronology, dossier readiness, and the operational workspace.
- Runtime work begins only after this planning gate is merged.
- Public CI uses fictional URLs, deterministic mock responses, and synthetic WARC/WACZ or screenshot fixtures only.

## Delivery slices

### v38.0 — Planning and compatibility gate

- define legal-safety, privacy, scope, ownership, and non-duplication boundaries;
- define the v38.1–v38.9 sequence;
- require the v37 closure contract and existing 46 Montreal crawler/search configurations;
- add focused planning tests;
- no runtime, route, network call, or migration.

### v38.1 — Discovery request and crawl-manifest gate

- create a case-scoped discovery request bound to an existing v29.1 collection job and current v29.2 policy evaluation;
- require case, purpose, operator, seed/query set, source class, adapter intent, resource limits, and administrative reason;
- generate deterministic request, manifest, and idempotency hashes;
- store append-only request history;
- do not fetch a URL in this slice.

### v38.2 — Source, scope, robots, terms, and query evaluation

- evaluate source allowlist tier, direct 46 Montreal relevance, reviewed candidate-entity relevance, public accessibility, robots policy, terms notes, deny terms, and excluded addresses;
- require explicit domain, depth, page, delay, concurrency, redirect, content-type, and size limits;
- reject login, paywall, CAPTCHA, private-account, credential, leak, dump, backup-index, dark-web, Tor, and unrelated expansion requests;
- produce a signed gate decision that is required before queue or execution.

### v38.3 — Passive archive and index discovery

- query approved Common Crawl and Internet Archive index endpoints through versioned adapters;
- return candidate URLs, timestamps, digests, status metadata, and archive identifiers without treating results as evidence;
- deduplicate candidates by normalized URL, archive identity, and digest;
- require operator review before any page or snapshot capture;
- prefer passive discovery before active crawling when it can answer the discovery question.

### v38.4 — Official/public HTTP crawler adapter

- implement an operator-triggered Scrapy-compatible adapter for approved official and public sources;
- obey the evaluated robots, terms, domain, rate, concurrency, depth, page, redirect, content-type, and size limits;
- disable cookies and private authentication;
- capture request/final URL, redirect chain, response headers, status, timing, MIME type, body hash, and adapter identity;
- stop on scope, policy, robots, content, or resource-limit violations;
- no arbitrary off-domain following or automatic scope growth.

### v38.5 — Browsertrix preservation adapter

- create an operator-triggered Browsertrix job only for an approved JavaScript-heavy public page or public media page;
- preserve WARC/WACZ, screenshots, page metadata, network/capture summary, and exact hashes in approved private storage;
- keep secrets, cookies, credentials, and authenticated browser profiles disabled;
- bind the result to the same discovery request, policy decision, and v35 execution identity;
- no automatic dossier or observation action.

### v38.6 — Capture acceptance and provenance registration

- submit captured files and metadata through the existing v29.4 artifact authority;
- require accepted artifact state and matching SHA-256 before source registration;
- register canonical/retrieved/final URLs, capture time, published time when known, adapter version, access method, terms notes, and artifact bindings through v36.1;
- preserve robots record, policy decision, crawl manifest, redirect chain, response metadata, and capture manifest;
- do not copy source content into a second backend.

### v38.7 — Duplicate, change, relevance, and import triage

- group mirrors, archive copies, canonical duplicates, and recaptures through existing source-independence controls;
- calculate deterministic change summaries without declaring factual significance;
- classify direct case relevance, relocation/mitigation context, out-of-scope content, and candidate-review-required content;
- require explicit analyst selection before creating a v37 import envelope;
- duplicates, mirrors, blocked captures, and quarantined candidates cannot inflate support.

### v38.8 — Public Discovery and Capture Workspace and browser E2E

- provide one administrator workspace for requests, gate decisions, candidates, executions, captures, artifacts, source records, duplicate/change groups, and v37 handoff status;
- separate request/execute actions from read-only diagnostics and recovery views;
- expose no private credentials, cookies, raw sensitive values, or unredacted case evidence;
- prove in browser E2E that blocked sources cannot run and that no truth, merge, claim-approval, dossier, export, or publication bypass exists.

### v38.9 — Controlled pilot, release evidence, and closure

- run a fictional 46 Montreal-shaped public-source pilot using deterministic local HTTP/archive fixtures only;
- prove allow, block, robots, terms, redirect, rate, duplicate, change, capture, artifact, source, and v37 handoff paths;
- record exact merge and validation evidence;
- require CI, Full Verification, legacy readiness, PostgreSQL/migration/backup/boot checks, and combined browser E2E;
- close v38 only after every planned slice is merged.

## Acceptance criteria

- every discovery request resolves to an existing case, purpose, operator, v29 collection job, and current allowing policy decision;
- every active fetch is preceded by an allowing source/scope/robots/terms/resource decision;
- passive archive results remain candidates until an explicit capture and artifact acceptance occurs;
- every capture records exact URLs, redirects, response metadata, times, adapter version, and SHA-256;
- every evidentiary capture resolves to an accepted v29 artifact and v36 source record;
- repeated requests and captures are deterministic and idempotent;
- mirrors, duplicates, archives, and recaptures cannot inflate corroboration;
- 559 Macdonnel remains relocation/mitigation context only and Cowdy-only issue expansion remains blocked;
- public CI contains no real case evidence, credentials, private links, or live third-party crawling;
- failed, blocked, and uncertain executions are never silently retried;
- no automatic observation promotion, truth assignment, entity merge, claim approval, dossier mutation, export, or publication occurs;
- all consequential records are append-only and hash-bound.

## Next action

`implement_v38_1_discovery_request_and_crawl_manifest_gate`
