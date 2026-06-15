# v23.7 Product Review and Browser E2E Checkpoint

Validates the full browser journey for the v23 case-closure lifecycle.

The checkpoint covers closure readiness, supervisor decision, retention assignment, deterministic archive generation, reopen request and authorization, consolidated history, derived closure and archive states, and final product-checkpoint readiness.

Static product review verifies all v23.0 through v23.6 modules, browser assets, release notes, required routes, duplicate-route absence, and migration absence.

Browser validation runs:

- Case Closure Workspace render
- Closure-readiness review
- Supervisor closure decision
- Retention-policy assignment
- Case archive generation
- Reopen request
- Reopen authorization
- Closure and Archive History render
- Reopened closure state
- Generated archive state
- Complete consolidated history
- Final v23 product checkpoint

Run:

```bash
python3 scripts/run_v23_7_case_closure_browser_e2e.py
```

The runner writes `reports/v23_7_case_closure_browser_e2e.json` and exits nonzero if any browser checkpoint fails.

This checkpoint creates no lifecycle record, changes no source event, and introduces no migration. A passing focused test suite, browser report, and full regression suite closes v23 before v24 Portfolio and Case Operations Command Center begins.
