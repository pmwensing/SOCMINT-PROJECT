# v35.5 Execution Recovery Observability

## Objective

Add a read-only administrator observability layer over durable governance executions so stalled, uncertain, failed and reconciled outcomes can be assessed without creating any new execution, retry, reconciliation, or delegate path.

## Delivered read models

### Recovery summary

Aggregates executions by durable state, governance action and family, delegate service, case, deterministic integrity classification, result-envelope presence, and age bucket.

### Attention queue

Surfaces old pending or running executions, uncertain executions awaiting reconciliation, undocumented failed executions, result-envelope mismatches, missing durable invocation bindings, and inconsistent ledger histories. The queue excludes execution history, confirmation digests, and submitted operator values.

### Reconciliation closure view

For reconciled executions, exposes the durable invocation binding, uncertain-outcome reference, authoritative result envelope, reconciliation metadata, update time, and elapsed seconds from uncertainty to reconciliation without offering a write action.

## Interfaces

- `GET /api/v1/dissemination-governance/executions/recovery-summary`
- `GET /api/v1/dissemination-governance/executions/attention`
- `GET /api/v1/dissemination-governance/executions/reconciled`
- `GET /dissemination-governance/execution-recovery-observability`

All interfaces are administrator-only and read-only.

## Integrity classifications

- `healthy` — durable state, ledger, bindings, and result-envelope expectations agree;
- `attention` — an age or documentation threshold is exceeded;
- `integrity_alert` — durable records disagree or required bindings are missing;
- `reconciliation_pending` — state is uncertain and no authoritative result envelope exists;
- `reconciled` — state and authoritative result envelope agree.

Wall-clock age is diagnostic only and never treated as proof of external failure.

## Preserved safety boundary

v35.5 does not invoke or resolve delegates; create, claim, transition, or reconcile executions; mutate result envelopes; expose write controls or sensitive operator inputs; add migrations; or create a competing state store.

## Verification

Implemented coverage includes deterministic classification tests, age-bucket tests, integrity precedence, administrator authorization, GET-only routes, non-disclosure, closure elapsed-time calculation, static no-write import checks, browser E2E proving the absence of forms and write controls, and inclusion in the focused v32-through-v35 browser workflow.

Full CI, PostgreSQL coverage, migration smoke, backup/restore, production boot, legacy verification, and full-container verification remain authoritative release gates.
