# v33.3 — Audience, Package, and Authorization Panels

## Objective

Expose audience, dissemination-package, and authorization state as deterministic, case-scoped, read-only panel models composed from the canonical v33.1 snapshot, v33.2 action queue, and authoritative v32 histories.

## Delivered

- combined audience, package, and authorization panel payload
- individual panel lookup
- current record and full case-scoped history for each panel
- panel-specific blockers and available action-queue entries
- audience recipient-count summary
- package assembly and active-package summary
- authorization approval, denial, hold, and delivery-eligibility summary
- deterministic panel and combined-panel SHA-256 values
- recursive removal of endpoint, contact-secret, credential, password, and token fields
- administrator-only panel APIs
- focused model and route tests

## Routes

- `GET /api/v1/dissemination-governance/cases/<case_id>/audience-package-authorization-panels`
- `GET /api/v1/dissemination-governance/cases/<case_id>/governance-panels/<panel_name>`

Supported individual panel names:

- `audience`
- `package`
- `authorization`

## Safety boundaries

- read-only workflow composition
- no panel action execution
- no new governance backend
- no source-record persistence or mutation
- no bypass of v32 human confirmation or policy controls
- no endpoint, credential, token, password, or contact-secret rendering
- no case-access change
- no database migration

## Next action

`implement_v33_4_delivery_receipt_and_feedback_panels`
