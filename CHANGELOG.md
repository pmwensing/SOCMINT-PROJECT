# Changelog

## v8.0.1

Browser capture automation and signed export bundle builder.

- Added browser capture mode with HTML, screenshot, PDF, MHTML, and manifest
  artifacts for each capture group.
- Added SHA-256 verification for capture manifests and every generated
  browser capture artifact.
- Added signed high-end export ZIP bundles with redaction presets, file hashes,
  bundle hashes, and verification metadata.
- Added API support for building and verifying high-end export bundles.
- Expanded v8 workflow tests for capture manifests, bundle generation, and
  bundle verification.

## v8.0.0

High-end SOCMINT workflow layer.

### Added

- Database-backed case records, case events, evidence captures, and
  responsible-use scope with Alembic migration `0008`.
- Browser/import evidence capture with artifact hashing, capture metadata,
  chain-of-custody events, automation plan, and verification API.
- Case management with subjects, notes, assignments, comments, priority, due
  dates, review state, saved workflow payloads, audit-style activity, and case
  capture attachment.
- Analyst console combining review queues, cases, captures, connector trust,
  jobs, policy events, and scope.
- Connector marketplace with trust badge, capability tags, fixture runner
  endpoint, and connector quality metrics.
- Entity resolution lab, graph canvas payload, export builder manifest,
  responsible-use gate, and scope review APIs.

### Validation

- `ruff check src tests scripts`
- `pytest -q tests/test_high_end_workflows.py`

## v7.8.1

Release hardening for the Ultimate Entity/Human dossier branch.

### Added

- Ultimate Dossier readiness review, export manifest, redacted JSON mode, and
  CSV/assertion parity checks.
- Connector reliability score and quality warning labels.
- Prioritized assertion review queue API.
- Scan job health, stale-running detection, requeue, and cancel APIs.
- Manual GitHub Actions Docker/Tor production rehearsal.

### Validation

- `make ci`
- `bash scripts/test_v7_8_0.sh`
- `make production-smoke`
- `make backup-restore-smoke`
- `make production-docker-smoke`

## v0.1.0-rc1

Production readiness candidate.

### Added

- Fail-fast production configuration validation for secrets, signup, bootstrap
  admin credentials, and backup passphrases.
- Split dependency sets for production, scanner integrations, and development.
- GitHub Actions CI with linting, tests, migration smoke, Compose validation,
  backup/restore smoke, production boot smoke, Docker deployment rehearsal, and
  `pip-audit`.
- Multi-stage Docker image build using the audited production lockfile.
- Admin user management, roles, audit filtering, password changes, queued scan
  jobs, and job status UI.
- Dedicated worker options for Docker Compose and systemd timer deployments.
- `/readyz`, request IDs, structured JSON request logging, and logrotate config.
- Production runbook covering deploy, rollback, backup, operations, and incident
  response.

### Changed

- Dashboard scan requests now enqueue work instead of running scans inside the
  request path.
- Docker health checks use database readiness via `/readyz`.
- Docker and systemd deployment docs now include worker operation and backup
  drills.

### Validation

- `make ci`
- `make production-docker-smoke`, including the Docker worker profile
- `make backup-restore-smoke`
