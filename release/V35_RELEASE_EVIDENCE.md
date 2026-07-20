# v35 Release Evidence

## Release identity

- Program: Durable Action Orchestration, Audit Traceability, and Operational Recovery
- Closure slice: v35.6
- Final runtime pull request: #289
- Final runtime validated head: `3916532caebf02ca9350ab098716215c83bf1b71`
- Final runtime squash merge commit: `f1b750241d03217aed0cb2a2fa255c7c9e5f37ee`
- Final runtime merged: 2026-07-20
- Rollback reference: parent of merge commit `f1b750241d03217aed0cb2a2fa255c7c9e5f37ee`

## Exact-head validation evidence

All required checks passed on the final v35.5 branch head before merge:

- CI run 4187 — success
- SOCMINT Full Verification run 1066 — success
- SOCMINT v12.10.19 Verify run 2399 — success
- SOCMINT v32.7 through v35.5 Browser E2E run 168 — success

CI included lint, the complete test suite, PostgreSQL schema upgrade and concurrency tests, publication browser regression, export-gate verification, Docker Compose validation, Alembic migration smoke, backup/restore smoke, production boot smoke, and dependency audit.

## Delivered durable controls

- one deterministic execution identity per issued confirmation;
- durable `pending`, `running`, `succeeded`, `failed`, `uncertain`, and `reconciled` states;
- versioned action contracts validated before execution state is created;
- authoritative v32 delegate selection from the existing registry;
- atomic result envelope, result audit, ledger event, and final-state commit;
- idempotent identical replay and rejection of conflicting replay;
- evidence-backed reconciliation of uncertain outcomes without delegate invocation;
- administrator-only recovery summaries, attention queues, and reconciliation closure views;
- explicit non-disclosure of operator-submitted values in diagnostics.

## Delivered operator routes

### Reconciliation

- `GET /api/v1/dissemination-governance/executions/uncertain`
- `GET /api/v1/dissemination-governance/executions/<execution_id>`
- `POST /api/v1/dissemination-governance/executions/<execution_id>/reconcile`
- `GET /dissemination-governance/execution-reconciliation`

### Recovery observability

- `GET /api/v1/dissemination-governance/executions/recovery-summary`
- `GET /api/v1/dissemination-governance/executions/attention`
- `GET /api/v1/dissemination-governance/executions/reconciled`
- `GET /dissemination-governance/execution-recovery-observability`

## Preserved controls

- v32 services remain authoritative.
- v34 human confirmation remains mandatory.
- Automatic retry remains disabled.
- Uncertain work is not silently replayed.
- Reconciliation cannot resolve or invoke a delegate.
- Recovery observability exposes no write controls.
- Historical audit and result records remain append-only.
- No generic orchestration platform or competing execution backend was introduced.

## Program disposition

v35 is closed. Runtime work continues under v36 only after the v36.0 planning and compatibility gate is merged.
