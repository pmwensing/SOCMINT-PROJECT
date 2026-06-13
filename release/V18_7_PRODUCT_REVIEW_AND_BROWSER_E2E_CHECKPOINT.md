# v18.7 Product Review and Browser E2E Checkpoint

Adds the product checkpoint endpoint `/api/v1/case-intelligence-review/product-review-checkpoint` and the real-browser runner `scripts/run_v18_7_case_intelligence_browser_e2e.py`.

The checkpoint verifies required v18 modules, assets, routes, release notes, and absence of v18 migration artifacts. The browser runner validates workspace rendering, analyst decision feedback, session-history update, and manual history refresh.

Evidence is written to `artifacts/v18_7_case_intelligence_browser_e2e.json`.
