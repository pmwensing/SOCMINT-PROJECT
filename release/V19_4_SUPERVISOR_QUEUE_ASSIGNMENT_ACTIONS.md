# v19.4 Supervisor Queue Assignment Actions

Adds supervisor controls to assign or reassign outstanding durable decisions to a reviewer.

Assignments are recorded as a separate immutable audit annotation with:

- case id
- decision record id
- assigned reviewer
- assigning supervisor
- assignment note
- assignment timestamp

The original persistent decision record is never updated or deleted. Reassignment creates another annotation, and the queue projects the latest assignment.

Only outstanding decisions in `unreviewed` or `needs_follow_up` state can be assigned. Missing reviewers, cross-case decision ids, and completed decisions are blocked.

Route:

- `POST /api/v1/case-intelligence-review/supervisor-queue/<case_id>/decisions/<decision_record_id>/assignment`

The supervisor UI supports inline assign or reassign actions and refreshes the displayed assignment after success.

The existing `audit_logs` table is reused. No new table or migration is introduced.
