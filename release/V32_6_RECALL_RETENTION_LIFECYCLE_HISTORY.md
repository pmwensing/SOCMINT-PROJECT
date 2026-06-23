# v32.6 — Recall, Retention, and Lifecycle History

## Objective

Record human recall and retention decisions as deterministic append-only lifecycle events while preserving every prior publication, package, authorization, delivery attempt, receipt, feedback item, and correction record.

## Delivered

- append-only recall decision history
- recall initiation, confirmation, denial, and lift state transitions
- recall decisions bound to an explicit v32.5 recall-review correction intake
- deterministic correction, package, and published-revision recall bindings
- explicit future-delivery blocking state for pending and confirmed recalls
- recipient-notice requirements without automatic notice transmission
- append-only case-scoped retention decisions
- retain, legal-hold, archive, and expiry-review dispositions
- explicit retention policy identifiers, reasons, and review dates
- destructive retention action prohibited
- consolidated case-scoped lifecycle history across v32.1 through v32.6
- deterministic lifecycle snapshots with stage counts, recall state, and retention state
- administrator-only recall, retention, and lifecycle APIs
- focused model and route tests

## Recall routes

- `GET /api/v1/dissemination-governance/recall-decisions`
- `GET /api/v1/dissemination-governance/recall-decisions/<recall_id>`
- `GET /api/v1/dissemination-governance/packages/<package_id>/recall-decisions`
- `GET /api/v1/dissemination-governance/correction-intakes/<correction_id>/recall-decisions`
- `POST /api/v1/dissemination-governance/correction-intakes/<correction_id>/recall-decisions`

## Retention and lifecycle routes

- `GET /api/v1/dissemination-governance/retention-decisions`
- `GET /api/v1/dissemination-governance/retention-decisions/<retention_id>`
- `GET /api/v1/dissemination-governance/cases/<case_id>/retention-decisions`
- `POST /api/v1/dissemination-governance/cases/<case_id>/retention-decisions`
- `GET /api/v1/dissemination-governance/lifecycle-history`
- `GET /api/v1/dissemination-governance/cases/<case_id>/lifecycle-history`

## Safety boundaries

- recall never deletes or rewrites historical evidence
- retention decisions do not execute destructive deletion
- no source intelligence, publication, package, authorization, delivery, feedback, or correction mutation
- no automatic external transmission or recall notice delivery
- no contact secret storage
- no case-access change
- no database migration

## Next action

`implement_v32_7_product_review_and_browser_e2e_checkpoint`
