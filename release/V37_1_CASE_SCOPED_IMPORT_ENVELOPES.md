# v37.1 — Case-Scoped Universal Import Envelopes

## Objective

Register deterministic, case-scoped metadata envelopes for operator-provided tool exports while binding every import to an accepted v29 artifact and preserving existing evidence, observation, identity, review, dossier, export, and publication authorities.

## Delivered

- JSON, JSONL, NDJSON, CSV, and HTML export-format contracts;
- required case, purpose, operator, artifact, content SHA-256, original filename, media type, tool identity, adapter identity, export time, import time, declared record count, source references, and collection context;
- accepted-artifact, case, and hash validation;
- deterministic import IDs and rerun keys;
- idempotent replay that reuses an existing envelope instead of duplicating it;
- append-only AuditLog records;
- administrator-only inventory, creation, detail, and case-filter APIs;
- analytic-review route-chain registration.

## Routes

- `GET /api/v1/operational-imports`
- `POST /api/v1/operational-imports`
- `GET /api/v1/operational-imports/<import_id>`

## Safety boundary

- no raw export payload is stored by this service;
- no connector, crawler, browser, API, or private-account collection is executed;
- no observation, source, entity, claim, relationship, dossier, export, or publication record is created or mutated;
- adapter identity is recorded but adapters do not assign truth;
- filename paths are rejected so operator workstation paths are not stored as original filenames;
- public tests use fictional metadata only.

## Next action

Implement v37.2 immutable import manifests and deterministic staged records with duplicate detection, normalization warnings, and quarantine.
