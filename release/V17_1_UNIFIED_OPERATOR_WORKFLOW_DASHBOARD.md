# v17.1 Unified Operator Workflow Dashboard

The v17.1 layer adds one operator-facing dashboard for the case-delivery workflow.

- UI: `/operator/workflow-dashboard?case_id=<case_id>`
- API GET: `/api/v1/operator/workflow-dashboard/<case_id>`
- API POST: `/api/v1/operator/workflow-dashboard/<case_id>`

The dashboard combines case-delivery readiness, v16 recovery-chain closure, normal delivery operations state, operator release-console health, consolidated blockers, and one prioritized recommended next action.

## Operator workflow behavior

- Case-delivery gate blockers take first priority.
- Recovery-chain closure blockers take second priority.
- Non-dispatchable operations take third priority.
- Stale release health recommends refreshing the release-health snapshot.
- A clear workflow recommends dispatching delivery operations.

## Product surface

The UI provides summary cards, workflow status, consolidated blockers, recommended action, and direct links to the case-delivery workspace and operator release console.

## Validation

- Focused regression coverage in `tests/test_v17_1_unified_operator_workflow_dashboard.py`.
- Production route registration is included in `src/socmint/wsgi.py`.
- No database schema mutation or migration is introduced.
