# v11.8 — Real Connector Run QA + Enrichment Normalization Upgrade

## Purpose

v11.8 adds a connector run QA gate after v11.7 made the core Python connector CLIs available in Docker.

## Added

- `src/socmint/connector_run_qa.py`
- `/api/v1/admin/connectors/run-qa`
- `scripts/test_v11_8.sh`
- `make test-v11-8`

## QA coverage

The new QA report validates:

1. Core connector runtime readiness for:
   - `maigret`
   - `sherlock`
   - `socialscan`
   - `holehe`
   - `h8mail`
2. Normalizer behavior against deterministic sample outputs.
3. Expected finding types:
   - `profile_url`
   - `account_presence`
4. Optional/manual connectors remain outside the blocking gate:
   - `phoneinfoga`
   - `archivebox`

## API

```text
GET /api/v1/admin/connectors/run-qa
```

Returns:

- `normalization`
- `runtime`
- `qa_gate`
- `status`

## Validation

Build with connector CLIs first:

```bash
docker compose build --no-cache --build-arg SOCMINT_INSTALL_CONNECTORS=true app worker
docker compose up -d app
docker compose --profile worker up -d worker
```

Run:

```bash
make test-v11-8
```

Expected:

```text
PASS connector run QA direct report
PASS /api/v1/admin/connectors/run-qa smoke
PASS v11.8 real connector run QA and normalization smoke
```
