# v35.5 Execution Recovery Observability

## Objective

Add a read-only administrator observability layer over durable governance executions so stalled, uncertain, failed and reconciled outcomes can be assessed without creating any new execution, retry, reconciliation, or delegate path.

## Delivered

- deterministic recovery summary grouped by state, action, action family, delegate, case, integrity, result-envelope presence, and age;
- attention queue for old pending/running work, uncertain work, missing bindings, ledger mismatches, result-envelope mismatches, and undocumented failures;
- reconciliation closure view with invocation and uncertain-outcome bindings, result envelope, operator metadata, and uncertainty-to-reconciliation elapsed seconds;
- administrator-only read APIs and operator page;
- explicit `healthy`, `attention`, `integrity_alert`, `reconciliation_pending`, and `reconciled` classifications;
- diagnostic-only age handling;
- no history, confirmation digest, or submitted operator-value disclosure in the attention queue;
- browser proof that no forms, retry controls, reconciliation controls, or delegate controls exist.

## Interfaces

- `GET /api/v1/dissemination-governance/executions/recovery-summary`
- `GET /api/v1/dissemination-governance/executions/attention`
- `GET /api/v1/dissemination-governance/executions/reconciled`
- `GET /dissemination-governance/execution-recovery-observability`

## Preserved safety boundary

v35.5 does not invoke or resolve delegates; create, claim, transition, or reconcile executions; mutate result envelopes; expose write controls or sensitive operator inputs; add migrations; or create a competing state store.

## Verification

Focused tests cover deterministic classifications, age buckets, integrity precedence, administrator authorization, GET-only routing, non-disclosure, closure elapsed-time calculation, and static no-write imports. Selenium E2E verifies the read-only workspace and absence of write controls. The existing CI, Full Verification, legacy verification, PostgreSQL, migration, backup/restore, production boot, and container gates remain authoritative and must pass on the final head before merge.
