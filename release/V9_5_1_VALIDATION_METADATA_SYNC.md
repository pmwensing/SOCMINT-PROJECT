# SOCMINT v9.5.1 — Release Certification Validation + Version Metadata Sync

## Summary

v9.5.1 is a stabilization release for the v9.5 release-certification line. It does not add a new major feature surface. It validates the release-certification layer and synchronizes project/package version metadata so operator, package, and certification outputs no longer disagree.

## Changed

- Synced `pyproject.toml` project version to `9.5.1`.
- Synced `src/socmint/__init__.py` module version to `9.5.1`.
- Added focused metadata validation tests.
- Added this release note as the validation handoff artifact.

## Validation scope

The v9.5.1 gate should confirm:

- `certification_report()` returns schema `socmint.certification.v9_5_0`.
- `certification_summary()` matches the report state, score, and percentage.
- Package metadata and module metadata both report `9.5.1`.
- Admin certification routes remain registered through production-release route integration:
  - `GET /api/v1/admin/certification/report`
  - `GET /api/v1/admin/certification/summary`

## Local validation commands

```bash
python -m pytest tests/test_certification_v9_5.py tests/test_version_metadata_v9_5_1.py
python -m pytest
```

## Merge gate

Merge only after the focused validation tests and full suite pass.
