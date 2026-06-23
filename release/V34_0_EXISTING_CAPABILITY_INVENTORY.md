# v34.0 — Existing Capability Inventory

v34 composes existing capabilities rather than creating a parallel execution system.

## Authoritative v32 services to delegate to

- audience and recipient governance
- dissemination package assembly and revision
- policy, authorization, and release decisions
- delivery attempt, retry, and receipt ledger
- recipient feedback and correction intake
- recall, retention, and lifecycle transitions
- append-only audit and historical evidence records

## Canonical v33 operator surfaces to reuse

- case-centric governance snapshot
- action queue and blocker surface
- audience, package, and authorization panels
- delivery, receipt, feedback, and correction panels
- recall, retention, and lifecycle timeline
- integrated browser/API case workspace
- product-review route inventory and browser E2E checkpoint

## Existing platform capabilities to reuse

- authenticated Flask dashboard and administrator checks
- case identifiers and case-scoped route conventions
- current form, JSON response, and template patterns
- deterministic hashing and sanitization utilities
- AuditLog and authoritative domain histories
- existing CI, full verification, production smoke, and browser E2E workflows

## Implemented v34 composition layer

v34.1 adds deterministic action eligibility and delegate resolution over the canonical v33.2 action queue. The read model recognizes the eight supported governance actions, requires an exact authoritative delegate match, checks action-specific target identifiers, preserves explicit confirmation requirements, disables automatic execution, and emits deterministic resolution hashes.

The v34.1 API is administrator-only and read-only. It does not invoke delegates or mutate source records.

## Remaining gap

Operators still cannot review a canonical confirmation form, submit an idempotent confirmation, or invoke an authoritative service from the workspace. Those capabilities remain deferred to v34.2 and later slices.

## Non-goals

- no new transport implementation
- no replacement for v32 services
- no automatic queue-item execution
- no second governance or execution database
- no direct mutation of historical evidence
- no broad bulk-action framework
- no secret or endpoint exposure
- no migration without a proven storage requirement
