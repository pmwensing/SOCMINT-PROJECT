# v25.7 Product Review and Browser E2E Checkpoint

Validates the full cross-case journey from candidate discovery through review decisions, confirmed-link registration, graph projection, impact analysis, history and audit, and metrics and confidence.

The product review verifies:

- all v25.0 through v25.6 service modules
- browser templates and client assets
- release notes for every completed v25 slice
- authenticated browser and API routes
- missing and duplicate route detection
- absence of v25 migration artifacts
- session case-access controls
- immutable review and confirmed-link bindings
- graph, impact, history, and metrics preservation boundaries
- confidence as an operational indicator rather than a probability or factual-certainty claim

The standalone Selenium runner exercises the complete browser journey using representative candidate, accepted-review, confirmed-link, graph, impact, history, and metrics payloads. It validates each product page, the interactive graph renderer, all major read APIs, and the product checkpoint.

Routes:

- `GET /cross-case-intelligence/product-review`
- `GET /api/v1/cross-case-intelligence/product-review-checkpoint`

Run the browser checkpoint with:

```bash
python3 scripts/run_v25_7_cross_case_browser_e2e.py
```

A successful report uses schema `socmint.cross_case_browser_e2e.v25_7`, reports zero failed checks, sets `v25_closed` to true, and identifies `begin_v26` as the next action.

v25.7 is read-only. It creates no checkpoint record and changes no candidate, review, confirmed-link, graph, impact, history, metrics, or source event. A passing browser report closes v25 before v26 begins.
