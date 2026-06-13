# v17.6 Operator Workflow Dashboard UX Hardening

The v17.6 layer improves the live operator dashboard experience without adding another integrity layer.

## UX improvements

- client-side action-result feedback for success, confirmation-required, cancellation, blocked, and request-failure states
- explicit confirmation prompts for release-health refresh and delivery dispatch
- loading and busy states with disabled controls and `aria-busy`
- automatic in-page action history refresh after action responses
- manual history refresh control using the read-only v17.5 history API
- clearer empty-history guidance
- safer dispatch disabling until case delivery, recovery closure, and operations readiness all pass
- clearer operator guidance around confirmed action plans and non-persistent session history
- navigation actions remain auditable through the existing v17.2-v17.5 action/receipt flow

## Product surface

- Dashboard UI: `/operator/workflow-dashboard?case_id=<case_id>`
- Client script: `src/socmint/static/operator_workflow_dashboard_v17_6.js`
- Existing action API: `POST /api/v1/operator/workflow-dashboard/<case_id>/actions`
- Existing history API: `GET /api/v1/operator/workflow-dashboard/<case_id>/actions/history`

The dashboard remains server-rendered for first load and progressively enhances action controls when JavaScript is available.

## Validation

- Focused regression coverage in `tests/test_v17_6_operator_workflow_dashboard_ux.py`.
- No new verification wrapper, database persistence, schema mutation, or migration is introduced.
