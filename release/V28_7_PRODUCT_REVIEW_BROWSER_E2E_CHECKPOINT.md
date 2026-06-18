# v28.7 Product Review and Browser E2E Checkpoint

Closes the complete v28 administration journey through a final product review, route and asset checkpoint, focused regression tests, and browser E2E validation.

The checkpoint covers:

- Administration Workspace
- User and Account Administration
- Role, Permission, and Access Policy Management
- Team and Organizational Structure
- Access Review and Certification
- Connector and Integration Administration
- Platform Health, Jobs, and Operational Audit

The product-review service verifies required modules, templates, release notes, route registration, duplicate administration routes, and unexpected v28 migration artifacts. It reports blockers without mutating source records or creating a checkpoint record.

The browser E2E journey authenticates an active administrator, visits each v28 browser page, reads each administration API, exercises representative CSRF-protected writes, and validates the final product-review checkpoint.

Security and preservation boundaries validated by the checkpoint include authentication, administrator authorization, CSRF write protection, explicit confirmation, administrative-reason binding, append-only governance events, credential and secret exclusion, team membership not granting case access, access-review decisions not directly mutating policy, connector execution remaining separate, and the operations workspace remaining read-only.

The browser report closes v28 only when every check passes:

- `status: passed`
- `failed_count: 0`
- `v28_closed: true`
- `next_action: begin_v29`

If any browser check fails, v28 remains open and the report returns `next_action: resolve_v28_browser_e2e_failures`.

Routes:

- `GET /administration/product-review`
- `GET /api/v1/administration/product-review-checkpoint`

Validation:

```bash
python3 -m pytest -q tests/test_v28_7_administration_product_review.py
python3 -m pytest -q tests/test_v28_7_administration_product_review_routes.py
python3 scripts/run_v28_7_administration_browser_e2e.py --json
python3 -m pytest -q
```

This slice introduces no migration.
