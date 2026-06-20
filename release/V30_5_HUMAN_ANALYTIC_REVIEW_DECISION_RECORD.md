# v30.5 — Human Analytic Review and Decision Record

## Objective

Require an explicit human decision before consequential use of a corroboration claim, while preserving every prior review and keeping dossier contribution as a separate later gate.

## Delivered

- append-only human analytic review records
- decisions: approved, held, rejected, and needs revision
- deterministic bindings to the claim, latest confidence assessment, source linkages, and conflict state
- approval gate requiring substantial confidence and no unresolved analytic conflict
- explicit rationale, findings, administrative reason, and confirmation
- reassessment records that supersede but never erase prior review decisions
- current-decision and full-history inventories
- human-review summary and waiting-review findings in the Analytic Review Workspace
- administrator-only list and create APIs
- focused contract and route tests

## Routes

- `GET /api/v1/analytic-review/human-reviews`
- `GET /api/v1/analytic-review/claims/<claim_id>/human-reviews`
- `POST /api/v1/analytic-review/claims/<claim_id>/human-reviews`

## Boundaries

Human approval permits consequential analytic use but does not authorize dossier contribution. No claim, confidence, evidence, observation, dossier, connector, or schema mutation is performed.

## Next action

Validate v30.5 and proceed to v30.6 Dossier Contribution and Reassessment.
