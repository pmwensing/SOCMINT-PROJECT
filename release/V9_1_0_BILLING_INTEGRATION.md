# SOCMINT v9.1.0 — Real Billing Integration

## Summary

Adds provider-neutral billing lifecycle support on top of the v8.3 billing bridge.

## Added

- Billing customer/subscription link table.
- Provider event normalization for Stripe-compatible webhook shapes.
- Customer link helper.
- Subscription/customer status helper.
- Provider config/report helper.
- Admin billing customer-link routes.
- Admin provider-event replay route.
- Alembic migration `0013_billing_customer_links`.
- Focused v9.1 billing integration tests.

## New API surfaces

- `GET /api/v1/admin/billing/provider-config`
- `GET /api/v1/admin/billing/customer-links/<username>`
- `POST /api/v1/admin/billing/customer-links/<username>`
- `POST /api/v1/admin/billing/provider-events`

## Merge gate

Full CI must pass before merge.

## Next target

v9.2.0 — Team/Case Access Control.
