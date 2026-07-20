# v35.5 Execution Recovery Observability

## Objective

Add a read-only administrator observability layer over durable governance executions so stalled, uncertain, failed and reconciled outcomes can be assessed without creating any new execution, retry, reconciliation, or delegate path.

## Delivered read models

### Recovery summary

Aggregates executions by:

- durable state;
- governance action and action family;
- delegate service;
- case ID;
- deterministic integrity classification;
- result-envelope presence;
- age bucket.

### Attention queue

Surfaces executions requiring operator attention, including:

- `pending` executions older than the configured pending threshold;
- `running` executions older than the configured invocation threshold;
- `uncertain` executions awaiting reconciliation;
- failed executions with no documented terminal reason;
- terminal-state and result-envelope mismatches;
- missing confirmation-issuance or contract-validation bindings;
- inconsistent ledger histories.

The queue excludes execution history, confirmation digests, and submitted operator values.

### Reconciliation closure view

For reconciled executions, exposes the durable invocation binding, uncertain-outcome reference, authoritative result envelope, reconciliation metadata, and update time without offering a write action.

## Interfaces

- `GET /api/v1/dissemination-governance/executions/recovery-summary`
- `GET /api/v1/dissemination-governance/executions/attention`
- `GET /api/v1/dissemination-governance/executions/reconciled`
- `GET /dissemination-governance/execution-recovery-observability`

All interfaces are administrator-only and read-only.

## Integrity classifications

Each execution receives deterministic observations rather than inferred outcomes:

- `healthy` — durable state, ledger, bindings, and result-envelope expectations agree;
- `attention` — an age or documentation threshold is exceeded;
- `integrity_alert` — durable records disagree or required bindings are missing;
- `reconciliation_pending` — state is uncertain and no authoritative result envelope exists;
- `reconciled` — state and authoritative result envelope agree.

Wall-clock age is explicitly marked as diagnostic only and never treated as proof of external failure.

## Preserved safety boundary

v35.5 does not:

- invoke or resolve a delegate service;
- create, claim, transition, or reconcile a governance execution;
- mutate an authoritative result envelope;
- expose retry, automatic-retry, reconcile, or delegate controls;
- expose sensitive operator-submitted values in the attention queue;
- add a migration or competing state store.

## Verification

Implemented coverage includes:

- deterministic age-bucket and classification tests;
- integrity-alert precedence tests;
- administrator authorization and GET-only route tests;
- attention-queue non-disclosure tests;
- static checks proving no transition, reconciliation, result-commit, or delegate-resolution imports;
- browser E2E proving the absence of forms and write controls;
- inclusion in the focused v32-through-v35 browser workflow.

Full CI, PostgreSQL coverage, migration smoke, backup/restore, production boot, legacy verification, and full-container verification remain authoritative release gates.
