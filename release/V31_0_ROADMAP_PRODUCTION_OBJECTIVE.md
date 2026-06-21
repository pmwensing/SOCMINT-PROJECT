# v31.0 — Operational Analytic Workflow and Dossier Publication

v31.0 is implemented on the Ruff-clean master baseline.

## Workflow

approved dossier contribution → publication candidate → draft revision → editorial validation → human release approval → immutable published revision → supersession history

## Status

- v31.0 Publication Review Workspace: implemented
- v31.1 Publication Candidate Contract: next
- no automatic publication
- no release approval
- no dossier mutation
- no database migration

## Validation

```bash
python3 -m pytest -q tests/test_v31_0*.py
python3 -m pytest -q tests/test_v31*.py
python3 -m pytest -q
python3 -m ruff check src tests scripts
```

Next action: `implement_v31_1_publication_candidate_contract`.
