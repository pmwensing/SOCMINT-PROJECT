# v38.3 — Offline Passive Archive Discovery

## Objective

Normalize operator-provided Common Crawl and Internet Archive index responses into deterministic review candidates without making a live network request or treating index results as evidence.

## Delivered

- offline Common Crawl and Internet Archive provider profiles;
- exact binding to an allowing v38.2 gate decision;
- required pre-live-network state;
- deterministic batch, candidate, duplicate-key, and event hashes;
- normalized candidate URL, capture timestamp, digest, status, MIME type, and archive identifier;
- 14-digit archive timestamp and ISO-8601 normalization;
- malformed-record quarantine;
- duplicate detection within a batch and across prior batches;
- accepted, duplicate, and quarantined counts;
- candidate-only evidence status and mandatory human review;
- append-only AuditLog records;
- idempotent batch replay.

## Input boundary

The service accepts records already supplied by an operator or deterministic fixture. The original response objects are not persisted. Only normalized candidate metadata, hashes, warnings, status, and bindings are recorded.

A candidate does not become an evidence artifact, source record, observation, claim, relationship, dossier contribution, export, or publication.

## Safety invariants

- no Common Crawl endpoint is contacted;
- no Internet Archive endpoint is contacted;
- no DNS lookup or HTTP request occurs;
- only an allowing v38.2 pre-live-network decision is eligible;
- malformed records are quarantined;
- mirrors and repeated index records are marked duplicate and cannot inflate support;
- raw responses are not retained by this layer;
- every candidate requires explicit review before v38.4 synthetic capture selection;
- all network, artifact, source, observation, truth, merge, claim, dossier, export, and publication flags remain false.

## Next action

`implement_v38_4_synthetic_capture_provenance_gate`
