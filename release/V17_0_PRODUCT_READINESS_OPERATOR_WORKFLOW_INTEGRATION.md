# v17.0 Product Readiness / Operator Workflow Integration

The v17.0 layer moves the workstream back from internal recovery-chain mechanics to visible SOCMINT product readiness.

- `POST /api/v1/product-readiness/operator-workflow`

The snapshot checks that the operator workflow surfaces, case-delivery UX routes, release-console alignment, v16.18 recovery-chain closure, and normal delivery operations route are all present and ready.

## Product readiness checks

- Case-delivery workspace UI route is present.
- Case-delivery API route is present.
- Normal delivery operations route is present.
- Recovery-chain closure audit route is present.
- Operator release console API/UI routes are present.
- v16.18 recovery-chain closure audit is closed.
- Product-level modules are present.
- Product-level release documentation is present.
- Changelog records v17.0.
- Duplicate product route drift is absent.

## Result

A passing snapshot returns `status: ready` and `next_action: resume_product_level_delivery_work`.

## Validation

- Focused regression coverage in `tests/test_v17_0_product_readiness_operator_workflow.py`.
- No database schema mutation or migration is introduced.
