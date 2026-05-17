# v11.7 — Connector Runtime Docker Toolchain + Template Fix

## Purpose

v11.7 makes the connector runtime usable after Docker rebuilds by optionally baking the core Python connector CLIs into the app image and fixing the Connector Runtime browser page template.

## Added

- Docker build arg: `SOCMINT_INSTALL_CONNECTORS=true`
- Optional Docker install layer for:
  - `maigret`
  - `sherlock-project`
  - `socialscan`
  - `holehe`
  - `h8mail`
- `/connectors/runtime` page/API smoke test
- `scripts/test_v11_7.sh`
- `make test-v11-7`

## Fixed

- `connector_runtime.html` now uses `payload.native_dependencies['items']` instead of `payload.native_dependencies.items`.
- This prevents Jinja from treating `items` as the Python dictionary method and crashing `/connectors/runtime`.

## Optional/manual connectors

The following remain optional/manual in v11.7:

- `phoneinfoga`
- `archivebox`

## Build with connector CLIs

```bash
docker compose build --no-cache --build-arg SOCMINT_INSTALL_CONNECTORS=true app worker
docker compose up -d app
docker compose --profile worker up -d worker
```

## Validation

Run:

```bash
make test-v11-7
```

Expected:

```text
PASS connector runtime ready set
PASS /connectors/runtime page/API smoke
PASS v11.7 connector runtime Docker toolchain smoke
```
