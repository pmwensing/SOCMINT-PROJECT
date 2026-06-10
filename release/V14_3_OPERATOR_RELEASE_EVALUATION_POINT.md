# v14.3 Operator Release Evaluation Point

## Purpose

Define the v14 Operator Release Console evaluation point after local evidence, GitHub-derived health, and snapshot freshness are all visible in one place.

## Added

- Evaluation payload with `EVALUATION_POINT_REACHED`, `PAUSE_FOR_REPAIR`, and `REFRESH_RELEASE_HEALTH` decisions.
- Blocker rollup with source and detail for any failed console gate.
- Console rendering for criteria, blocker count, and next action.
- Regression coverage for passing and blocked evaluation states.

## Evaluation Criteria

- Release docs accounted for.
- Open PR queue clean.
- Local git metadata available.
- Release health snapshot passing.
- Release health snapshot fresh.

## Verification

- `tests/test_v14_operator_release_console.py`
