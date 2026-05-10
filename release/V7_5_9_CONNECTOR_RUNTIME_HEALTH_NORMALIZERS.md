# SOCMINT v7.5.9 — Connector Runtime Verification + Tool Install Health + Real Output Normalizers

## Added

- Connector runtime health module.
- Runtime health UI page.
- Runtime health JSON endpoint.
- Version/executable probes for:
  - Maigret
  - Sherlock
  - SocialScan
  - Holehe
  - h8mail
  - PhoneInfoga
  - ArchiveBox
- Sample command rendering per connector.
- Target-type reporting per connector.
- ArchiveBox enabled/disabled/install-state reporting.
- Real output normalizers for connector stdout/stderr/JSON output.
- Connector runner integration so real runs, timeouts, skipped runs, and dry-runs all pass through normalized findings logic.
- Command Center link to Connector Runtime.
- v7.5.9 smoke test.
- `make test759` and `make zip759`.

## New routes

- `GET /connectors/runtime`
- `GET /api/v1/connectors/runtime`

## Why this matters

Earlier versions had connector wrappers and dry-run fallbacks, but the UI could still make enrichment look stronger than the actual runtime. v7.5.9 separates:

- connector wiring
- executable installation
- version availability
- ArchiveBox enablement
- dry-run status
- normalized output extraction

## Connector states

- `ready` — executable/version probe is available and real runs can be attempted.
- `missing` — executable is not available; dry-runs will be recorded.
- `disabled` — ArchiveBox is installed-capable but not enabled by `SOCMINT_ARCHIVEBOX_ENABLED=true`.

## Validate

```bash
make test759
```

## Covered by smoke

- Runtime health payload schema is `socmint.connector_runtime.v7_5_9`.
- All expected connectors are present.
- ArchiveBox is included in runtime health.
- Every connector exposes status, target types, and sample command.
- Normalizers extract URL/email findings from sample output.
- Dry-run connector path returns normalized payloads.
- Unsupported target type returns skipped payload safely.
- Runtime health UI renders.
- Runtime health API renders.
- Command Center links to Connector Runtime.
- v7.5.8 Command Center regression still passes.
- Full Dossier regression still passes.
