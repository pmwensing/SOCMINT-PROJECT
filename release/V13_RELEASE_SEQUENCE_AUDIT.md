# v13 Release Sequence Audit

## Purpose

This audit records the current v13 release-note sequence after the v13.35 correlation-scope closure and the v13.36-v13.48 export-blocker workflow line. It is intentionally an audit, not a retroactive rewrite of missing release notes.

## Current closure points

- `V13_35_FINAL_CORRELATION_SCOPE_CLOSURE.md`: closes the v13.35 correlation-scope correctness gate and backs the `v13.35` tag.
- `V13_36_TO_44_EXPORT_BLOCKER_INDEX.md`: indexes scoped export blockers, policy blockers, operator surfaces, screenshots, manifests, hashes, and dedicated screenshot workflow setup.
- `V13_45_TO_48_EXPORT_BLOCKER_WORKFLOW_INDEX.md`: indexes screenshot workflow runbook guidance, route health, manifest download audit, Playwright installation, and portable Make invocation.

## Numbered sequence status

| Range | Status | Notes |
| --- | --- | --- |
| v13.0-v13.10 | Documented | Command Center, readiness, claim ledger, handoff status, normalization review, and review UI release notes exist. |
| v13.11 | Documented | `V13_11_NORMALIZATION_FORM_UPDATE.md` documents normalization update route form-post fallback from historical commit `6f5773f`. |
| v13.12-v13.22 | Documented | Review queue UX, promotion, ledger UI, readiness UI, subject status, manifest draft, dry-run spec, usability smoke, and route audit notes exist. |
| v13.23 | Documented | `V13_23_WORKFLOW_NAVIGATION.md` documents Command Center workflow navigation coverage. |
| v13.24 | Documented | Export manifest UI release note exists. |
| v13.25 | Gap | No `V13_25_*` release note or direct `test_v13_25*` file is present. |
| v13.26 | Documented | Operator guide and test script release note exists. |
| v13.27-v13.31 | Documented | Runtime/full-report/export-artifact regression notes now exist for v13.27 through v13.31. |
| v13.32-v13.35D | Documented | Full dossier UX, final RC lock, support bundle diagnostics, and correlation-scope A-D release notes exist. |
| v13.36-v13.48 | Indexed | Export-blocker and screenshot workflow release notes are present and indexed. |

## Former test-backed gaps

- v13.23: `V13_23_WORKFLOW_NAVIGATION.md`, backed by `tests/test_v13_23_workflow_navigation.py`
- v13.27: `V13_27_FULL_REPORT_HISTORY_RUNTIME_SAFE.md`, backed by `tests/test_v13_27_full_report_history_runtime_safe.py`
- v13.28: `V13_28_RUNTIME_ROUTE_HARDENING.md`, backed by `tests/test_v13_28_runtime_route_hardening.py`
- v13.29: `V13_29_FULL_DOSSIER_ENDPOINT_ALIAS.md`, backed by `tests/test_v13_29_full_dossier_endpoint_alias.py`
- v13.30: `V13_30_RUNTIME_VISUAL_POLISH.md`, backed by `tests/test_v13_30_runtime_visual_polish.py`
- v13.31: `V13_31_EXPORT_ARTIFACT_UX.md`, backed by `tests/test_v13_31_export_artifact_ux.py`

## Handoff

Future v13 documentation work should either close the true v13.25 gap with evidence or leave this audit as the source of truth. New v13 release work should keep a one-to-one relationship between release notes, changelog entries, and focused regression coverage.
