# SOCMINT v8.2.0 — Membership + Quotas

## Summary

Implements the first productization gate layer from the Ultimate SOCMINT build spec.

## Added

- Membership plan catalogue for Free, Weekly, Starter, Pro, and Team.
- Default Free membership creation for existing or new users on first membership access.
- Usage event ledger.
- Period usage counters for daily and monthly quota keys.
- Quota override ledger for admin-controlled case-specific exceptions.
- Gate contract helper returning `allowed`, `plan`, `quota_key`, `used`, `limit`, `resets_at`, `scope_state`, `upgrade_required`, and `reason`.
- Account membership/usage API helpers.
- Admin membership assignment and quota override API helpers.
- Alembic migration `0010_membership_quotas`.
- v8.2 quota test coverage.

## Plan limits

The implemented quota keys follow the build spec:

- `active_cases`
- `subjects_per_month`
- `connector_runs_per_day`
- `browser_captures_per_day`
- `account_ingests_per_day`
- `signed_exports_per_month`
- `graph_builds_per_day`
- `storage_gb`
- `team_seats`
- `watermark_exports`

## Gate contract

Every future mutating workflow can now call `membership.evaluate_gate(...)` before work is performed and can pass `consume=True` when usage should be recorded.

## Validation

```bash
PYTHONPATH=$PWD/src pytest -q tests/test_membership_quotas_v8_2.py
```

## Next follow-up

Wire the gate helper into the mutating dashboard/API routes incrementally:

- case create
- subject create
- connector run
- account discovery ingest
- browser capture
- graph build
- signed export

Paid tiers raise limits, but they do not bypass responsible-use scope.
