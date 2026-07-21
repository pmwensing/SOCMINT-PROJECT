# v37.0 — Existing Capability Inventory

## Reused capabilities

- v29 collection-job contracts and evidence-safe artifact ingestion;
- accepted artifact state, content hashes, custody bindings, and derived observations;
- v30 claim creation, evidence/observation links, conflicts, confidence, human review, and dossier-contribution decisions;
- v36 source registry, canonical observation envelopes, entity-candidate assessments, source-independence groups, claim verification, relationship timelines, dossier snapshots, and read-only workspace;
- existing case authorization, purpose, minimization, privacy, retention, sensitive-context, audit, redaction, quality, export, and publication gates;
- the rebuilt 46 Montreal case scope, evidence-vault manifests, hash helpers, and location-map helpers.

## Gaps addressed by v37

- one tool-neutral import envelope for exported JSON, JSONL/NDJSON, CSV, and HTML reports;
- immutable import manifests and deterministic rerun keys;
- staged record hashes, duplicate detection, quarantine, and adapter diagnostics;
- case-specific pilot review without exposing real evidence in CI;
- explicit analyst promotion of reviewed import records into existing observations;
- workflow composition across entity, claim, conflict, relationship, dossier, redaction, and export-readiness layers;
- an integrated operator workspace and end-to-end browser checkpoint.

## Non-goals

- running collection tools automatically;
- logging into private accounts;
- bypassing authentication, paywalls, CAPTCHAs, robots rules, or terms;
- bulk people-search scraping;
- storing raw case evidence in the public repository;
- automatic identity merge, truth assignment, claim approval, dossier mutation, export, or publication;
- replacing existing evidence, identity, dossier, or export authorities.
