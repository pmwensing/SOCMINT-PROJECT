# v24.2 Workload and Assignment Monitoring

Aggregates existing reviewer and supervisor assignments from the persistent decision supervisor queue and reviewer work queues.

The monitoring surface reports active workload, assigned active work, unassigned work, reviewer totals, assignment age, review state counts, oldest and average assignment age, workload spread, workload imbalance, overloaded reviewers, and direct links into the existing reviewer and supervisor queues.

Routes:

- `GET /portfolio-operations`
- `GET /api/v1/portfolio-operations`
- `GET /api/v1/portfolio-operations/workload-monitoring`

The workload model treats `unreviewed` and `needs_follow_up` as active work. Assignment age is calculated from the latest assignment timestamp. Unassigned active work is surfaced separately for supervisor action. A workload spread of two or more marks the portfolio as imbalanced.

The dashboard provides direct links to:

- `/case-intelligence-review/supervisor-queue`
- `/case-intelligence-review/my-assignments`

v24.2 is read-only. It reuses the existing reviewer and supervisor queues, creates no workload record, mutates no assignment or decision event, and introduces no migration.
