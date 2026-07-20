# v36.2 — Canonical Observation Contract

## Objective

Wrap accepted v29 evidence observations in deterministic, tool-neutral canonical envelopes without replacing, rewriting, or assigning identity or truth to the authoritative observation records.

## Delivered

- append-only canonical observation registration and state history;
- exact source, artifact, tool-run, and authoritative-observation bindings;
- raw and normalized values with deterministic hashes;
- observed time and optional validity interval;
- extraction method and bounded extraction confidence;
- JSON, CSV, NDJSON, and manual adapter formats;
- adapter name and version;
- structured observation context;
- optional parent-observation bindings;
- automatic quarantine for extraction confidence below 0.5;
- explicit quarantine reasons;
- append-only human transition from quarantined to accepted or rejected;
- administrator-only inventory, detail, registration, filtering, and state APIs;
- analytic-review route integration.

## Routes

- `GET /api/v1/entity-accuracy/observations`
- `POST /api/v1/entity-accuracy/observations`
- `GET /api/v1/entity-accuracy/observations/<canonical_observation_id>`
- `POST /api/v1/entity-accuracy/observations/<canonical_observation_id>/state`

## Authoritative reuse

The v29 `observation_derived` record remains authoritative for the source observation. The v36.2 envelope binds to its observation SHA, artifact event SHA, collection job, accepted capture artifact, and v36.1 source record.

## Safety boundary

- no source observation mutation;
- no artifact mutation;
- no identity assignment;
- no truth assignment;
- no claim creation or approval;
- no dossier mutation;
- accepted and rejected envelopes are terminal;
- quarantined observations require explicit confirmed review;
- no migration or competing observation table.

## Verification

Focused coverage includes source, case, artifact, tool-run, and observation binding; accepted and quarantined registration; extraction-confidence quarantine; validity interval checks; adapter validation; parent bindings; terminal-state enforcement; administrator-only routes; state filtering; and analytic-review registration.

## Next action

Implement v36.3 Entity Candidate Resolution using accepted canonical observations and explainable positive, negative, strong, supporting, and weak signals without automatically merging identities.
