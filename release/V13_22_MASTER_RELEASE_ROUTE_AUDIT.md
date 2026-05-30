# v13.22 — Master Release Route Audit

## Purpose

Add CI-visible route coverage for the full v13 analyst workflow surface.

## Added

- `tests/test_v13_22_release_route_audit.py`
  - Constructs a clean app.
  - Registers v13 workflow routes explicitly and idempotently.
  - Asserts expected UI and API routes are present.

## Covered areas

```text
Command Center
Normalization review queue
Normalization update/promote APIs
Dossier readiness UI/API
Claim/evidence ledger UI/API
Subject status API
Export manifest draft API
```

## Value

Current-head branches will fail CI if a future patch drops one of the core v13 workflow routes.
