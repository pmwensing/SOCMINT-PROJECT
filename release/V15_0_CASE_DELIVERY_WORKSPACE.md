# v15.0 Case Delivery Workspace

## Purpose

Start the v15 product line with an operator-facing Case Delivery Workspace that turns dossier readiness, evidence completeness, export blockers, delivery registry state, and human approval into one case-level gate.

## Added

- `/case-delivery` workspace UI route.
- `/api/v1/case-delivery/<case_id>` GET and POST API routes.
- `socmint.case_delivery_workspace.v15_0` payload builder.
- `socmint.case_delivery_workspace.v15_0.gate` delivery gate with dossier, evidence, export, registry, delivery, and approval checks.
- Regression coverage for ready, approval-required, blocked, and authenticated route states.

## Verification

- `tests/test_v15_case_delivery_workspace.py`
