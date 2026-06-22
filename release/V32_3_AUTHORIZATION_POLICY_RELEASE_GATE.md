# v32.3 — Authorization, Policy, and Release Gate

## Objective

Require an explicit human authorization decision and policy review before any dissemination package can proceed to delivery-attempt creation.

## Delivered

- append-only authorization decision history
- approve, deny, and hold decisions
- explicit administrator identity, reason, and confirmation
- deterministic authorization decision identifiers and hashes
- package, source-binding, manifest, and payload integrity verification
- audience classification, purpose, recipient-channel, and unresolved-endpoint policy checks
- immutable authorization binding across package, publication, audience, manifest, and payload hashes
- administrator-only decision APIs
- focused model and route tests

## Routes

- `GET /api/v1/dissemination-governance/authorization-decisions`
- `GET /api/v1/dissemination-governance/authorization-decisions/<authorization_decision_id>`
- `GET /api/v1/dissemination-governance/packages/<dissemination_package_id>/authorization-decisions`
- `POST /api/v1/dissemination-governance/packages/<dissemination_package_id>/authorization-decisions`

## State outcomes

- `approve` -> `approved_for_delivery_attempt`
- `deny` -> `release_denied`
- `hold` -> `release_held`

## Safety boundaries

- no delivery endpoint resolution
- no delivery attempt creation
- no external transmission
- no contact secret storage
- no package, publication, audience-contract, or delivery-history mutation
- no database migration

## Next action

`implement_v32_4_delivery_attempt_and_receipt_ledger`
