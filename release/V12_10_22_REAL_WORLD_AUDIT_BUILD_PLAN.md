# v12.10.22 — Real World Audit Build Plan

## Purpose

This release turns the usability/value audit into a runtime product surface instead of a conversation-only assessment.

The goal is to keep SOCMINT-PROJECT anchored on the highest-value path:

```text
case -> entity -> evidence -> confidence -> human review -> dossier/report export
```

## Added

- `src/socmint/real_world_audit.py`
  - Builds a concrete operator-facing audit payload.
  - Scores runtime capability coverage by actual registered routes.
  - Separates `what_works` from `what_does_not`.
  - Includes a prioritized repair/value build plan.
  - Pulls in drift and audit summaries from existing build audit services.

- Runtime routes:
  - `GET /api/v1/workbench/real-world-audit`
  - `GET /workbench/real-world-audit`

- Smoke/test coverage:
  - `scripts/real_world_audit_smoke_v12_10_22.py`
  - `tests/test_real_world_audit_v12_10_22.py`

- CI/release-gate repair:
  - CI now uploads ruff lint output as an artifact when lint fails.
  - The runtime verify workflow starts Gunicorn before running the dashboard gate.
  - The dashboard gate verifies `/readyz` through the runtime-readiness path instead of assuming readiness.

## Build plan encoded in runtime output

1. Repair-first stabilization.
2. Operator happy-path workflow.
3. Claim/evidence/review integrity.
4. Connector normalization before connector expansion.
5. Professional case package export.

## Operator value

The new audit endpoint answers:

- What works now?
- What does not work yet?
- What is the current product value center?
- Which blockers must be repaired before more features are added?
- What should be built next?

## Safety / execution boundary

The audit service does **not** run connectors, crawlers, scraping jobs, browser automation, or destructive retention operations. It only inspects runtime routes, drift/audit payloads, and build-readiness signals.

## Remote verification

Required remote checks:

```text
CI / test: pass
SOCMINT v12.10.19 Verify / verify: pass
```

The verify workflow must prove runtime readiness by starting the application and polling:

```text
GET http://127.0.0.1:5000/readyz
```
