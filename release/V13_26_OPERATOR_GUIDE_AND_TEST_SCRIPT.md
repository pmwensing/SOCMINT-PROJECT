# v13.26 — Operator Guide and Full Test Script

## Purpose

This is the final pre-runtime-test guide for the v13 workflow. It defines the clean test sequence that should be run before more feature work continues.

## Test cutoff

Run this after v13.24 is merged and before further feature expansion.

## Clean clone test

```bash
git clone https://github.com/pmwensing/SOCMINT-PROJECT.git
cd SOCMINT-PROJECT
git checkout master
```

## Build and boot

```bash
docker compose build
docker compose up -d
```

## Runtime health checks

```bash
curl -fsS http://127.0.0.1:8080/readyz
curl -fsS http://127.0.0.1:8080/healthz || true
```

## Login

Open:

```text
http://127.0.0.1:8080
```

Use the configured local operator credentials.

## Analyst workflow walk-through

1. Open Command Center.
2. Open or create a subject.
3. Open the normalization review queue.
4. Confirm, reject, suppress, and reset test review items if sample data exists.
5. Open subject dossier readiness.
6. Open claim/evidence ledger.
7. Open export manifest page.
8. Open manifest API payload.
9. Open subject status API.
10. Open full dossier.

## Expected v13 pages

```text
/command-center
/review/normalization-queue
/subjects/<subject_id>/dossier/readiness
/subjects/<subject_id>/claim-evidence-ledger
/subjects/<subject_id>/export-manifest
/spine/subjects/<subject_id>/dossier
```

## Expected v13 APIs

```text
/api/v1/review/normalization-queue
/api/v1/review/normalization-update
/api/v1/review/normalization-promote
/api/v1/subjects/<subject_id>/dossier/readiness
/api/v1/subjects/<subject_id>/claim-evidence-ledger
/api/v1/subjects/<subject_id>/handoff-status
/api/v1/subjects/<subject_id>/export-manifest-draft
```

## Local test commands

```bash
python -m pytest tests/test_v13_21_usability_smoke.py -q
python -m pytest tests/test_v13_22_release_route_audit.py -q
python -m pytest tests/test_export_manifest_ui_routes_v13.py -q
python -m pytest -q
```

## Pass criteria

- Docker build completes.
- App boots.
- `/readyz` returns success.
- Login succeeds.
- Command Center loads.
- Review queue loads.
- Subject readiness loads.
- Claim/evidence ledger loads.
- Export manifest page loads.
- Route audit tests pass.
- No production database mutation is observed during smoke-only tests.

## Stop conditions

Stop feature building and repair if any of these happen:

- Container fails to boot.
- `/readyz` fails.
- Login fails.
- Command Center fails to load.
- Any v13 workflow page returns 500.
- Route audit fails.
- Database migration smoke fails.

## Next after test

If the clean runtime test passes, continue with packaging/export implementation. If it fails, patch only the exact failing runtime path first.
