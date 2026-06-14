# v19.6 Reviewer Queue Completion / Handoff Summary

Adds a supervisor-facing summary of completed reviewer work, outstanding assignments, follow-up items, reviewer throughput, and handoff readiness.

The summary provides:

- completed, outstanding, and follow-up counts
- per-reviewer assigned and completed totals
- reviewer completion rates
- oldest open assignment age
- per-case completion and handoff readiness
- direct case workspace navigation
- optional reviewer and case filters

A case is handoff-ready only when all assigned decisions are in `reviewed` or `accepted` state and no outstanding or follow-up work remains. The global summary is ready only when every included assignment is complete.

Routes:

- `GET /case-intelligence-review/reviewer-handoff-summary`
- `GET /api/v1/case-intelligence-review/reviewer-handoff-summary`

This is a read-only product summary over existing immutable assignment and review annotations. It calculates handoff readiness without mutating source decisions, assignments, or delivery state.

The existing `audit_logs` table is reused. No new table or migration is introduced.
