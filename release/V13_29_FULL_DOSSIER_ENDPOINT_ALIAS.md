# v13.29 - Full Dossier Endpoint Alias

## Purpose

Document the full-report history endpoint alias used by the Full Dossier v2 template.

## Added

- Registered UI endpoint alias `ui_full_report_history`.
- Full-report history route:
  - `GET /spine/subjects/<subject_id>/full-report/history`
- Template reference coverage so Full Dossier v2 links use the registered endpoint name.

## Verification

- `tests/test_v13_29_full_dossier_endpoint_alias.py`

## Value

Full Dossier v2 can link to export history through a stable Flask endpoint alias instead of relying on an unregistered route name.
