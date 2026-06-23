# v32.2 — Dissemination Package Assembly

## Objective

Assemble a deterministic, append-only dissemination package by binding one active immutable v31 published revision to one proposed v32.1 audience and recipient contract.

## Delivered

- deterministic dissemination package identifiers and SHA-256 hashes
- active published-revision enforcement
- same-case publication and audience binding
- immutable source binding across publication and audience hashes
- deterministic section manifest
- deterministic recipient manifest
- package payload snapshot containing published content, metadata, and provenance
- independent integrity hashes for source binding, manifest, and payload
- append-only package history in the audit ledger
- administrator-only package APIs
- focused model and route tests

## Routes

- `GET /api/v1/dissemination-governance/packages`
- `GET /api/v1/dissemination-governance/packages/<dissemination_package_id>`
- `GET /api/v1/dissemination-governance/cases/<case_id>/packages`
- `POST /api/v1/dissemination-governance/published-revisions/<published_revision_id>/audience-contracts/<audience_contract_id>/packages`

## Safety boundaries

- package state is `assembled_pending_authorization`
- recipients remain `not_authorized`
- no delivery endpoint is resolved
- no delivery attempt is created
- no external transmission occurs
- no contact secret is stored
- no published revision, audience contract, or delivery history is mutated
- no database migration

## Next action

`implement_v32_3_authorization_policy_and_release_gate`
