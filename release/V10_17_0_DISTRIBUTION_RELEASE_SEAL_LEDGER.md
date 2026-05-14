# SOCMINT v10.17.0 — Distribution Export Seal + Release Ledger

## Summary

Adds a final release seal and case release ledger for verified distribution exports. A distribution export can only be sealed after integrity verification passes.

## Focus

The release ledger answers:

- Has this distribution export been finally released?
- Who sealed the release?
- When was the release sealed?
- Which ZIP hash was released?
- Which verification status supported the release?
- Which subjects have released exports for a case?

## Changes

- Adds `src/socmint/distribution_release_ledger.py`.
- Adds `src/socmint/distribution_release_ledger_routes.py`.
- Registers release ledger routes in `src/socmint/wsgi.py`.
- Adds release state and seal controls to `src/socmint/templates/certification_dashboard.html`.
- Adds `tests/test_distribution_release_ledger_v10_17.py`.
- Adds `scripts/test_v10_17.sh`.

## Routes

- `POST /api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/seal`
- `GET /api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/markdown`
- `GET /api/v1/dossier-builder/v3/distribution-release-ledger/<case_id>`

## Gate behavior

Release sealing is blocked unless distribution export verification passes.

## Persistence

Release seals are written under:

```text
exports/distribution_release_ledger/<case_id>/<subject_id>.seal.json
```

The append-only case ledger is written to:

```text
exports/distribution_release_ledger/<case_id>/release_ledger.jsonl
```

## Merge gate

Run:

```bash
bash scripts/test_v10_17.sh
```
