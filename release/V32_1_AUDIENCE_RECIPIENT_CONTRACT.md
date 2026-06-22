# v32.1 — Audience and Recipient Contract

## Objective

Record case-scoped dissemination audiences and recipient identities as append-only contracts without authorizing delivery or storing contact secrets.

## Delivered

- deterministic audience contract identifiers and SHA-256 hashes
- append-only contract history in the audit ledger
- case-scoped audience definitions
- recipient identity, organization, role, type, purpose, classification ceiling, and allowed-channel declarations
- duplicate-recipient detection
- classification compatibility checks
- supported-channel validation using existing v22 delivery channels
- explicit operator confirmation and administrative reason
- administrator-only APIs
- focused model and route tests

## Routes

- `GET /api/v1/dissemination-governance/audience-contracts`
- `GET /api/v1/dissemination-governance/audience-contracts/<audience_contract_id>`
- `GET /api/v1/dissemination-governance/cases/<case_id>/audience-contracts`
- `POST /api/v1/dissemination-governance/cases/<case_id>/audience-contracts`

## Safety boundaries

- contracts are recorded as `proposed`
- recipients remain `not_authorized`
- no dissemination package is assembled
- no delivery or external transmission occurs
- no contact secret or endpoint is stored
- no published revision or delivery history is mutated
- no database migration

## Next action

`implement_v32_2_dissemination_package_assembly`
