# v38.2 — Public Discovery Policy Gate

## Objective

Evaluate each v38.1 discovery request against explicit source, scope, robots, terms, public-access, rejected-query, access-indicator, domain, and resource-limit controls before passive discovery or any future network execution can occur.

v38.2 records immutable allow or block decisions. It performs no DNS lookup, HTTP request, archive query, crawler execution, browser capture, artifact ingestion, source registration, observation promotion, dossier mutation, export, or publication.

## Delivered

- exact binding to a v38.1 request event and manifest SHA-256;
- source-tier validation for official, media/archive, public-document, and review-before-use sources;
- direct case relevance or reviewed candidate-entity requirement;
- public-access confirmation;
- robots `allow` requirement;
- reviewed terms approval requirement;
- explicit login, paywall, CAPTCHA, and private-account indicators;
- source-domain allowlist and seed-host evaluation;
- Cowdy-only scope exclusion and prohibited credential/leak/bypass/dark-web query screening;
- policy ceilings for pages, depth, delay, concurrency, redirects, response bytes, domains, and content types;
- immutable allow or block decisions with visible reasons;
- deterministic decision IDs and idempotent replay;
- `passive_discovery_eligible` only for an allowing decision;
- `live_network_eligible: false` for every result.

## Decision semantics

A structurally valid evaluation is recorded even when the result is `block`. This preserves why the request was denied instead of discarding the decision.

An allowing decision means only that v38.3 may process operator-provided passive archive/index responses offline. It does not authorize a live Common Crawl request, Internet Archive request, HTTP crawl, or Browsertrix capture.

## Safety invariants

- deny and exclusion rules override eligibility;
- direct relevance or a reviewed candidate is mandatory;
- login, paywall, CAPTCHA, private-account, robots, or terms blockers cannot be overridden by source tier;
- requested domains and resource limits must be within the evaluated policy ceiling;
- excluded-address and prohibited-query findings remain visible;
- no network or downstream evidentiary action is performed;
- all consequential decisions remain append-only and hash-bound.

## Next action

`implement_v38_3_offline_passive_archive_discovery`
