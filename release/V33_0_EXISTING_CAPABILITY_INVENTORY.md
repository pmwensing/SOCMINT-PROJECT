# v33.0 — Existing Capability Inventory

v33 composes existing capabilities. It does not replace them.

## Authoritative v32 governance services

- audience and recipient contracts
- dissemination package assembly
- authorization, policy, and release decisions
- delivery attempt and receipt ledger
- recipient feedback and correction intake
- recall, retention, and lifecycle history
- v32 product-review and browser E2E checkpoint

## Existing case and dashboard capabilities to reuse

- authenticated Flask dashboard and administrator session controls
- existing case identifiers, case-scoped routes, and case access checks
- existing command-center and workspace navigation patterns
- current templates, API response conventions, AuditLog persistence, and deterministic hashing utilities

## Proven gap

The repository has complete v32 backend contracts but no single case-centric operator surface that summarizes all dissemination-governance state and guides safe actions across the full lifecycle.

## Non-goals

- no parallel governance database or service family
- no replacement for v32 APIs
- no automatic authorization, delivery, recall, or retention execution
- no mutation of immutable publications or historical evidence
- no raw endpoint, credential, or contact-secret exposure
- no new connector family without a proven gap
- no migration without a proven storage requirement
