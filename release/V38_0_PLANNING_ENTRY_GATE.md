# v38.0 — Planning Entry Gate

## Gate decision

v38.0 is planning-only. It adds no service, route, migration, network request, archive query, crawler execution, browser capture, artifact ingestion, source registration, import handoff, observation promotion, entity merge, claim decision, dossier mutation, export, or publication capability.

## Required conditions before v38.1

- the v37 closure contract exists and records `v37_closed: true`;
- v37 is merged on `master` at `46d52560ea8dcd3bd5255b4afa63453c79fbb5fe`;
- the 46 Montreal case configuration, search pack, crawler policy, and entity-scope filter are present;
- v29 remains authoritative for collection jobs, policy evaluation, adapter contracts, evidence artifacts, and collection quality;
- v35 remains authoritative for issued actions, durable execution, result envelopes, reconciliation, and recovery observability;
- v36 remains authoritative for source provenance, capture integrity, reliability, and independence;
- v37 remains authoritative for import records, quarantine, case review, explicit observation promotion, chronology, dossier readiness, and operational workflow;
- public CI requires fictional domains, deterministic mock responses, and synthetic capture fixtures;
- real case captures, credentials, cookies, private URLs, personal cloud links, and unredacted evidence are prohibited from the public repository.

## Entry-gate invariants

- every discovery request requires case, purpose, operator, an existing v29 collection job, and a current policy evaluation;
- discovery requests are deterministic, idempotent, append-only, and hash-bound;
- no URL is fetched until source, case/entity scope, direct relevance, robots, terms, public-access, rejected-query, and resource limits allow it;
- only openly accessible and approved public sources are eligible;
- 559 Macdonnel remains relocation/mitigation context only;
- Cowdy-only issue collection and unrelated entity expansion remain blocked;
- private login, cookies, credentials, paywall or CAPTCHA bypass, credential/leak/dump hunting, Tor, and hidden services remain prohibited;
- passive archive/index discovery returns candidates, not evidence or facts;
- every accepted capture enters the existing v29 artifact authority before v36 source registration;
- every downstream candidate enters the existing v37 import and review pipeline;
- mirrors, duplicates, archive copies, and recaptures cannot inflate support;
- failed, blocked, or uncertain executions are never silently retried;
- no discovery result assigns truth, causation, intent, identity, claim status, dossier eligibility, export approval, or publication approval.

## Mandatory pre-live-network sequence

The initial implementation order is fixed:

`v38.1 discovery request → v38.2 policy gate → v38.3 passive discovery → v38.4 synthetic capture/provenance pilot`

v38.1 through v38.4 must not create or enable a live third-party crawler or browser-capture path.

Before any live-network adapter is eligible, v38.4 must prove with synthetic fixtures:

- capture-envelope completeness;
- deterministic content SHA-256;
- requested, final, and redirect URL provenance;
- response and adapter metadata;
- accepted v29 artifact binding;
- registered v36 source binding;
- duplicate and quarantine non-inflation;
- explicit v37 import handoff without automatic observation promotion.

Scrapy live-network execution is eligible no earlier than v38.5. Browsertrix live-network execution is eligible no earlier than v38.6. Both remain subject to the v38.2 gate and explicit operator action.

## First runtime slice

v38.1 will implement only the discovery-request and crawl-manifest gate. It will create no network adapter and perform no public-web request.

## Next action

`implement_v38_1_discovery_request_and_crawl_manifest_gate`
