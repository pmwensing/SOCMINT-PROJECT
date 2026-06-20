# v29.7 — Product Review and Browser E2E Checkpoint

## Objective

Close the v29 Connector and Collection Operations program only after the end-to-end operator workflow, browser navigation, access controls, API/UI consistency, and production invariants are verified.

## Required product review

- review every v29 workspace from collection operations through quality and dossier contribution
- verify navigation links, page titles, empty states, findings, queues, and operator guidance
- verify administrator-only access and unauthenticated redirects
- verify API and rendered workspace counts remain consistent
- confirm connector execution, automatic retry execution, evidence rewrite, and automatic dossier mutation remain unavailable
- confirm append-only audit history and deterministic evidence/quality bindings

## Required browser E2E coverage

1. Log in as an administrator.
2. Open the Collection Operations workspace.
3. Visit collection jobs, policy, adapter, evidence, recovery, and quality workspaces.
4. Create or load an authorized collection job fixture.
5. Register and accept an evidence artifact.
6. Derive an observation.
7. Create a quality assessment.
8. Approve a supported or trusted dossier contribution.
9. Verify low-trust, unaccepted, or observation-free output cannot be approved.
10. Verify a non-administrator receives forbidden responses and an unauthenticated browser is redirected to login.
11. Capture browser pass/fail totals and preserve the report as a release artifact.

## Closure gates

- focused v29.7 tests pass
- all v29 tests pass
- full pytest suite passes
- browser E2E failed count equals zero
- no unresolved product-review findings
- planning contract marks v29.7 implemented only after evidence for every gate exists
- `v29_closed` remains false until all gates pass

## Planned artifacts

- `src/socmint/collection_product_review_v29_7.py`
- `tests/test_v29_7_collection_product_review.py`
- `tests/test_v29_7_collection_product_review_routes.py`
- `scripts/run_v29_7_collection_browser_e2e.py`
- browser E2E JSON/Markdown report
- final update to `release/V29_0_PLANNING_CONTRACT.json`

## Initial validation commands

```bash
python3 -m pytest -q tests/test_v29*.py
python3 -m pytest -q
python3 scripts/run_v29_7_collection_browser_e2e.py
```

## Current state

Implementation started. The v29 program is not closed and the planning contract must not be advanced to `begin_v30` until the browser and regression evidence is recorded.
