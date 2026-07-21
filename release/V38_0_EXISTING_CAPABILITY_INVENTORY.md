# v38.0 — Existing Capability Inventory

## Reused capabilities

- 46 Montreal case, purpose, privacy, minimization, retention, sensitive-context, entity-scope, and Cowdy exclusion controls;
- the existing 46 Montreal entity-aware search pack with address, identifier, authority, event, entity-template, and negative-filter terms;
- the existing public-source tier, crawler-gate, resource-limit, output, and rejection configuration;
- v29.1 collection-job contracts, immutable state transitions, idempotency, failure classification, and authorization binding;
- v29.2 collection policy, source-class, purpose, jurisdiction, case/entity/source scope, deny-rule, exclusion, validity, and expiry evaluation;
- v29.3 adapter identity and normalization contracts;
- v29.4 accepted artifact, acquisition, content-hash, custody, and observation derivation authorities;
- v29.6 collection-quality review;
- v35 issued action contracts, durable execution identities, atomic result envelopes, evidence-backed reconciliation, and read-only recovery observability;
- v36.1 source records, capture integrity, URL separation, adapter identity, authorization notes, and claim-type reliability;
- v36.4 source independence and dependency grouping;
- v37 import envelopes, staged records, duplicate detection, quarantine, case review, explicit observation promotion, chronology, dossier readiness, and integrated workspace;
- existing search, watchlist, reporting, audit-history, redaction, quality, export, and publication controls.

## Existing configuration already aligned to v38

`config/search_packs/46_montreal_keywords.yaml` already provides:

- direct 46 Montreal address aliases;
- known municipal, fire, building, ESA, OFM, and LTB identifiers;
- authority and event search terms;
- entity-linked query templates;
- Cowdy negative filters;
- candidate-review and public-record-only rules.

`config/crawlers/46_montreal_public_sources.yaml` already provides:

- official, media/archive, public-document, and review-before-use source tiers;
- direct entity relevance, robots, terms, public-access, allowlist, rate-limit, no-login, no-bypass, no-private-account, and human-review gates;
- depth, page, delay, and concurrency defaults;
- crawl-manifest, robots, source, hash, matched-term, matched-entity, scope, review, and private-output requirements;
- rejection of unrelated addresses, unreviewed candidates, non-public sources, unscoped collection, and circumvention.

## Gaps addressed by v38

- one deterministic discovery-request and crawl-manifest contract bound to the existing v29 job and policy authorities;
- executable source/scope/robots/terms/query/resource-limit decisions before any network action;
- passive Common Crawl and Internet Archive candidate discovery;
- a synthetic capture/provenance pilot proving capture envelopes, hashes, accepted v29 artifact bindings, v36 source registration, duplicate/quarantine controls, and explicit v37 handoff before live collection exists;
- an official/public HTTP crawler adapter with strict limits and complete request/response provenance, eligible only after the synthetic governance proof;
- Browsertrix WARC/WACZ and screenshot preservation for explicitly approved public pages, eligible only after the synthetic governance proof;
- mirror, duplicate, recapture, and change triage without corroboration inflation;
- explicit handoff of reviewed candidates to the existing v37 import workflow;
- one public-discovery workspace with execution, recovery, capture, provenance, and handoff visibility;
- end-to-end browser proof that blocked or unreviewed collection cannot execute.

## Required dependency order

1. v38.1 discovery request and crawl manifest;
2. v38.2 policy, source, scope, robots, terms, query, and resource gate;
3. v38.3 passive archive/index discovery;
4. v38.4 synthetic capture governance, artifact acceptance, source registration, and import handoff proof;
5. v38.5 Scrapy-compatible live public HTTP collection;
6. v38.6 Browsertrix live public-page preservation.

No live-network crawler or browser-capture path is eligible before v38.4 is merged and green.

## Non-goals

- a general-purpose internet crawler or search engine;
- broad people-search, bulk social scraping, or unrelated entity expansion;
- private-account, credentialed, paywalled, CAPTCHA-protected, or login-only access;
- robots, terms, rate-limit, authentication, or access-control circumvention;
- credential dumps, leak databases, backup indexes, exposed admin panels, or stolen data discovery;
- Tor, hidden-service, dark-market, or dark-web collection;
- storing real case captures or unredacted evidence in the public repository;
- replacing v29 collection jobs, v35 execution governance, v36 source records, or v37 imports;
- automatic observation promotion, truth assignment, entity merge, claim approval, dossier mutation, export, or publication;
- inferring misconduct, causation, intent, or evidentiary significance from discovery or page changes alone.
