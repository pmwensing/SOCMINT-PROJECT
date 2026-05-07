# SOCMINT Workbench v5.2

## Status

Build track: real connector execution layer + raw result persistence.

## Added

- Real connector registry.
- Real connector runner with subprocess execution.
- Safe fallback mode when external connector binaries are unavailable.
- DB-backed `connector_runs.raw_result` persistence.
- Raw run viewer endpoint.
- Findings extraction from connector output.
- Connector catalog endpoint.
- Frontend connector catalog and raw result viewer.
- v5.2 smoke test.

## New API

```text
GET  /api/connectors/
POST /api/connectors/run
GET  /api/connectors/runs
GET  /api/connectors/runs/{run_id}
```

## Supported connector wrappers

```text
sherlock   -> username
maigret    -> username
holehe     -> email
h8mail     -> email
domain_dns -> domain
```

## Operational test

```bash
make test52
```

## Notes

External OSINT tools run through subprocess execution when installed inside the worker/API image. If a binary is unavailable, the platform returns a safe fallback result and still persists the run record and raw output shape so the UI and audit pipeline remain stable.
