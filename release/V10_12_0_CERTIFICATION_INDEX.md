# SOCMINT v10.12.0 — Certification Index

## Summary

Adds a case-wide dossier certification index that converts individual export manifests and per-subject certification checks into a distribution-readiness view.

## Focus

The certification index answers:

- Which dossier exports exist.
- Which artifacts are attached.
- Which exports are verified.
- Which exports pass or fail certification.
- Which blockers remain.
- Which audit coverage exists.
- Which bundle is safe to distribute.

## Changes

- Adds `src/socmint/dossier_certification_index.py`.
- Adds `src/socmint/dossier_certification_index_routes.py`.
- Registers certification index routes in the production release route module.
- Adds focused v10.12 certification index tests.
- Adds a v10.12 smoke script.

## Routes

- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>`
- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>/summary`
- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>/markdown`
- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>`

## Key fields

- `export_count`
- `artifact_count`
- `hash_count`
- `missing_hash_count`
- `verification_status`
- `gate_decision`
- `certified`
- `safe_to_distribute`
- `distribution_decision`
- `blockers`
- `audit_event_count`
- `recommended_bundle`

## Merge gate

Run:

```bash
PYTHONPATH=src pytest -q tests/test_dossier_certification_index_v10_12.py tests/test_dossier_export_certification_v10_11.py
```

or:

```bash
bash scripts/test_v10_12.sh
```

## Manual smoke

After login, check:

```text
/api/v1/dossier-builder/v3/certification-index/<case_id>
/api/v1/dossier-builder/v3/certification-index/<case_id>/summary
/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown
/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>
```
