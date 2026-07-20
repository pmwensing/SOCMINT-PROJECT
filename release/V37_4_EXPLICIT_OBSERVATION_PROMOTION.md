# v37.4 — Explicit Observation Promotion

## Objective

Promote one explicitly reviewed staged import record at a time through the existing v29 evidence-observation authority.

## Delivered

- accepted v37.3 review decision required;
- current staged-record, scope-assessment, import-envelope, and accepted-artifact bindings;
- duplicate and out-of-scope promotion blocks;
- explicit derivation method, reason, and confirmation;
- one call to the existing v29 `derive_observation` service per request;
- append-only promotion event binding the import, staged record, scope assessment, review decision, artifact, and resulting observation hashes;
- idempotent replay;
- relocation-context preservation so promoted relocation observations remain barred from issue-claim support;
- administrator-only inventory, promotion, and detail APIs;
- analytic-review route integration.

## Safety boundary

- no bulk or automatic promotion route;
- no direct observation-table replacement;
- no truth assignment, entity merge, claim approval, dossier mutation, export, or publication;
- authoritative artifact and observation validation remains in v29;
- canonical observation registration remains a separate v36.2 action.

## Next action

Implement the guided analyst workflow over imports, review decisions, promotions, entity candidates, claims, conflicts, verification, relationships, and dossier snapshots.
