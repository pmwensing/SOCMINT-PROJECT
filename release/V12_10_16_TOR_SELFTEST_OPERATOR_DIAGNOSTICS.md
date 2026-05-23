# SOCMINT v12.10.16 — Tor Hidden Service Self-Test + Operator Diagnostics

## Release identity

- Version: `12.10.16`
- Release tag: `v12.10.16-rc1`
- Branch: `feat/v12.10.16-tor-selftest-diagnostics`
- Baseline: `v12.10.15 CI release gate artifact upload branch`

## Purpose

This release adds operator diagnostics for the SOCMINT Docker Tor hidden-service topology.

The specific issue fixed is false-positive remediation advice that tells the operator to change:

```text
HiddenServicePort 80 127.0.0.1:5000
```

That mapping is correct when the application container uses:

```text
network_mode: service:tor
```

and gunicorn binds inside the shared network namespace at:

```text
127.0.0.1:5000
```

## Added

- `/api/v1/tor/diagnostics`
- `src/socmint/hidden_service_diagnostics_routes_v12_10_16.py`
- `scripts/tor_hidden_service_selftest_v12_10_16.py`
- `scripts/runtime_route_release_gate_v12_10_16.py`
- `scripts/subject_to_dossier_e2e_v12_10_16.py`
- `scripts/fresh_db_release_gate_v12_10_16.sh`
- `.github/workflows/v12_10_16_release_gate.yml`
- `release/V12_10_16_TOR_SELFTEST_OPERATOR_DIAGNOSTICS.md`

## Updated

- `src/socmint/tor_production.py`
- `src/socmint/wsgi.py`
- `src/socmint/version.py`
- `pyproject.toml`
- `release/CURRENT_STATUS.json`

## API diagnostic

Authenticated route:

```text
GET /api/v1/tor/diagnostics
```

The payload reports:

- torrc availability to the running process
- parsed hidden-service target mapping
- hidden-service directory and hostname status
- socket check for the application target
- `/readyz` HTTP check for the application target
- dashboard HTTP check for the application target
- whether the Docker Tor shared namespace model explains why `127.0.0.1:5000` is correct

## Operator self-test

Run from the repository root after the Docker stack is up:

```bash
python3 scripts/tor_hidden_service_selftest_v12_10_16.py
```

The self-test checks:

- `docker compose config` is readable
- compose contains `network_mode: service:tor`
- compose shows the app target as `127.0.0.1:5000`
- source torrc exists at `deploy/tor/torrc`
- source torrc contains the expected hidden-service mapping
- app `/readyz` works inside the shared namespace
- the Python diagnostics payload loads and returns the v12.10.16 schema

Reports are written to:

```text
var/socmint/rc_reports/
```

## Release gate

Run:

```bash
bash scripts/fresh_db_release_gate_v12_10_16.sh
```

The v12.10.16 fresh DB gate validates:

- clean checkout or CI checkout state
- editable install
- version metadata alignment
- empty DB migration
- WSGI import and route list
- `/api/v1/tor/diagnostics` route registration
- subject-to-dossier E2E workflow
- Tor diagnostics payload schema
- report generation

## CI

The branch adds:

```text
.github/workflows/v12_10_16_release_gate.yml
```

The inherited v12.10.15 workflow is marked superseded/manual-only on this branch to prevent a version-mismatch false failure.

## Expected operator conclusion

When the Docker stack is configured like this:

```text
app network_mode: service:tor
gunicorn --bind 127.0.0.1:5000
HiddenServicePort 80 127.0.0.1:5000
```

then the Tor hidden-service mapping is correct.

Do not change it to `app:5000` unless the app no longer shares the Tor network namespace.
