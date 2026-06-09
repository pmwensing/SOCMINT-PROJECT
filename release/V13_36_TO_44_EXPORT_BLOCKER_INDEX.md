# v13.36-v13.44 — Export Blocker Index

## Purpose

This index links the post-v13.35 export-blocker line after the correlation-scope closure gate. The accepted direction is to carry case/correlation scope correctness into export persistence, export verification, operator-visible blocker reasons, and screenshot/manifest evidence.

## Included builds

- `V13_36_EXPORT_CASE_SCOPE_BLOCKERS.md`: case/subject scope checks for export persistence and verification.
- `V13_37_EXPORT_POLICY_BLOCKERS_AND_AUDIT.md`: policy blockers and audit events for scoped export decisions.
- `V13_38_OPERATOR_BLOCKER_SURFACE.md`: operator-facing blocker summaries and gate-denial details.
- `V13_39_EXPORT_BLOCKER_ROUTES_UI_WARNINGS.md`: route/UI coverage and warning hygiene for export blockers.
- `V13_40_EXPORT_BLOCKER_SCREENSHOTS_FIXTURES_COMMAND_CENTER.md`: runtime screenshot fixtures and command-center export blocker evidence.
- `V13_41_EXPORT_BLOCKER_SCREENSHOT_WORKFLOW_CI.md`: CI screenshot capture workflow coverage.
- `V13_42_EXPORT_BLOCKER_ARTIFACT_MANIFEST_AND_SMOKE.md`: screenshot artifact manifest and smoke validation.
- `V13_43_EXPORT_BLOCKER_MANIFEST_HASHES_AND_UPLOAD.md`: manifest hashes and upload/download integrity.
- `V13_44_EXPORT_BLOCKER_DEDICATED_SCREENSHOT_WORKFLOW.md`: dedicated screenshot workflow separation.

## Operator acceptance

- Exports are blocked when manifest subject/case scope does not match the requested export scope.
- Policy blockers are visible before artifact distribution.
- Operator APIs and UI responses include blocker codes and details.
- Screenshot evidence is captured, indexed, hashed, and validated as a release artifact line.

## Verification

- Focused V13.36-v13.44 suite:
  - `tests/test_export_case_scope_blockers_v13_36.py`
  - `tests/test_export_policy_blockers_v13_37.py`
  - `tests/test_operator_blocker_surface_v13_38.py`
  - `tests/test_export_blocker_routes_v13_39.py`
  - `tests/test_export_blocker_demo_v13_40.py`
  - `tests/test_export_blocker_screenshot_workflow_v13_41.py`
  - `tests/test_export_blocker_artifacts_v13_42.py`
  - `tests/test_export_blocker_manifest_refresh_v13_43.py`
  - `tests/test_export_blocker_manifest_routes_v13_44.py`

## Handoff

This line follows `V13_35_FINAL_CORRELATION_SCOPE_CLOSURE.md`. Future export-blocker work should keep scope mismatch, policy risk, and artifact integrity failures visible at both the API and operator UI layers.
