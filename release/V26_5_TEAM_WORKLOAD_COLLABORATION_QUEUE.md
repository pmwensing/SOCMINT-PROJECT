# v26.5 Team Workload and Collaboration Queue

Adds a read-only operational queue for collaboration and team workload across visible cases.

The queue consolidates:

- my assigned cases
- pending requests
- items awaiting acknowledgement
- delegated work
- pending handoffs
- overdue collaboration items
- unassigned collaboration work
- supervisor escalation queue
- recent team activity
- collaboration load by user
- workload imbalance

The queue calculates active case count, open requests, open handoffs, unread updates, total collaboration load, average collaboration load, and high-load users. It preserves direct links into each case, case-team page, notes and mentions, requests and handoffs, responses and resolution, reviewer queue, and supervisor queue.

Overdue status is calculated from request and handoff due dates at read time. Unassigned work is derived from outstanding review work without an assigned reviewer. Supervisor escalations are derived from unresolved escalation responses.

Routes:

- `GET /collaboration/my-work`
- `GET /api/v1/collaboration/my-work`

The result includes a deterministic queue SHA-256, the current case-access scope, summary counts, and a generated timestamp.

v26.5 is read-only. It creates no collaboration record, mutates no team assignment, note, request, handoff, response, case, evidence, review, closure, archive, release, portfolio, or cross-case source event, performs no connector execution or collection activity, and introduces no migration.
