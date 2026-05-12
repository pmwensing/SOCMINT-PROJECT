# SOCMINT v7.8.1 - Release Hardening And Operator Reliability

This milestone hardens the v7.8.0 Ultimate Entity/Human dossier path and closes
the highest-value operational gaps before merge.

## Added

- Ultimate dossier readiness review with `ready`, `needs_review`, and `blocked`
  states.
- Ultimate dossier export manifest with deterministic payload SHA-256, assertion
  CSV SHA-256, CSV/assertion parity checks, and traceability counts.
- Redacted Ultimate Dossier JSON mode for sensitive identifier fields.
- Connector reliability score and warning labels for dry-run-only,
  failure-heavy, high-rejection, and low-evidence-coverage connectors.
- Assertion review queue API ordered by review priority.
- Scan job health API with queue depth, running/failed counts, stale-running job
  detection, and needs-attention status.
- Admin APIs to requeue or cancel scan jobs.
- On-demand GitHub Actions Docker/Tor production rehearsal via
  `workflow_dispatch`.

## New API Surfaces

```text
GET  /api/v1/spine/subjects/<id>/ultimate-dossier?redacted=1
GET  /api/v1/spine/subjects/<id>/ultimate-dossier/manifest
GET  /api/v1/spine/assertions/review-queue
GET  /api/v1/jobs/health
POST /api/v1/jobs/<id>/requeue
POST /api/v1/jobs/<id>/cancel
```

## Validation

```bash
make ci
bash scripts/test_v7_8_0.sh
make production-smoke
make backup-restore-smoke
make production-docker-smoke
```
