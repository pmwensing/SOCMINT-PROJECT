# v14.0 Operator Release Console

## Purpose

Start the v14 release line with an in-app operator console that summarizes local release evidence, git metadata, stale PR queue closure, and the next release action.

## Added

- `/operator/release-console` and `/release/console` UI routes.
- `/api/v1/operator/release-console` JSON route.
- Local release evidence checks for v13 closure docs, export-blocker indexes, the v13.25 reserved gap, v10 PR triage, the open PR queue closure, and the v14 changelog entry.
- Git metadata summary for branch, commit, latest tag, and dirty working-tree state.
- Regression coverage for the payload and authenticated UI/API routes.

## Verification

- `tests/test_v14_operator_release_console.py`
