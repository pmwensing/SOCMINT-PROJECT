# v36.5 — Claim Verification and Alternative Ranking

## Objective

Assess proposed v30 claims through visible identity, source, directness, capture, temporal, independence, linkage, conflict, and limitation dimensions, then rank mutually exclusive alternatives without assigning truth or bypassing human review.

## Delivered

- deterministic append-only verification assessments over proposed v30 claims;
- required v30 evidence and observation linkage;
- claim-type-specific v36.1 source reliability;
- v36.4 exact-source-set independence context;
- direct verified control, reviewed candidate, or case-entity identity contexts;
- separate identity, source, directness, capture-integrity, temporal, independence, and linkage scores;
- unresolved-conflict and declared-limitation penalties;
- bounded insufficient, limited, moderate, and substantial bands;
- hard score cap of 79 before human review;
- deterministic alternative groups by case, entity, and claim type;
- live position, candidate count, unique-most-likely, and top-tie indicators;
- administrator-only inventory, detail, and assessment APIs;
- analytic-review route integration.

## Scoring model

- source reliability: 20%
- source directness: 20%
- identity context: 20%
- source independence: 15%
- capture integrity: 10%
- temporal relevance: 10%
- evidence/observation linkage: 5%
- unresolved conflicts: minus 15 each, capped at 30
- declared limitations: minus 5 each, capped at 20

A source lacking a reliability profile for the assessed claim type contributes zero for source reliability and directness. A source set lacking an exact v36.4 independence assessment contributes zero for independence.

## Routes

- `GET /api/v1/entity-accuracy/claim-verifications`
- `POST /api/v1/entity-accuracy/claims/<claim_id>/verification`
- `GET /api/v1/entity-accuracy/claims/<claim_id>/verification`

## Safety boundary

- confidence is not truth;
- ranking means most strongly supported among assessed alternatives, not fact;
- ties are explicitly visible and produce no unique most-likely result;
- human analytic review remains the v30.5 gate;
- dossier contribution remains the v30.6 gate;
- no claim, source, conflict, review, graph, or dossier mutation;
- no approval, truth, or dossier route is introduced.

## Verification

Focused coverage includes dimensional substantial scoring, conflict and limitation penalties, alternative ordering and top ties, unassessed independence, missing claim-type source profiles, reviewed-candidate restrictions, administrator routes, analytic-review registration, and absence of truth, approval, or dossier actions.

## Next action

Implement v36.6 Relationship and Timeline Verification with source-grounded event, report, capture, validity, and inference-warning contracts.
