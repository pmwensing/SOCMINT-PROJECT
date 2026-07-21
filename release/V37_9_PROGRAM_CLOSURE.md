# v37.9 — Operational Case Intelligence Program Closure

## Closure decision

The **v37 — Operational Case Intelligence Pipeline** program is closed.

All planned slices from v37.0 through v37.8 have been implemented, validated, and merged. v37.9 adds only the closure contract, release evidence, and focused closure tests. It introduces no runtime service, route, migration, collection action, import execution, observation promotion, entity merge, claim decision, dossier mutation, export, or publication capability.

## Production outcome

v37 turns the closed v36 analytical foundation into a defensible operator workflow:

1. bind an operator-provided export to a case, purpose, operator, accepted artifact, filename, SHA-256, tool, adapter, and timestamps;
2. parse JSON, JSONL/NDJSON, CSV, and HTML-table exports offline;
3. stage deterministic records with duplicate and quarantine controls;
4. apply the fictional 46 Montreal pilot's direct-scope, relocation-context, excluded-address, and candidate-review rules;
5. require explicit human record decisions;
6. promote one accepted record at a time through the existing v29 observation authority;
7. compose entity, claim, conflict, verification, review, contribution, relationship, and dossier state in a read-only analyst workflow;
8. preserve event, report, capture, and validity times plus inference warnings in chronology;
9. create an append-only export-readiness projection without exporting or publishing;
10. expose the complete pipeline in an administrator-only, read-only workspace with browser proof that prohibited controls are absent.

## Delivered slices

- **v37.0** — Planning and Compatibility Gate
- **v37.1** — Case-Scoped Universal Import Envelopes
- **v37.2** — Immutable Import Records and Offline Adapters
- **v37.3** — Controlled 46 Montreal Pilot
- **v37.4** — Explicit Observation Promotion
- **v37.5** — Guided Analyst Workflow
- **v37.6** — Relationship and Chronology Workflow
- **v37.7** — Dossier Export Readiness
- **v37.8** — Operational Case Intelligence Workspace and Browser E2E
- **v37.9** — Program Closure and Release Evidence

## Final runtime validation

The final v37.8 head `7bb00b7516c87af7d85128402d634609c5226efd` passed:

- CI **4432**;
- Full Verification **1150**;
- legacy runtime readiness **2447**;
- combined v32 through v37 browser E2E **180**.

It was merged through PR **#315** as `a9e53695a2db374791904aa56f6264770058d387`.

## Preserved authority boundaries

The following remain authoritative and were not replaced:

- existing case, purpose, access, authorization, minimization, sensitive-context, retention, and privacy controls;
- v29 collection-job contracts, evidence artifacts, custody state, and derived observations;
- v30 claims, evidence links, conflicts, confidence, human review, and dossier-contribution decisions;
- v36 source registry, canonical observations, entity resolution, source independence, claim verification, relationship timelines, dossier synthesis, and entity-accuracy workspace;
- existing redaction, quality, approval, audit, bundle, manifest, export, and publication services;
- append-only AuditLog history.

## Safety invariants

v37 does not provide:

- automatic or hidden collection;
- credential, authentication, paywall, CAPTCHA, robots, or private-account bypass;
- automatic observation promotion;
- adapter, parser, model, or AI truth assignment;
- automatic entity merge, claim approval, or human-review completion;
- automatic dossier mutation, export, or publication;
- a second evidence vault, observation authority, identity graph, truth table, dossier pipeline, or export authority;
- real case evidence, credentials, private URLs, or personal cloud links in public fixtures.

The Operational Case Intelligence Workspace is read-only. The browser checkpoint verifies the required safety markers and absence of forms or named collection, promotion, merge, approval, export, publication, and dossier-mutation controls.

## Closure scope

v37.9 is documentation-and-test-only. It records that:

- v37 is closed;
- no v37 runtime or schema work remains;
- the controlled 46 Montreal pilot uses fictional records only;
- all future runtime work requires a new planning and compatibility gate;
- exact import, review, promotion, chronology, readiness, validation, and merge history remains preserved.

## Next action

`define_the_next_program_planning_and_compatibility_gate_before_runtime_work`
