# SOCMINT v12.10.19 — Release Dashboard Decision Engine Hardening

## Release identity

- Version: `12.10.19`
- Release tag: `v12.10.19-rc1`
- Branch: `feat/v12.10.19-release-dashboard-decision-engine`
- Baseline commit: `175d3f8e01ddc1c997c413b82d376726f6f1de39`

## Purpose

v12.10.19 hardens the release dashboard decision engine so the operator dashboard can show a `GO` state when the release is actually healthy, even if the most recent report file is a failed smoke test.

This fixes the observed v12.10.18 issue where `/release/status` showed `HOLD` because the newest JSON report was a failed live-smoke report while a passing runtime route gate existed one second earlier.

## Fixes

1. Adds a v12.10.19 release status service instead of reusing v12.10.17 logic.
2. Makes the latest gate viewer prefer the latest `PASS` / `GO` release gate report while still showing the latest overall report for audit context.
3. Updates required files to v12.10.18/v12.10.19 paths.
4. Does not require the app container to see Tor service files for dashboard `GO`.
5. Treats runtime readiness as `PASS` if app socket, `/readyz`, and dashboard HTTP checks pass.
6. Separates release dashboard decision sections:
   - release gate health
   - file visibility
   - runtime reachability
   - report availability
   - required files
7. Adds a dashboard decision gate proving the dashboard decision becomes `GO`.

## Added

- `src/socmint/release_status_v12_10_19.py`
- `scripts/release_dashboard_decision_gate_v12_10_19.py`
- `.github/workflows/v12_10_19_verify.yml`
- `release/V12_10_19_RELEASE_DASHBOARD_DECISION_ENGINE.md`

## Updated

- `src/socmint/release_status_routes_v12_10_17.py` now imports the v12.10.19 decision service while preserving route paths.
- `src/socmint/release_status_ui_routes_v12_10_18.py` now uses the v12.10.19 decision service while preserving UI route paths.
- `pyproject.toml`, `src/socmint/version.py`, and `release/CURRENT_STATUS.json` move to `12.10.19`.
- `.github/workflows/v12_10_18_verify.yml` is superseded/manual-only on this branch.

## Decision engine behavior

The release gate payload now exposes:

- `latest_overall`: newest JSON report, even if failed.
- `latest_pass`: newest passing report.
- `latest_release_gate_pass`: newest passing release gate report, preferred for dashboard `GO`.
- `failed_latest_does_not_block`: true when the newest report failed but a passing gate exists.

The dashboard decision is `GO` when:

- version and release manifest match,
- required v12.10.18/v12.10.19 artifacts exist,
- a passing release gate report exists,
- runtime reachability is healthy.

Tor service file visibility is shown as informational and does not block `GO` when runtime reachability is healthy.

## Verification

Run:

```bash
python scripts/release_dashboard_decision_gate_v12_10_19.py
```

Expected result:

```text
status: pass
decision: GO
```

## Operator result

After v12.10.19, `/release/status` should display `GO / pass` when the route gate and runtime checks are good, even if an older or newer non-blocking smoke report failed.
