# v22.7 Product Review and Browser E2E Checkpoint

Validates the complete browser journey across the v22 release and delivery product slice.

The browser validation covers release authorization, package preview and acknowledgement, secure distribution through the existing case-delivery path, delivery receipt, recipient acknowledgement, recovery controls, consolidated history, and closure readiness.

The product-review checkpoint also verifies required v22 modules, templates, client assets, release notes, route registration, duplicate-route absence, and the no-migration boundary.

Successful focused tests, full-suite validation, and the browser report close v22 as a clean product checkpoint before starting a new product slice.

Commands:

- `python3 -m pytest -q tests/test_v22_7_dossier_release_product_review.py`
- `python3 -m pytest -q tests/test_v22_7_dossier_release_product_review_routes.py`
- `python3 scripts/run_v22_7_dossier_release_browser_e2e.py`

The checkpoint is validation-only. It does not mutate release records, introduce another integrity wrapper, or add a database migration.
