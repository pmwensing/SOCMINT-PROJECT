# SOCMINT v7.6.0 — Connector Runtime Installer + Scanner Image Toolchain

## Baseline preserved

v7.5.9 remains the honest runtime diagnostic baseline:

- connector wrappers exist
- runtime health reports installed/missing/disabled truthfully
- missing tools dry-run instead of pretending to enrich
- normalized findings are used for real runs and dry-runs

## Added in v7.6.0

- One-command local connector runtime installer:
  - `scripts/install_connector_runtime_v7_6_0.sh`
- Optional scanner compose profile:
  - `docker-compose.scanners.yml`
- Connector install hints in runtime payload/UI.
- Connector check commands in runtime payload/UI.
- Installer metadata in connector runtime API.
- Health CLI:
  - `python -m socmint.connector_runtime_health_cli`
- Make targets:
  - `make install-connectors`
  - `make connectors-health`
  - `make test760`
  - `make zip760`
- v7.6.0 installer smoke.

## Installer behavior

The installer creates an isolated runtime under:

```bash
.connector-tools/
```

It attempts Python-based connector installs into:

```bash
.connector-tools/venv/
```

It writes an activation file:

```bash
.connector-tools/bin/socmint-connectors-env
```

Activate with:

```bash
source .connector-tools/bin/socmint-connectors-env
make connectors-health
```

## Python connector install attempts

- Maigret: `python -m pip install --upgrade maigret`
- Sherlock: `python -m pip install --upgrade sherlock-project`
- SocialScan: `python -m pip install --upgrade socialscan`
- Holehe: `python -m pip install --upgrade holehe`
- h8mail: `python -m pip install --upgrade h8mail`

## Manual/conditional connectors

- PhoneInfoga: binary install required; installer writes guidance.
- ArchiveBox: installable with Python but must be explicitly enabled with `SOCMINT_ARCHIVEBOX_ENABLED=true`.

## Optional Docker scanner profile

Run with:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-web.yml -f docker-compose.scanners.yml up --build app
```

The profile mounts a persistent `connector-tools` volume and runs the installer on first startup if the connector venv does not exist.

## Validate

```bash
make test760
```

## Runtime activation check

```bash
make install-connectors
source .connector-tools/bin/socmint-connectors-env
make connectors-health
```

## Smoke coverage

- Installer script exists and references all expected connector profiles.
- Optional scanner compose profile exists.
- Runtime payload schema is upgraded to `socmint.connector_runtime.v7_6_0`.
- Every connector exposes install/check commands.
- Connector Runtime UI shows install activation instructions.
- Connector Runtime API exposes installer metadata.
- v7.5.9 runtime smoke still passes.
- Full Dossier regression still passes.
