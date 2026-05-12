# SOCMINT v8.3.0 — Billing

## Summary

Adds the billing bridge on top of v8.2 Membership + Quotas.

## Added

- Billing event ledger.
- Checkout session ledger.
- Stripe-compatible price mapping placeholders.
- Deterministic checkout session creator for CI and local testing.
- Webhook signature verification helper.
- Idempotent subscription event processing.
- Paid membership activation from checkout/subscription/invoice-paid events.
- Payment-failed grace state.
- Cancellation/subscription-deleted downgrade to Free.
- Account billing status API route.
- Account checkout API route.
- Billing webhook API route.
- Admin billing event replay route.
- Alembic migration `0011_billing`.
- v8.3 billing tests.

## Safety and product rules

- Paid plans activate quota entitlements through the v8.2 membership layer.
- Duplicate provider events are ignored by `provider_event_id`.
- Failed payments move memberships to `past_due_grace` instead of deleting data.
- Cancellations downgrade new actions to Free while preserving stored data.
- This implementation is provider-adapter ready but does not require live Stripe keys in CI.

## Validation

```bash
PYTHONPATH=$PWD/src pytest -q tests/test_billing_v8_3.py
```

## Next target

v8.4.0 — Tor Production.
