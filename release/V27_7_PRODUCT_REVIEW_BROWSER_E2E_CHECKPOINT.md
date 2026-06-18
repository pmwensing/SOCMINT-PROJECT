# v27.7 Product Review and Browser E2E Checkpoint

Adds the final Product Review and Browser E2E Checkpoint for the complete v27 journey.

The checkpoint validates global search, case/entity/evidence/finding search, advanced filters and facets, saved views, watchlists and monitoring, report builder and export packages, and history and audit. It verifies required modules, templates, browser script, release notes, route registration, duplicate-route absence, and the absence of v27 migration artifacts.

The product review confirms authentication, CSRF-protected write operations, execution against the requesting user’s current access scope, append-only boundaries for saved-view, watchlist, report, and package events, and the rule that saved views, watchlists, reports, and exports never grant access.

The browser E2E journey opens every v27 workspace, exercises representative saved-view, watchlist, monitoring, report-definition, and report-generation writes, validates every major API, and checks the product-review checkpoint itself.

Browser output uses:

- `status: passed|failed`
- `passed_count`
- `failed_count`
- `v27_closed`
- `next_action: begin_v28|resolve_v27_browser_e2e_failures`

v27 closes only when all product checks and browser E2E checks pass. A failed browser or product check leaves `v27_closed` false and blocks `begin_v28`.

Routes:

- `GET /global-search/product-review`
- `GET /api/v1/global-search/product-review-checkpoint`

Run the browser checkpoint with:

```bash
SOCMINT_CHROME_BINARY=/usr/bin/chromium \
SOCMINT_CHROMEDRIVER=/usr/bin/chromedriver \
python3 scripts/run_v27_7_search_reporting_browser_e2e.py
```

This slice is read-only except for the representative E2E calls against mocked checkpoint services. It creates no product-review record, mutates no source event, changes no case access scope, performs no connector execution or collection activity, and introduces no migration.
