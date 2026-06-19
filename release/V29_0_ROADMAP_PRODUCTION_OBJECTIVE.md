# v29.0 Roadmap and Production Objective

## Program title

**v29 — Connector and Collection Operations**

## Production objective

Operationalize repeatable, authorized, observable ingestion into the existing SOCMINT intelligence spine without turning the product into a connector zoo or a generic mega-platform.

The production path remains:

`case → entity → raw evidence → observation → corroboration → confidence → human review → dossier/report export`

Every v29 capability must prove that it improves this path. Connectors are subordinate collection mechanisms, not the organizing architecture.

## Repair-first directive

v29 starts with stabilization and control before adding collection breadth.

The first priority is to make the existing collection and connector surface understandable, authorized, deterministic, recoverable, and auditable. New connector types are out of scope until the current collection path has explicit contracts, observable state, retry boundaries, provenance, and operator review.

## Primary v29.0 objective

Create a **Collection Operations Workspace** that gives an operator a single read-only view of:

- configured collection sources and connector definitions
- authorization and scope metadata
- queued, running, completed, failed, blocked, and stale work
- source-to-case and source-to-entity bindings
- raw-artifact and observation output counts
- provenance and chain-of-custody completeness
- retry eligibility and failure classification
- connector trust and evidence contribution
- human-review requirements
- collection blockers and next actions

The v29.0 workspace must not execute collection, mutate jobs, retry work, rotate credentials, alter case access, or rewrite evidence. It is the production-baseline and repair map for later v29 slices.

## Success criteria

v29 is successful only when an authorized operator can answer, from product state rather than logs or manual inspection:

1. What collection work exists?
2. Who or what authorized it?
3. Which case, entity, seed, or source does it belong to?
4. What state is it in now?
5. What evidence and observations did it produce?
6. Was provenance preserved?
7. Did it fail, stall, duplicate, or exceed scope?
8. Is retry safe and idempotent?
9. Does the output improve the dossier or only create noise?
10. What human action is required next?

## Non-goals

v29 must not:

- become a broad connector marketplace
- add dozens of tools without dossier value
- bypass existing case-access policy
- permit unaudited collection execution
- store or expose secret values in events or APIs
- rewrite original evidence or provenance
- merge collection, analysis, and adjudication into one opaque action
- introduce paid APIs merely for breadth
- position the product as a generic enterprise mega-platform
- add graph or infrastructure complexity that is not required by the collection workflow

## Production invariants

Every v29 slice must preserve:

- explicit actor, reason, scope, and authorization binding
- append-only collection and operator history
- immutable raw evidence
- deterministic IDs and SHA-256 bindings where applicable
- idempotent retry contracts
- explicit failure classification
- no secret-value exposure
- no implicit case-access expansion
- no connector execution from read-only views
- human review before consequential downstream use
- no schema migration unless a concrete production gap requires one and the migration is separately justified

## Roadmap

### v29.0 — Collection Operations Workspace

Read-only collection control plane and production baseline.

Deliverables:

- collection inventory
- work-state summary
- source/case/entity bindings
- output and provenance summary
- stale, failed, duplicate, and scope findings
- retry eligibility projection
- dossier-value contribution summary
- no execution or mutation

### v29.1 — Collection Job Contract and State Machine

Define one authoritative collection-job contract and lifecycle.

Target states:

- drafted
- authorized
- queued
- running
- completed
- failed
- blocked
- cancelled
- superseded

Required contracts:

- state-transition rules
- idempotency key
- attempt number
- authorization binding
- case/entity/source binding
- failure category
- retry eligibility
- immutable attempt history

### v29.2 — Authorization, Scope, and Collection Policy

Bind every collection attempt to explicit authority and collection scope.

Deliverables:

- permitted source classes
- jurisdiction and policy metadata
- case and entity scope
- operator authorization
- collection-purpose binding
- deny and exclusion rules
- expiry and review dates
- policy evaluation before queueing

### v29.3 — Connector Normalization and Adapter Contract

Normalize existing connectors behind a narrow adapter contract.

Each connector must expose:

- capability declaration
- input schema
- output schema
- authorization requirements
- rate-limit metadata
- deterministic error classes
- provenance fields
- health status
- dossier-value declaration

No connector is added solely for breadth.

### v29.4 — Evidence-Safe Ingestion and Provenance

Ensure collection output enters the evidence spine safely.

Deliverables:

- immutable raw artifact registration
- content hash and acquisition hash
- source and acquisition timestamps
- collection-attempt binding
- observation derivation
- duplicate detection
- chain-of-custody completeness checks
- quarantine and rejection states

### v29.5 — Retry, Recovery, and Operator Intervention

Add controlled recovery without hidden automation.

Deliverables:

- retry eligibility rules
- safe retry action
- duplicate-attempt prevention
- backoff and rate-limit handling
- operator hold and resume
- partial-output handling
- recovery reason and confirmation
- immutable remediation history

### v29.6 — Collection Quality, Trust, and Dossier Contribution

Measure whether collection improves investigations.

Deliverables:

- connector trust summary
- evidence quality checks
- observation yield
- corroboration contribution
- confidence impact
- duplicate/noise ratio
- unresolved provenance findings
- dossier contribution scorecard
- human-review queue

### v29.7 — Product Review and Browser E2E Checkpoint

Validate and close the complete v29 collection journey.

Browser journey:

- collection operations workspace
- job lifecycle
- authorization and scope review
- connector normalization
- evidence-safe ingestion
- retry and recovery
- quality and dossier contribution
- final checkpoint

Closure contract:

- focused tests pass
- v29 regression tests pass
- full suite passes
- browser E2E failed count is zero
- `v29_closed: true`
- `next_action: begin_v30`

## Delivery sequence

The implementation order is fixed:

1. planning and baseline
2. read-only workspace
3. state and authorization contracts
4. normalized connector interface
5. evidence-safe ingestion
6. controlled recovery
7. quality and dossier-value validation
8. browser and full-suite closure

## v29.0 entry gate

No runtime code should be added until this roadmap and production objective are accepted as the v29 baseline.

## v29.0 exit gate

The first code slice may begin only when it can be implemented as a read-only workspace over existing records, with no connector execution, no job mutation, no secret exposure, no case-access change, and no migration unless a concrete data gap is proven.
