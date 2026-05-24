# SOCMINT v12.10.18 — Release Status Dashboard UI + Live Gate Viewer

## Release identity

- Version: `12.10.18`
- Release tag: `v12.10.18-rc1`
- Branch: `feat/v12.10.18-release-status-dashboard-ui`
- Baseline commit: `0178b3bcf7989f74f57766e2bf494f65053e6a6a`

## Purpose

v12.10.18 makes the v12.10.17 release-status JSON visible through operator-facing web pages.

The goal is to give the operator a human-friendly dashboard for current release condition, latest gate result, report paths, route gate status, Tor diagnostic status, post-merge verification state, and the final `GO` / `HOLD` decision.

## Added

- `/release/status`
- `/release/gates`
- `src/socmint/release_status_ui_routes_v12_10_18.py`
- `src/socmint/templates/release_status.html`
- `src/socmint/templates/release_gates.html`
- `scripts/live_release_status_smoke_v12_10_18.py`
- `scripts/runtime_route_release_gate_v12_10_18.py`
- `.github/workflows/v12_10_18_verify.yml`
- `release/V12_10_18_RELEASE_STATUS_DASHBOARD_UI.md`

## Updated

- `src/socmint/wsgi.py` registers the release status UI routes.
- `src/socmint/templates/base.html` adds Product navigation links for Release Status and Gate Viewer.
- `pyproject.toml`, `src/socmint/version.py`, and `release/CURRENT_STATUS.json` move to `12.10.18`.
- `.github/workflows/v12_10_17_verify.yml` is manual-only/superseded on this branch.

## Operator pages

Authenticated UI page:

```text
/release/status
```

Shows:

- current version
- release manifest status
- latest gate decision
- latest JSON report path
- Tor diagnostic status
- release checks
- raw API links

Authenticated UI page:

```text
/release/gates
```

Shows:

- latest gate result
- latest gate report path
- recent JSON gate reports from `var/socmint/rc_reports/`

## Existing protected JSON APIs surfaced by the UI

```text
/api/v1/release/status
/api/v1/release/gates/latest
/api/v1/tor/diagnostics
```

The UI links to these APIs while keeping the authentication requirement intact.

## Smoke test

Run against a live local app:

```bash
SOCMINT_BASE_URL=http://127.0.0.1:5000 python scripts/live_release_status_smoke_v12_10_18.py
```

CI-safe route/template smoke:

```bash
SOCMINT_BASE_URL= python scripts/live_release_status_smoke_v12_10_18.py
```

The smoke script checks:

- package version is `12.10.18`
- `/release/status` is registered
- `/release/gates` is registered
- release JSON API routes remain registered
- templates exist
- live `/readyz` works when a base URL is supplied
- unauthenticated UI pages redirect or deny safely
- unauthenticated JSON APIs return `401` or `403`
- JSON/Markdown smoke reports are written to `var/socmint/rc_reports/`

## Runtime route gate

Run:

```bash
python scripts/runtime_route_release_gate_v12_10_18.py
```

The route gate adds `/release/status` and `/release/gates` to the required route list.

## Decision rule

- `GO`: UI routes registered, templates present, JSON APIs protected, and route gate passes.
- `HOLD`: missing route, missing template, unprotected JSON API, failed WSGI import, or version mismatch.
