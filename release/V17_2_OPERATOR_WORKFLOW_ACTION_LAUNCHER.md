# v17.2 Operator Workflow Action Launcher

The v17.2 layer turns the unified operator dashboard recommendation into guarded operator controls.

- Action API: `POST /api/v1/operator/workflow-dashboard/<case_id>/actions`
- Dashboard UI: `/operator/workflow-dashboard?case_id=<case_id>`

## Supported actions

- `open_case_delivery`
- `open_release_console`
- `review_blockers`
- `refresh_release_health`
- `dispatch_delivery_operations`

Navigation actions return safe GET targets immediately. Refresh and dispatch actions require explicit `confirmed: true` before the launcher returns an action plan.

Dispatch is additionally blocked unless case delivery is ready, the recovery chain is closed, and normal delivery operations are dispatchable.

The launcher returns plans rather than silently executing commands or state changes. Release-health refresh returns the reviewed manual command, and delivery dispatch returns a confirmed POST action plan tied to the current operation id.

## Validation

- Focused regression coverage in `tests/test_v17_2_operator_workflow_action_launcher.py`.
- Safe controls are rendered in `unified_operator_workflow_dashboard.html`.
- No database schema mutation or migration is introduced.
