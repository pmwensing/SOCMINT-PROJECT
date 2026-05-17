# v11.9 — Real Enrichment Run UX + Evidence Promotion Pipeline

## Purpose

v11.9 turns connector output into an analyst-facing run inspector and evidence promotion pipeline.

## Added

- Connector run result inspector per subject.
- Real / diagnostic / review badges per connector run.
- Normalized findings displayed directly under each run.
- Promotion-ready observations under each run.
- One-click promote observation to confirmed assertion.
- Failed/empty connector run explanation panel.
- Dossier readiness gate requiring at least one confirmed assertion.
- `scripts/test_v11_9.sh`
- `make test-v11-9`

## Validation

Run:

```bash
make test-v11-9
```

Expected:

```text
PASS v11.9 direct run inspector/promotion/readiness smoke
PASS v11.9 browser/API smoke
PASS v11.9 real enrichment run UX and evidence promotion smoke
```
