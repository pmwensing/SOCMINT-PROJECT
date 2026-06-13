# v19.5 Reviewer Work Queue / My Assignments

Adds a focused queue for the currently authenticated reviewer.

The queue shows only decisions currently assigned to that reviewer, including:

- case id
- decision
- age
- review state
- assignment note
- direct navigation to the case workspace

Reviewers can update the review state to `reviewed`, `needs_follow_up`, or `accepted`. Each update creates a separate immutable review annotation and never changes the source decision.

Routes:

- `GET /case-intelligence-review/my-assignments`
- `GET /api/v1/case-intelligence-review/my-assignments`
- `POST /api/v1/case-intelligence-review/my-assignments/<case_id>/decisions/<decision_record_id>/review-state`

The reviewer endpoint verifies that the decision is assigned to the authenticated reviewer before recording a state change.

The existing `audit_logs` table is reused. No new table or migration is introduced.
