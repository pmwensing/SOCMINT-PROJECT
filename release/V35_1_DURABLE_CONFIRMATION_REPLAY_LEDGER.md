# v35.1 — Durable Confirmation and Replay Ledger

## Purpose

Add durable, reviewable state management to the existing human-confirmed governance workflow while retaining the established domain-service boundaries.

## Delivered

- authoritative `governance_executions` current-state table introduced by Alembic revision `0019_v35_1_governance_executions`
- deterministic execution identifiers bound to confirmation digest, case, governance action, and registered service
- database uniqueness for both execution identity and consumed confirmation digest
- append-only transition events retained in `audit_logs`
- canonical states: `pending`, `running`, `succeeded`, `failed`, `uncertain`, and `reconciled`
- integer `state_version` for optimistic compare-and-swap transitions
- current-state update and audit event committed in one database transaction
- durable replay detection for simultaneous duplicate creation
- explicit transition rules preventing backward movement and silent replay
- durable history snapshots with actor, reason, timestamp, result metadata, and consistency proof
- integration with the existing confirmed-action workflow

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

## Processing order

```text
validate human confirmation
-> atomically create pending state
-> prepare registered service arguments
-> atomically transition pending to running
-> perform the confirmed service operation
-> persist record identifiers and execution audit
-> atomically transition running to succeeded
-> refresh the canonical workspace
```

## Failure classification

- failures before the service operation transition `pending -> failed`
- exceptions or lost responses after the service operation begins transition `running -> uncertain`
- failures persisting a completed result also transition `running -> uncertain`
- duplicate confirmations are rejected before another operation begins
- neither `failed` nor `uncertain` can transition back to `running`
- no automatic retry is authorized

## Concurrency guarantees

- simultaneous creates are serialized by database uniqueness; exactly one `pending` record and one creation event survive
- transitions use a conditional database update matching `execution_id`, `current_state`, and `state_version`
- a zero-row conditional update is treated as `ExecutionStateConflict`
- the authoritative state update and corresponding append-only event are committed or rolled back together
- SQL compatibility is checked for SQLite and PostgreSQL
- an optional PostgreSQL runtime contract test runs when `SOCMINT_TEST_POSTGRES_URL` is configured

## Preserved controls

- no automatic retries
- no silent replay of uncertain work
- no confirmation bypass
- no generic workflow engine
- no replacement of established domain services
- no destructive remediation
- no access-scope change

## Validation coverage

- deterministic pending-state creation
- simultaneous duplicate creation
- persistence across database reconfiguration
- canonical forward transitions
- stale expected-state and stale-version conflicts
- conflicting worker transitions
- authoritative-state and append-only-ledger consistency
- rejection of backward transitions
- rejection of retry from `failed` and `uncertain`
- pre-operation failure classification
- uncertain-outcome classification after processing begins
- duplicate rejection after an uncertain outcome
- SQLite and PostgreSQL statement compatibility
- Alembic migration smoke through revision `0019_v35_1_governance_executions`

## Next program slice

v35.2 will add a versioned service signature and input-schema registry. It must validate action-specific inputs before `pending -> running` while preserving v35.1 identity, replay, and transition guarantees.
