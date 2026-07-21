# v37.2 — Immutable Import Manifests and Staged Records

## Objective

Parse operator-provided exports through pure offline adapters and stage deterministic review records without storing the original payload, running collection tools, or creating authoritative observations.

## Delivered

- pure JSON, JSONL/NDJSON, CSV, and HTML-table parsers;
- fictional fixture coverage for every supported format;
- deterministic staged-record and batch identifiers;
- duplicate detection within a batch and across prior staged records;
- accepted, quarantined, and duplicate initial states;
- automatic quarantine for warnings or extraction confidence below 0.5;
- duplicate records cannot support claims;
- idempotent batch replay;
- append-only batch events and administrator inventory/detail APIs;
- analytic-review route integration.

## Safety boundary

- adapters perform no network access or collection;
- original export payload text is not persisted by the adapter or staging service;
- staged records are review candidates, not canonical facts or claims;
- no automatic observation promotion;
- no truth assignment, identity merge, claim approval, dossier mutation, export, or publication;
- public fixtures contain fictional generic entities and locations only.

## Next action

Implement v37.3 controlled 46 Montreal pilot classification and review decisions over staged records.
