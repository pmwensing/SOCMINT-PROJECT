# SOCMINT v10.14.0 — Distribution Action Console

## Summary

Adds an operator action layer on top of the v10.13 certification dashboard and v10.12 certification index. Operators can mark a dossier export reviewed, approve distribution, hold distribution, reject distribution, and generate a distribution action packet.

## Focus

The action console answers:

- Has an operator reviewed the export?
- Has the export been approved for distribution?
- Was the export held or rejected?
- Why was a decision made?
- Which bundle is safe to distribute after certification and approval?
- What action history supports the distribution decision?

## Changes

- Adds `src/socmint/distribution_actions.py`.
- Adds `src/socmint/distribution_action_routes.py`.
- Registers distribution action routes in `src/socmint/wsgi.py`.
- Adds action controls to `src/socmint/templates/certification_dashboard.html`.
- Adds `tests/test_distribution_actions_v10_14.py`.
- Adds `scripts/test_v10_14.sh`.

## Actions

Supported operator actions:

- `mark_reviewed`
- `approve`
- `hold`
- `reject`

Approval is blocked while certification blockers remain.

## Routes

- `GET /api/v1/dossier-builder/v3/distribution-actions/<case_id>/<subject_id>`
- `POST /api/v1/dossier-builder/v3/distribution-actions/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>/markdown`

## Persistence

Distribution action logs are file-backed JSONL records under:

```text
exports/distribution_actions/<case_id>/<subject_id>.jsonl
```

A latest summary is written to:

```text
exports/distribution_actions/<case_id>/<subject_id>.summary.json
```

## Merge gate

Run:

```bash
bash scripts/test_v10_14.sh
```

or:

```bash
PYTHONPATH=src pytest -q tests/test_distribution_actions_v10_14.py tests/test_certification_dashboard_v10_13.py tests/test_dossier_certification_index_v10_12.py
```
