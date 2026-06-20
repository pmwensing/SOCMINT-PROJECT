# v30.2 — Evidence and Observation Linkage

## Objective

Bind proposed corroboration claims to accepted evidence artifacts and derived observations using deterministic append-only manifests.

## Delivered

- append-only linkage records in the existing audit log
- deterministic linkage IDs and SHA-256 manifests
- evidence existence and accepted-state validation
- observation existence validation
- observation-to-artifact binding validation
- duplicate linkage blocking
- linkage inventory and missing-linkage findings in the Analytic Review Workspace
- administrator-only list and create APIs
- focused contract and route tests

## Routes

- `GET /api/v1/analytic-review/claims/<claim_id>/source-linkages`
- `POST /api/v1/analytic-review/claims/<claim_id>/source-linkages`

## Boundaries

No evidence, observation, claim, confidence, dossier, connector, or schema mutation is performed.

## Next action

Validate v30.2 and proceed to v30.3 Contradiction and Disagreement Handling.
