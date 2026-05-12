# SOCMINT v9.6 Release Cleanup Checklist

## Before merge

- [ ] Confirm `smoke/v9-6-operator-ux` was compared against current `master`.
- [ ] Confirm stale smoke branch changes were ported rather than merged directly.
- [ ] Run focused operator smoke tests.
- [ ] Run full CI.
- [ ] Confirm production-release route registration still works.
- [ ] Confirm admin-only operator smoke endpoints reject unauthenticated requests.

## Focused validation

```bash
python -m pytest tests/test_operator_smoke_v9_6.py
```

## Full validation

```bash
python -m pytest
```

## After merge

- [ ] Confirm `master` receives a successful CI run.
- [ ] Tag or document v9.6.0 if release process requires it.
- [ ] Delete stale source branch `smoke/v9-6-operator-ux`.
- [ ] Delete merged v9 release/hardening branches listed in `release/BRANCH_INVENTORY_V9_6.md`.
- [ ] Re-list branches and confirm only active feature branches remain.

## Release result

Expected state after completion:

- `master` includes v9.5.1 metadata sync.
- `master` includes v9.6 operator UX smoke routes and tests.
- v9 merged branches are pruned or explicitly retained with reason.
- remaining feature branches are known and tracked.
