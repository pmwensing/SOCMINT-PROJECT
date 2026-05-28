# v13.0 — Command Center Next Best Action

## Purpose

This release starts the clean real-world operator workflow foundation without rewriting the existing command center.

It adds a focused next-action layer that turns the current operational dashboard into a clearer product path:

```text
subject -> seed -> collection/import -> findings -> guided review -> dossier -> export package
```

## Added

- `src/socmint/command_center_next_action_v13.py`
  - Computes `dossier_readiness` from the current command-center payload.
  - Computes a single `next_best_action` for the operator.
  - Exposes the canonical v13 operator flow.

- API route:
  - `GET /api/v1/command-center/next-action`

- Tests:
  - `tests/test_command_center_next_action_v13.py`

## Decision logic

The next best action follows this order:

1. Create/open subject.
2. Add seed/target.
3. Process queued/running jobs.
4. Review failed jobs.
5. Run/import collection.
6. Do guided investigation action.
7. Generate dossier.
8. Export case package.

## Value

This gives SOCMINT-PROJECT a user-friendly command-center API that can drive the UI toward one obvious next step instead of presenting a broad feature list.
