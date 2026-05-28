# v13.5 — Claim/Evidence Ledger Skeleton

## Purpose

Start the claim/evidence ledger without requiring a database migration.

This release builds a read-only ledger over existing spine data:

- `SpineDossierAssertion`
- `SpineObservation`
- `SpineRawArtifact`

## Added

- `src/socmint/claim_evidence_ledger_v13.py`
  - Builds ledger rows from assertions and observations.
  - Links observations to raw artifacts by connector run.
  - Reports evidence coverage counts.

- `src/socmint/claim_evidence_ledger_routes_v13.py`
  - Adds a subject-level API endpoint.

- Route:
  - `GET /api/v1/subjects/<subject_id>/claim-evidence-ledger`

- Tests:
  - `tests/test_claim_evidence_ledger_v13.py`

## Ledger row fields

```text
claim_id
claim_type
claim_value
confidence
review_state
source
evidence_refs
artifact_links
has_evidence
created_at
```

## Summary fields

```text
claim_count
with_evidence
missing_evidence
unreviewed
```

## Value

This gives the dossier system a first reusable contract for:

```text
Claim -> Evidence refs -> Artifact links -> Review state
```

Future versions can add first-class claim/evidence tables and CSV export without changing the user-facing ledger contract.
