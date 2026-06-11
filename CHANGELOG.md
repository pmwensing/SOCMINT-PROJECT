# Changelog

## Unreleased

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
