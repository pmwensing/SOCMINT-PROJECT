# v13.20 — Case Package Dry Run Spec

## Purpose

Define the dry-run validation contract before real package generation writes files.

## Input

```text
subject_id
```

## Planned route

```text
GET /api/v1/subjects/<subject_id>/checklist-preview
```

## Planned output

```json
{
  "schema": "socmint.checklist_preview.v13_20",
  "subject_id": 1,
  "state": "blocked | ready_with_warnings | ready",
  "block_count": 0,
  "warning_count": 0,
  "checks": [],
  "manifest": {}
}
```

## Checks

```text
readiness
claim_coverage
status_rows
write_mode
```

## Behavior

- Read the v13.19 export manifest draft.
- Validate readiness state.
- Validate claim evidence coverage.
- Validate subject status rows.
- Return pass/warn/block checks.
- Write no files.

## Value

Operators can see whether a subject is package-ready before actual export generation exists.

## Implementation note

Initial executable route attempts were blocked by the connector safety layer. This spec locks the contract for the next implementation pass.
