# v30.1 — Corroboration Claim Contract

## Objective

Introduce an append-only analytic claim contract that binds a proposed claim to case, entity, purpose, and immutable source references without assigning truth, confidence, or dossier eligibility.

## Delivered

- deterministic corroboration claim identifiers
- explicit case and entity bindings
- normalized claim type and value
- analytic purpose and administrative reason requirements
- one or more typed source references with deterministic binding hash
- append-only AuditLog persistence
- duplicate claim blocking
- proposed and withdrawn claim states
- withdrawal as a separate append-only state event
- claim inventory in the Analytic Review Workspace
- administrator-only list, create, and state-transition APIs
- focused contract and route tests

## API routes

- `GET /api/v1/analytic-review/claims`
- `POST /api/v1/analytic-review/claims`
- `POST /api/v1/analytic-review/claims/<claim_id>/state`

## Safety boundaries

- no truth assignment
- no confidence assignment
- no human-review completion
- no evidence or observation mutation
- no dossier mutation
- no connector execution
- no database migration

Only withdrawal is permitted as a v30.1 state transition. Approval, confidence, contradiction resolution, and dossier contribution remain reserved for later v30 slices.

## Next action

Validate focused and full regression gates, then implement v30.2 Evidence and Observation Linkage.
