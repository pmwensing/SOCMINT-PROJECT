# SOCMINT v7.6.1 — Connector Runtime Repair UX + Native Dependency Diagnostics

## Why

Runtime activation proved v7.6.0 worked, moving the connector runtime from all-missing to partially activated:

- Ready: h8mail, holehe, sherlock, socialscan
- Missing: maigret, phoneinfoga, archivebox

The remaining Maigret/ArchiveBox failure was caused by native pycairo/cairo build dependencies missing on the host:

- `pkg-config` missing
- `cmake` missing
- cairo development headers missing

## Added

- Human-readable connector health CLI by default.
- Clean JSON mode via `--json`.
- `make connectors-health` now prints grouped status without requiring `jq`.
- `make connectors-health-json` prints clean machine-readable JSON.
- Native dependency diagnostics for:
  - `pkg-config`
  - `cmake`
  - `cc`
  - `cairo`
- Native repair hint:

```bash
sudo apt update && sudo apt install -y pkg-config cmake build-essential python3-dev libcairo2-dev libgirepository-2.0-dev gir1.2-gtk-3.0
```

- Missing connector repair cards on the Connector Runtime UI.
- PhoneInfoga manual activation steps.
- Native dependency warning cards for Maigret/ArchiveBox/pycairo failures.
- Diagnostic helper script:
  - `scripts/diagnose_connector_runtime_v7_6_1.sh`
- `make test761` and `make zip761`.

## Updated commands

Human report:

```bash
make connectors-health
```

JSON report:

```bash
make connectors-health-json
```

Diagnostic helper:

```bash
bash scripts/diagnose_connector_runtime_v7_6_1.sh
```

## Validate

```bash
make test761
```

## Smoke coverage

- Runtime schema is `socmint.connector_runtime.v7_6_1`.
- Native dependency diagnostics exist.
- Maigret and ArchiveBox include native dependency repair hints.
- PhoneInfoga includes manual binary activation steps.
- Connector Runtime UI shows repair panels.
- Health CLI prints human-readable grouped status.
- Health CLI `--json` prints clean JSON.
- v7.6.0 installer regression still passes.
- Full Dossier regression still passes.
