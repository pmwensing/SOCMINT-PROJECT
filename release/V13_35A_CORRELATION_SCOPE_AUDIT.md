# v13.35A — Correlation Scope Audit / Policy Gate

## Purpose

This is an audit-first correctness build. It does not add schema migrations.

## Safe decision

- Do not assume entity-correlation correctness is proven.
- Do not expand enrichment features until scope controls are implemented.
- Do not mix initial search runs without same-scope or same-target proof.
- Quarantine ambiguous cross-scope matches.

## Routes

- `/audit/correlation-scope/v13.35`
- `/api/v1/audit/correlation-scope/v13.35`

## Acceptance

- Scope coverage audit reports which tables lack persistent `correlation_scope_id`.
- Run grouping snapshot separates existing runs by `subject_id + seed_id`.
- Policy gate requires one of:
  - same scope
  - analyst-merged scope
  - deterministic same-target proof
- Ambiguous cross-scope matches quarantine.
