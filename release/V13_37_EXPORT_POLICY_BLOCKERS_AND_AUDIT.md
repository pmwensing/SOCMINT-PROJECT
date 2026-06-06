# v13.37 - Export Policy Blockers and Audit

## Scope

This build adds policy blockers and audit coverage for scoped export decisions.

## Included

- `.gitignore` coverage for generated runtime screenshot and support bundle artifacts
- Export scope allow/block audit events
- Export preflight blockers for explicit unreviewed assertion evidence
- Export preflight blockers for explicit single-source claims
- Export preflight blockers for contradictory identity claim evidence
- Regression tests for policy blockers and scope decision audit records

## Operator Result

Generated runtime artifacts no longer clutter git status, scoped export allow/block decisions are written to the export audit log, and risky assertion evidence blocks export readiness before artifact distribution.
