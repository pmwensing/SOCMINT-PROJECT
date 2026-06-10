# v14.2 Release Health Freshness

## Purpose

Make the Operator Release Console report whether its GitHub-derived release-health snapshot is fresh enough for release decisions.

## Added

- Snapshot freshness evaluation with a default 24-hour max age.
- `SOCMINT_RELEASE_HEALTH_MAX_AGE_HOURS` override for slower or stricter release windows.
- Console display for snapshot age, max-age threshold, and refresh command.
- Regression coverage for fresh, stale, missing, and invalid snapshot timestamps.

## Verification

- `tests/test_v14_operator_release_console.py`
