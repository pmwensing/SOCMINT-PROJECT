# SOCMINT v10.18.0 — Release Ledger Dashboard + Case Distribution Console

## Summary

Adds a case-wide release ledger dashboard for distribution exports. The dashboard summarizes released, ready-to-seal, and held subjects and links each subject to verification, download, release state, and seal markdown views.

## Focus

The dashboard answers:

- Which subjects have released distribution exports?
- Which subjects are verified and ready to seal?
- Which subjects remain held?
- What seal ID, ZIP hash, release timestamp, and actor are attached to released exports?
- Which download, verification, and release-state links should the operator use next?

## Changes

- Adds `src/socmint/release_ledger_dashboard.py`.
- Adds `src/socmint/release_ledger_dashboard_routes.py`.
- Adds `src/socmint/templates/release_ledger_dashboard.html`.
- Registers dashboard routes in `src/socmint/wsgi.py`.
- Adds `tests/test_release_ledger_dashboard_v10_18.py`.
- Adds `scripts/test_v10_18.sh`.

## Routes

- `GET /dossier/release-ledger-dashboard`
- `GET /dossier/release-ledger-dashboard?case_id=<case_id>`
- `GET /api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>`
- `GET /api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>/markdown`

## Merge gate

Run:

```bash
bash scripts/test_v10_18.sh
```
