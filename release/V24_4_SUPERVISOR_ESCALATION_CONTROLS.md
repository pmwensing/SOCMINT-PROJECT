# v24.4 Supervisor Escalation Controls

Adds immutable escalation, acknowledgement, reassignment, and resolution actions for cases currently present in the blocked and overdue queue.

Every control event is bound to the current queue snapshot and source case state, including the queue schema and version, active thresholds, complete queue item, current severity, stage age, assignment age, blockers, owner, reviewer, review state, and remediation links. The source-state SHA-256 and control-event SHA-256 make the binding independently verifiable.

Controls:

- escalation requires explicit confirmation and a reason
- acknowledgement requires an existing escalation
- reassignment requires an existing escalation and reviewer identity
- resolution requires an existing escalation and resolution text

Routes:

- `GET /portfolio-operations/escalations`
- `GET /api/v1/portfolio-operations/escalations`
- `POST /api/v1/portfolio-operations/<case_id>/escalate`
- `POST /api/v1/portfolio-operations/<case_id>/acknowledge`
- `POST /api/v1/portfolio-operations/<case_id>/reassign`
- `POST /api/v1/portfolio-operations/<case_id>/resolve`

Each action is recorded as a separate audit event. Reassignment records supervisory direction but does not rewrite the existing reviewer assignment event. Resolution records the supervisor outcome but does not delete or rewrite the queue source.

The underlying case, stage, and assignment events remain unchanged. No queue snapshot is mutated, and no migration is introduced.
