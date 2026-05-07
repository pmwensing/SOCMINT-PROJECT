# Changelog

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
