# v14.1 Release Health Snapshot

## Purpose

Extend the v14 Operator Release Console with a refreshable release-health artifact that captures live GitHub PR and master workflow state for offline operator display.

## Added

- `release/OPERATOR_RELEASE_HEALTH.json` as the local release-health snapshot consumed by the console.
- `scripts/refresh_operator_release_health_v14_1.py` to refresh the snapshot from GitHub CLI state.
- Console rendering for open PR count, latest master SHA, workflow conclusions, and snapshot freshness.
- Regression coverage for snapshot loading, missing snapshot behavior, and release-note/changelog coverage.

## Verification

- `tests/test_v14_operator_release_console.py`
