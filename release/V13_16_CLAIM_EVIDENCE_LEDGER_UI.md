# v13.16 — Claim/Evidence Ledger UI

## Purpose

Make the claim/evidence ledger visible to analysts instead of API-only.

## Added

- `src/socmint/claim_evidence_ledger_ui_routes_v13.py`
  - Adds a subject-level ledger page.

- `src/socmint/templates/claim_evidence_ledger.html`
  - Shows claim count, evidence coverage, missing evidence, unreviewed count, and ledger rows.

- Route:
  - `GET /subjects/<subject_id>/claim-evidence-ledger`

- Tests:
  - `tests/test_claim_evidence_ledger_ui_routes_v13.py`

## Value

Analysts can inspect claim-to-evidence coverage before generating or relying on a dossier.
