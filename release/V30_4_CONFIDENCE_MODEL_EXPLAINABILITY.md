# v30.4 — Confidence Model and Explainability

## Objective

Create bounded, explainable confidence assessments for proposed corroboration claims using visible source, conflict, and limitation inputs without representing confidence as truth.

## Delivered

- append-only analytic confidence assessments
- deterministic claim, linkage, conflict, and explanation bindings
- visible scoring components for source linkage, artifact diversity, observation support, resolved conflicts, unresolved-conflict penalties, and declared limitations
- confidence bands: insufficient, limited, moderate, and substantial
- hard score cap of 79 pending later human review
- explicit methodology, limitations, reasons, and unresolved conflict IDs
- claim linkage required before assessment
- confidence inventory and missing-assessment findings in the Analytic Review Workspace
- administrator-only list and create APIs
- focused contract and route tests

## Routes

- `GET /api/v1/analytic-review/claims/<claim_id>/confidence-assessments`
- `POST /api/v1/analytic-review/claims/<claim_id>/confidence-assessments`

## Boundaries

Confidence is not truth. No high-confidence state, human-review completion, claim mutation, dossier mutation, connector execution, or schema migration is performed.

## Next action

Validate v30.4 and proceed to v30.5 Human Analytic Review and Decision Record.
