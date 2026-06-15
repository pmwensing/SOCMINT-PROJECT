# v24.0 Portfolio Operations Dashboard

Introduces a read-only manager-facing portfolio dashboard built from existing case-targeted audit events rather than a duplicate case table.

The dashboard summarizes active, blocked, delivered, closed, archived, reopened, and unstarted cases. It shows the latest activity, latest actor, derived lifecycle stage, current blockers, and direct navigation to case review, dossier assembly, release, closure, closure history, and delivery workspaces.

Configured cases with no activity may be supplied through `SOCMINT_PORTFOLIO_CASES` as JSON or a comma-separated list, allowing unstarted cases to appear without creating new records.

Routes:

- `GET /portfolio-operations`
- `GET /api/v1/portfolio-operations`

v24.0 is read-only. Case status normalization, workload and assignment monitoring, blocked and overdue queues, supervisor escalation, operational metrics, and portfolio history are added in v24.1 through v24.6.

No source record is mutated, no portfolio record is created, and no migration is introduced.
