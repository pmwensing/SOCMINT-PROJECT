# SOCMINT v8.0.1 - Next Build Spec

This spec starts from the local v8.0.0 baseline committed in
`ec2dee3 Add high-end SOCMINT workflow layer`.

## Current Assessment

- Evidence capture is now artifact-backed, hash-verified, manifest-driven, and
  connected to chain-of-custody events.
- Case management is database-backed for cases, case events, subjects, tags,
  notes, assignment, saved views, and review state.
- Analyst cockpit routes exist for queues, cases, evidence, graph, exports,
  connector trust, jobs, and audit.
- Connector marketplace and trust surfaces exist, but the metrics are still
  mostly derived from runtime health rather than long-lived quality telemetry.
- Entity resolution and graph routes exist, but the UI is still structured
  data-first rather than a polished interactive analyst canvas.
- Responsible-use controls exist as scope review and gate APIs, but enforcement
  should be wired deeper into every connector, export, job, and capture path.
- Exports expose manifests and blockers, but signed bundle generation and
  parity checks across HTML, PDF, JSON, and CSV still need deeper coverage.

## High-Value Build Moves

1. Browser Capture Automation
   - Replace the current import-style capture with Playwright-driven full-page
     screenshots, PDF capture, MHTML/WARC-style archive output, response header
     capture, and deterministic artifact naming.

2. Connector Trust Telemetry
   - Persist connector run outcomes, rejected candidates, false positives,
     stale connectors, timeout rates, evidence coverage, and platform
     confidence over time.

3. Interactive Graph Canvas
   - Move from JSON-backed graph payloads to a real browser graph with filters
     for confidence, time, contradiction state, source refs, artifact refs, and
     entity type.

4. Export Bundle Builder
   - Add signed ZIP bundles with reproducible manifests, redaction presets,
     export diffing, parity assertions, verification screens, and release
     blockers.

5. Responsible-Use Enforcement
   - Enforce scope gates across capture, connector execution, jobs, case
     actions, and exports with audit events for every allow, warn, and block.

6. Analyst UI Polish
   - Replace template-first tables with dense workbench layouts, saved filters,
     queue drill-downs, empty states, error states, and consistent badges and
     action controls.

7. Connector SDK
   - Add a documented connector schema, normalizer contract, dry-run behavior,
     timeout policy, evidence reference requirements, and fixture runner.

## Optional Build Moves

- Add browser-side visual regression smoke tests for every major page.
- Add report export watermarking and client/court/internal export presets.
- Add case-level permissions beyond role-level route protection.
- Add background worker capture jobs for long pages and large export bundles.
- Add CSV parity tests for every table-like export.
- Add audit log search, retention filters, and admin review queues.
- Add backup/restore fixture coverage for all new v8 tables.

## Recommended Next Milestone

Ship v8.0.1 as the Browser Capture Automation and Export Bundle Builder
milestone. It gives the product its most defensible differentiator: every
finding can be traced back to reproducible, hash-verifiable evidence artifacts
and released in a client-ready bundle.

Definition of done:

- Playwright screenshot and PDF capture are available through UI and API.
- Capture manifests include request metadata, headers, actor, case, subject,
  artifact paths, and SHA-256 hashes.
- Export bundles include signed manifests, bundle-level hash verification,
  redaction preset metadata, and export blockers.
- Tests cover capture, verification, export bundling, migration, and route
  permissions.
- `ruff check src tests scripts`, `pre-commit run --all-files`, `pytest -q`,
  `make production-smoke`, `make backup-restore-smoke`, and `make ci` pass.
