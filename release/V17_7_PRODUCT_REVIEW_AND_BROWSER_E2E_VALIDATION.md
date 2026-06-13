# v17.7 Product Review Checkpoint and Browser-Level E2E Validation

The v17.7 layer closes the first operator-dashboard product slice with a static product review checkpoint and a real-browser end-to-end validation runner.

## Product review checkpoint

Authenticated endpoint:

- `GET /api/v1/operator/workflow-dashboard/product-review-checkpoint`

The checkpoint verifies:

- v17.0-v17.5 product modules are present
- the v17.6 template and JavaScript assets are present
- operator workflow routes are registered
- v17.0-v17.6 release notes and changelog entries exist
- no duplicate operator workflow routes are present
- no v17/operator-workflow migration artifacts were introduced
- the browser validation runner is present

A clean checkpoint returns `status: ready_for_browser_validation` and `next_action: run_browser_e2e_validation`.

## Browser-level validation

Run the real headless browser flow with Chrome:

```bash
python3 scripts/run_v17_7_operator_dashboard_browser_e2e.py --driver chrome
```

Or Firefox:

```bash
python3 scripts/run_v17_7_operator_dashboard_browser_e2e.py --driver firefox
```

The runner starts the real Flask app on an ephemeral local port, creates an authenticated test session, opens the live dashboard in Selenium, and validates:

- authenticated dashboard rendering
- unsafe dispatch remains disabled for an unready case
- confirmed action feedback appears
- session action history updates after an action
- manual history refresh works
- navigation actions reach the expected dashboard target

The JSON evidence report is written to:

- `artifacts/v17_7_operator_dashboard_browser_e2e.json`

A locally installed Chrome/Chromium or Firefox browser and a compatible driver/Selenium Manager environment are required.

## Validation

- Focused checkpoint coverage: `tests/test_v17_7_operator_workflow_product_review_checkpoint.py`
- Existing Flask/test-client suite remains the primary deterministic regression gate.
- Browser validation is intentionally a separate explicit command so environments without a browser do not fail the core pytest suite.
- No database persistence, schema mutation, or migration is introduced.
