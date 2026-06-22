# v31.6 — Supersession and Revision History

## Objective

Preserve immutable publication history while allowing an explicitly published successor revision to supersede an earlier revision for the same case.

## Delivered

- append-only supersession records
- deterministic supersession identifiers and SHA-256 hashes
- immutable predecessor/successor bindings
- same-case enforcement
- self-supersession prevention
- one successor per predecessor
- one predecessor per successor
- case-level revision history with active and superseded status
- explicit confirmation, reason, note, and actor identity
- administrator-only supersession and revision-history APIs
- focused model and route tests

## Routes

- `GET /api/v1/publication-review/supersessions`
- `POST /api/v1/publication-review/supersessions`
- `GET /api/v1/publication-review/cases/<case_id>/revision-history`

## Safety boundaries

- predecessor and successor revisions remain immutable
- historical publication records are never deleted
- no published content is rewritten
- no external transmission
- no database migration

## Next action

Implement v31.7 Product Review and Browser E2E.
