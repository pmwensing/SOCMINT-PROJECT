# SOCMINT v10.13.0 — Certification Index UI / Distribution Readiness Dashboard

## Summary

Adds an analyst-facing UI for the v10.12 certification index. The dashboard gives operators a case-wide view of export readiness, blockers, audit coverage, attached artifacts, and safe-to-distribute bundles.

## Focus

The UI answers:

- Which dossier exports exist.
- Which artifacts are attached.
- Which exports are verified.
- Which exports pass or fail certification.
- Which blockers remain.
- Which audit coverage exists.
- Which bundle is safe to distribute.

## Changes

- Adds `src/socmint/certification_dashboard_routes.py`.
- Adds `src/socmint/templates/certification_dashboard.html`.
- Registers dashboard routes in `src/socmint/wsgi.py`.
- Adds a signed-in navigation link in `src/socmint/templates/base.html`.
- Adds `tests/test_certification_dashboard_v10_13.py`.
- Adds `scripts/test_v10_13.sh`.

## UI routes

- `GET /dossier/certification-dashboard`
- `GET /dossier/certification-dashboard?case_id=<case_id>`
- `GET /dossier/certification-dashboard?case_id=<case_id>&subject_id=<subject_id>`

## API companion route

- `GET /api/v1/dossier-builder/v3/certification-dashboard/<case_id>`
- Optional query: `?subject_id=<subject_id>`

## Dashboard sections

- Case and subject filter form.
- Summary cards.
- Distribution readiness links.
- Blocker badges.
- Dossier export table.
- Focused subject artifact table.
- Markdown readiness preview.

## Merge gate

Run:

```bash
bash scripts/test_v10_13.sh
```

or:

```bash
PYTHONPATH=src pytest -q tests/test_certification_dashboard_v10_13.py tests/test_dossier_certification_index_v10_12.py
```
