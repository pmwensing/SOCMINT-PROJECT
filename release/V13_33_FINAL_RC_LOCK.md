# v13.33 — Final Release Candidate Lock + Clean Install Acceptance

## Scope

This build locks the current SOCMINT v13 workflow as a final release candidate and adds repeatable acceptance tooling.

## Included

- Versioned Final RC status page: `/release/final-rc/v13.33`
- Versioned Final RC status API: `/api/v1/release/final-rc/v13.33`
- Clean clone/build/run acceptance script: `scripts/clean_install_acceptance_v13_33.sh`
- Runtime route/export acceptance script: `scripts/runtime_acceptance_v13_33.sh`
- Screenshot capture helper: `scripts/capture_runtime_pages_v13_33.py`
- Static regression tests for routes, scripts, release note, and acceptance labels

## Acceptance Lock

The final RC acceptance checks:

- Command Center
- Normalization Review Queue
- Dossier Readiness
- Claim/Evidence Ledger
- Full Dossier v2
- Full Report History
- Full Report View
- Full Report Retention
- Final RC status page/API
- Controlled Full Report export artifacts:
  - ZIP
  - Manifest
  - HTML
  - Markdown
  - JSON

## Operator Notes

The clean install script intentionally writes a local `.env` for isolated acceptance testing. Replace generated/local credentials before any production deployment.
