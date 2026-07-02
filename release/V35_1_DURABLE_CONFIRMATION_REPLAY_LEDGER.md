# v35.1 — Durable Confirmation and Replay Ledger

## Purpose

Create the first durable orchestration layer above the hardened v34.8 human-confirmed execution surface without replacing v32 domain services or enabling automatic action execution.

## Implemented in this slice

- deterministic execution identifiers bound to confirmation digest, case, governance action, and authoritative delegate
- append-only execution events stored in the existing `audit_logs` table
- canonical execution states:
  - `pending`
  - `running`
  - `succeeded`
  - `failed`
  - `uncertain`
  - `reconciled`
- optimistic expected-state checks before every transition
- durable replay detection for duplicate execution creation
- explicit transition rules that prevent backward movement and silent replay
- durable history snapshots with actor, reason, timestamp, and optional result metadata

## State machine

```text
pending -> running -> succeeded -> reconciled
    |         |            \
    |         +-> failed ----> reconciled
    |         +-> uncertain --> reconciled
    +-> failed -------------> reconciled
    +-> uncertain ----------> reconciled
```

No state transitions back to `pending` or `running` are permitted from `failed`, `uncertain`, `succeeded`, or `reconciled`.

## Preserved controls

- no automatic retries
- no silent replay of uncertain work
- no confirmation bypass
- no route or browser action in this initial implementation
- no replacement of authoritative v32 services
- no generic workflow engine
- no destructive remediation
- no access-scope change
- no schema migration; existing append-only `AuditLog` storage is reused

## Known follow-up boundary

This service establishes durable state and transition invariants but is not yet wired into the v34 execution route. Integration must preserve the exact v34 confirmation contract and must create `pending` state before invoking an authoritative delegate.

## Validation

Focused tests cover:

- deterministic pending-state creation
- duplicate replay rejection without duplicate events
- persistence across database reconfiguration
- canonical forward transitions
- stale expected-state conflicts
- rejection of backward transitions
- rejection of automatic retry from `failed` and `uncertain`

## Next action

Integrate the ledger with the v34 confirmed-execution path so every accepted confirmation receives durable `pending` state before exactly one authoritative delegate invocation.
