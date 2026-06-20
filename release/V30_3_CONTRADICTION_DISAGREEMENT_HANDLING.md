# v30.3 — Contradiction and Disagreement Handling

## Objective

Preserve contradictory claims and analyst disagreements as append-only analytic conflict records, with explicit review and resolution events that never overwrite claims or source material.

## Delivered

- contradiction and analyst-disagreement conflict types
- deterministic conflict identifiers and claim bindings
- validation that compared claims share case and entity context
- contradiction validation for matching claim types with distinct normalized values
- append-only unresolved conflict records
- explicit resolution choices: both retained, claim A preferred, claim B preferred, or insufficient evidence
- duplicate conflict blocking
- immutable resolution history
- conflict inventory and unresolved-conflict findings in the Analytic Review Workspace
- administrator-only list, create, and resolution APIs
- focused contract and route tests

## Routes

- `GET /api/v1/analytic-review/conflicts`
- `POST /api/v1/analytic-review/conflicts`
- `POST /api/v1/analytic-review/conflicts/<conflict_id>/resolution`

## Boundaries

No claim, evidence, observation, dossier, confidence, connector, or schema mutation is performed.

## Next action

Validate v30.3 and proceed to v30.4 Confidence Model and Explainability.
