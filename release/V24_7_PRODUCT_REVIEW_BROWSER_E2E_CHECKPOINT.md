# v24.7 Product Review and Browser E2E Checkpoint

Validates the complete portfolio journey and closes v24 before v25 begins.

The checkpoint covers:

- Portfolio Operations Dashboard
- Case Status and Stage Overview
- Workload and Assignment Monitoring
- Blocked and Overdue Case Queue
- Supervisor Escalation Controls
- Operational Metrics and Throughput
- Portfolio History and Audit
- final authenticated product-review checkpoint

Static product review verifies all v24.0 through v24.6 modules, browser assets, release notes, required routes, duplicate-route absence, and migration absence.

The browser journey validates:

- portfolio dashboard rendering
- stage-overview rendering and API
- workload-monitoring rendering and API
- blocked/overdue queue rendering and API
- supervisor escalation page
- immutable escalation, acknowledgement, reassignment, and resolution APIs
- operational metrics rendering and API
- portfolio history rendering and API
- final product-checkpoint readiness

Run:

```bash
python3 scripts/run_v24_7_portfolio_browser_e2e.py
```

The runner writes `reports/v24_7_portfolio_browser_e2e.json` and exits nonzero when any browser checkpoint fails.

The checkpoint is read-only. It creates no checkpoint record, mutates no portfolio, stage, assignment, blocker, overdue, escalation, metrics, or history source data, and introduces no migration.

A passing focused suite, browser report, and full regression suite closes v24 and authorizes the start of v25 Cross-Case Intelligence.
