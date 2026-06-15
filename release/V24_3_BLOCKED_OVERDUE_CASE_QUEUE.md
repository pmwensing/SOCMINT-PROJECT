# v24.3 Blocked and Overdue Case Queue

Combines portfolio blockers, stage age, assignment age, configurable overdue thresholds, severity, owner and reviewer, review state, next expected action, and direct remediation links into one prioritized supervisor queue.

Default thresholds:

- stage overdue: 72 hours
- assignment overdue: 48 hours

They may be overridden with `SOCMINT_STAGE_OVERDUE_HOURS` and `SOCMINT_ASSIGNMENT_OVERDUE_HOURS`.

Severity is normalized as critical, high, medium, or low. Blocked cases with extreme age or both stage and assignment overdue are critical. Blocked cases or cases overdue in both dimensions are high. A single overdue threshold is medium.

The queue is ordered by severity, total overdue duration, and case ID. Each entry exposes current stage, stage age, assignment age, overdue duration, blocking reason, owner, assigned reviewers, active assignment count, review states, next expected action, and direct remediation links to case review, dossier assembly, closure, history, reviewer assignments, and the supervisor queue.

Routes:

- `GET /portfolio-operations`
- `GET /api/v1/portfolio-operations`
- `GET /api/v1/portfolio-operations/blocked-overdue`

v24.3 is read-only. It derives the prioritized supervisor queue from existing portfolio, stage, and assignment data, creates no queue record, mutates no case or assignment event, and introduces no migration.
