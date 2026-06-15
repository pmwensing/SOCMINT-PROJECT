# v24.1 Case Status and Stage Overview

Normalizes every portfolio case into a single operational stage model:

- unstarted
- active
- closure review
- dossier exported
- delivered
- closed
- retention pending archive
- archived
- reopened

For every case, the overview exposes the current stage, prior stage, stage-entry timestamp, stage duration in seconds and hours, progress position and percentage, blocking reason, blocker sources, latest activity timestamp, transition history, and next expected action.

Blocked cases return `resolve_blocking_reason` as the next expected action. Operational cases receive the stage-specific next action, such as beginning review, completing analysis, recording closure, assigning retention, generating the archive package, monitoring retention, or resuming reopened operations.

Routes:

- `GET /portfolio-operations`
- `GET /api/v1/portfolio-operations`
- `GET /api/v1/portfolio-operations/stage-overview`

The stage overview is read-only. It derives status from existing case-targeted audit events, creates no stage record, mutates no source event, and introduces no migration.
