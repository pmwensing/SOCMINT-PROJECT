# v13.45-v13.48 - Export Blocker Workflow Index

## Purpose

This index closes the export-blocker screenshot workflow follow-up line after the v13.36-v13.44 blocker foundation. The accepted direction is to keep the dedicated screenshot workflow discoverable, route-health visible, manifest downloads audited, and CI capture commands portable across local and GitHub runners.

## Included builds

- `V13_45_EXPORT_BLOCKER_WORKFLOW_DOCS_AND_ROUTE_HEALTH.md`: runbook workflow instructions, artifact references, and support-bundle route-health entries.
- `V13_46_EXPORT_BLOCKER_MANIFEST_DOWNLOAD_AUDIT.md`: explicit manifest download audit action and operator UI support copy.
- `V13_47_EXPORT_BLOCKER_SCREENSHOT_WORKFLOW_PLAYWRIGHT.md`: Python Playwright install guard for the dedicated screenshot workflow.
- `V13_48_EXPORT_BLOCKER_SCREENSHOT_WORKFLOW_MAKE_PYTHON.md`: portable `PYTHON=python` and `SCREENSHOT_PYTHON=python` workflow invocation.

## Operator acceptance

- Operators can find the dedicated Export Blocker Screenshots workflow in the runbook.
- Support bundles report the screenshot manifest JSON and audited manifest download routes.
- Manifest downloads emit a `screenshot_manifest_downloaded` audit action.
- The dedicated screenshot workflow installs Playwright and invokes the capture target without depending on a checked-in virtualenv path.

## Verification

- Focused V13.45-v13.48 coverage:
  - `tests/test_v13_34_support_bundle.py`
  - `tests/test_export_blocker_manifest_routes_v13_44.py`

## Handoff

This line follows `V13_36_TO_44_EXPORT_BLOCKER_INDEX.md`. Future workflow evidence work should keep route health, audit visibility, artifact naming, and runner-portable capture commands in the same operator-facing acceptance path.
