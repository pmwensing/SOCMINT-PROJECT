# Changelog

## Unreleased

- Added the v16.11 Delivery Recovery Finalization Record Verification layer with
  canonical finalization payload-hash checks, finalization-id verification,
  audit verification linkage, readiness flag checks, and authenticated
  verification API wiring.
- Added the v16.10 Delivery Recovery Finalization Record with strict v16.9 audit
  verification prerequisite, deterministic finalization ids, final delivery-continuation
  readiness marking, linkage checks, and authenticated finalization API wiring.
- Added the v16.9 Delivery Recovery Closure Audit Package Verification layer with
  canonical package hash checks, audit package id verification, manifest order
  validation, per-row manifest id checks, artifact hash checks, and authenticated
  verification API wiring.
- Added the v16.8 Delivery Recovery Closure Audit Package with verified closure
  packaging, deterministic audit package ids, per-artifact manifest hashes,
  linkage checks, and authenticated package API wiring.
- Added the v16.7 Delivery Recovery Closure Record Verification layer with
  canonical closure payload-hash checks, closure-id verification, receipt/queue
  linkage validation, closure status checks, and authenticated verification API wiring.
- Added the v16.6 Delivery Recovery Closure Record with strict v16.5 receipt
  verification prerequisite, deterministic closure ids, completed/no-action
  closure handling, pending receipt blocking, and authenticated closure API wiring.
- Added the v16.5 Delivery Recovery Action Receipt Verification layer with
  canonical receipt-id checks, queue linkage verification, action receipt-id
  validation, action/recovery consistency checks, and authenticated verification
  API wiring.
- Added the v16.4 Delivery Recovery Action Receipt with deterministic action
  receipt ids, operator action status capture for retry/remediate/escalate/hold
  decisions, blocked-recovery handling, and authenticated receipt API wiring.
- Added the v16.3 Delivery Recovery / Retry Resolution Layer with deterministic
  recovery ids, operator recovery queue state, retry/hold/escalate/remediate
  decisions, and authenticated recovery API/workspace wiring.
- Added the v16.2 Delivery Exception Review with deterministic failed-attempt
  classification, exception ids, retryable exception counts, escalation state,
  and recommended operator actions.
- Added the v16.1 Delivery Attempt Ledger with deterministic attempt ids,
  delivery outcome state, retry eligibility, latest-attempt status, and
  blocked operations handling.
- Added the v16.0 Delivery Operations Snapshot with v15.6 execution-envelope
  gating, deterministic operation ids, operator event rollup, dispatch state,
  and blocked-operation reporting.
- Added the v15.6 Delivery Execution Envelope with a strict v15.5
  authorization prerequisite, authorized delivery links, and a compact
  execution id for the final delivery boundary.
- Added the v15.5 Delivery Authorization Record with a strict v15.4 receipt
  verification prerequisite, blocked authorization handling, and a compact
  canonical authorization id.
- Added the v15.4 Delivery Readiness Receipt Verification layer with
  canonical payload-hash, signature-hash, receipt-id, package-match, and
  handoff-package verification checks.
- Added the v15.3 Delivery Readiness Receipt with a signed-style canonical
  payload hash, signature hash, receipt id, and a strict v15.2 verification
  prerequisite before a receipt is emitted.
- Added the v15.2 Case Delivery Handoff Verification layer with manifest
  hash checks, gate/disposition consistency checks, package case matching,
  and a verification API for v15 handoff packages.
- Added the v15.1 Case Delivery Handoff Package with deterministic handoff
  manifests, operator receipts, deliver/hold disposition, and remediation
  actions derived from the v15 case delivery gate.
- Added the v15.0 Case Delivery Workspace with a case-level delivery gate
  spanning dossier readiness, evidence completeness, export blockers, delivery
  registry state, and human approval.
- Added the v14.3 Operator Release Console evaluation point with blocker
  rollup, explicit continue/pause decisions, and next-action guidance.
- Added v14.2 release-health freshness checks for the Operator Release Console,
  including snapshot age, configurable max age, and refresh command display.
- Added a v14.1 release-health snapshot for the Operator Release Console,
  including a GitHub CLI refresh script and console rendering for live-derived
  PR/check status.
- Added the v14.0 Operator Release Console with local release evidence checks,
  git metadata, clean PR queue closure state, UI/API routes, and regression
  coverage.
- Added a v10.32-v10.37 open PR triage note documenting stale branch state,
  mergeability, and non-destructive handling guidance.
- Added a v13 release documentation closure note and regression coverage that
  verifies every numbered v13 slot from v13.0 through v13.48 is accounted for.
- Added a v13.25 reserved-gap note so the v13 release sequence explicitly
  records the only slot without implementation evidence.
- Added the missing v13.11 normalization form update release note and narrowed
  the v13 sequence audit to the remaining v13.25 evidence gap.
- Added retroactive v13.23 and v13.27-v13.31 release notes for
  test-backed workflow navigation, full-report runtime safety, route
  hardening, endpoint aliases, visual polish, and export artifact UX.
- Added a v13 release sequence audit documenting closure indexes and known
  release-note gaps across the v13 line.
- Added a v13.45-v13.48 export-blocker workflow index covering screenshot
  runbook guidance, manifest route health, download audit, and runner-portable
  Playwright capture commands.
- Updated CI workflows to Node 24-backed GitHub Actions pins for checkout,
  Python setup, and artifact upload.
- Added a v13.36-v13.44 export-blocker index linking scoped export
  persistence, policy blockers, operator surfaces, and screenshot manifests.
- Added the v13.35 final correlation-scope closure note and `v13.35` tag,
  closing the case/correlation scope correctness gate before the v13.36+
  export-blocker line.
- Added v13.35D correlation-scope model integration, DB-backed proof/backfill
  routes, additive runtime schema repair for older spine databases, and
  regression coverage for isolated initial searches.
- Added the implementation-grade ultimate SOCMINT product build spec covering
  memberships, quotas, Tor deployment, responsible-use gates, evidence
  workflows, account discovery, graph UX, exports, billing, and production
  readiness.

## v9.6.0

Operator UX smoke and release cleanup.

- Added admin-only operator smoke matrix, summary, and validation endpoints.
- Registered operator smoke routes through production-release integration.
- Added focused operator smoke tests and release cleanup documentation.
- Synced package metadata to the v9.6.0 release line.

## v8.1.0

Account discovery ingest layer.

- Added `account_discoveries` persistence for social/profile account leads.
- Added account discovery ingestion from `account_presence` and `profile_url`
  spine observations.
- Added optional profile capture for discovered profile URLs.
- Added account discovery review and seed-promotion workflow.
- Added UI and API routes for discovery queues, ingest, review, and promotion.

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
