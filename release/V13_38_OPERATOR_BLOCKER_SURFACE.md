# v13.38 - Operator Blocker Surface

## Scope

This build surfaces export blocker details in operator-facing API summaries and removes pytest collection noise from the test-data controls helper.

## Included

- Export pack summaries include blocker count, blocker codes, and blocker detail payloads
- Export gate decisions include verification summary details for operator-facing deny reasons
- Test-data summary helper is no longer collected as a pytest test while preserving existing imports
- Regression tests for blocker summary and gate decision surface area

## Operator Result

Operators can inspect export summary and gate decision responses to see why an export is denied without fetching the full export pack or verification report.
