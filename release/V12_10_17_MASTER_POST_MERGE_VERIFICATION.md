# SOCMINT v12.10.17 — Master Post-Merge Release Verification + Operator Status Dashboard

## Release identity

- Version: `12.10.17`
- Release tag: `v12.10.17-rc1`
- Branch: `feat/v12.10.17-master-post-merge-status`
- Baseline commit: `dbfac399e74edda05f9d6f8fd8a2d3c8acde0dad`

## Purpose

v12.10.17 adds a master-focused verification layer so the operator can prove the merged branch is release-clean after PR merge, not just during PR review.

It also adds API-readable release status payloads for dashboard or command-center integration.

## Added

- `/api/v1/release/status`
- `/api/v1/release/gates/latest`
- `src/socmint/release_status_v12_10_17.py`
- `src/socmint/release_status_routes_v12_10_17.py`
- `scripts/runtime_route_release_gate_v12_10_17.py`
- `scripts/post_merge_master_verify_v12_10_17.sh`
- `.github/workflows/v12_10_17_verify.yml`
- `release/V12_10_17_MASTER_POST_MERGE_VERIFICATION.md`

## Updated

- `src/socmint/wsgi.py`
- `src/socmint/version.py`
- `pyproject.toml`
- `release/CURRENT_STATUS.json`
- `.github/workflows/v12_10_16_release_gate.yml` is superseded/manual-only on this branch

## API routes

Authenticated route:

```text
GET /api/v1/release/status
```

Returns:

- package version payload
- release manifest payload
- latest release gate summary
- required file presence checks
- release decision: `GO` or `HOLD`

Authenticated route:

```text
GET /api/v1/release/gates/latest
```

Returns the latest JSON gate report found under:

```text
var/socmint/rc_reports/
```

## Local verification

Run after pulling master:

```bash
bash scripts/post_merge_master_verify_v12_10_17.sh
```

The verifier checks:

- clean master checkout unless `SOCMINT_CI_MODE=true`
- package/manifest/pyproject version alignment
- runtime route registration including release status routes
- release status payload generation
- inherited fresh DB gate availability and execution
- latest gate report readability
- JSON/Markdown verification report output

## CI

Workflow:

```text
.github/workflows/v12_10_17_verify.yml
```

The workflow runs the verifier and uploads all JSON/Markdown reports from:

```text
var/socmint/rc_reports/*.json
var/socmint/rc_reports/*.md
```

## Operator result

After v12.10.17, the operator has one local command and two API endpoints for release-clean verification:

```bash
bash scripts/post_merge_master_verify_v12_10_17.sh
```

```text
/api/v1/release/status
/api/v1/release/gates/latest
```
