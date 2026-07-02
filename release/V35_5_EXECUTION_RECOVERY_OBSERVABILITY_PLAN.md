# v35.5 Execution Recovery Observability

## Objective

Add a read-only administrator observability layer over durable governance executions so stalled, uncertain, failed and reconciled outcomes can be assessed without creating any new execution or retry path.

## Planned read models

### Recovery summary

Aggregate executions by:

- durable state;
- governance action and action family;
- delegate service;
- case ID;
- ledger-consistency status;
- presence of an authoritative result envelope;
- age bucket.

### Attention queue

Surface executions requiring operator attention, including:

- `pending` executions older than the configured pending threshold;
- `running` executions older than the configured invocation threshold;
- `uncertain` executions awaiting reconciliation;
- failed executions with no documented terminal reason;
- terminal state and result-envelope mismatches;
- missing confirmation-issuance or contract-validation bindings;
- inconsistent ledger histories.

### Reconciliation closure view

For reconciled executions, show:

- original invocation binding;
- uncertain event and recorded outcome reference;
- final authoritative record IDs;
- reconciliation reason and evidence references;
- original and reconciling actors;
- result-envelope digest;
- elapsed time from uncertainty to reconciliation.

## Planned interfaces

- `GET /api/v1/dissemination-governance/executions/recovery-summary`
- `GET /api/v1/dissemination-governance/executions/attention`
- `GET /api/v1/dissemination-governance/executions/reconciled`
- `/dissemination-governance/execution-recovery-observability`

All interfaces are administrator-only and read-only.

## Safety boundary

v35.5 must not:

- invoke or resolve a delegate service;
- create, claim or transition a governance execution;
- reconcile an execution;
- mutate an authoritative result envelope;
- expose a retry or automatic-retry control;
- expose sensitive operator-submitted values in diagnostics;
- treat wall-clock age alone as proof of an external failure.

## Integrity classifications

Each execution receives deterministic observations rather than inferred outcomes:

- `healthy` — durable state, ledger and result envelope agree;
- `attention` — an age or documentation threshold is exceeded;
- `integrity_alert` — durable records disagree or required bindings are missing;
- `reconciliation_pending` — state is uncertain and no result envelope exists;
- `reconciled` — state and authoritative result envelope agree.

## Verification gates

- deterministic age-bucket and classification tests;
- no write-capable imports in observability services or routes;
- administrator authorization and non-disclosure tests;
- SQLite and PostgreSQL query coverage;
- browser verification proving no retry, reconcile or delegate controls;
- full pytest and Ruff;
- migration smoke, backup/restore and production boot;
- legacy and full container verification.
