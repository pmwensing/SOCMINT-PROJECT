# SOCMINT v12.10.15 — CI Wiring + Auto Release Gate Artifact Upload

## Release identity

- Version: `12.10.15`
- Release tag: `v12.10.15-rc1`
- Branch: `feat/v12.10.15-ci-release-gate-artifacts`
- Baseline commit: `1025970721489e5f700bedb433361e975c1fb471`
- Baseline summary: `v12.10.14 RC Stabilization + Fresh Deploy Gate passed locally and merged`

## Purpose

v12.10.15 promotes the v12.10.14 release gate into CI. It adds GitHub Actions wiring so every pull request and push can run the fresh database release gate and upload the generated JSON/Markdown reports as workflow artifacts.

This is a CI/productization increment. It does not add a new intelligence feature layer.

## Added files

- `.github/workflows/v12_10_15_release_gate.yml`
- `scripts/fresh_db_release_gate_v12_10_15.sh`
- `scripts/runtime_route_release_gate_v12_10_15.py`
- `scripts/subject_to_dossier_e2e_v12_10_15.py`
- `release/V12_10_15_CI_RELEASE_GATE_ARTIFACTS.md`

## Updated files

- `pyproject.toml`
- `src/socmint/version.py`
- `release/CURRENT_STATUS.json`

## CI behavior

The workflow runs on:

- pull requests targeting `master`
- pushes to `master`
- pushes to `feat/**`
- manual `workflow_dispatch`

The workflow runs:

```bash
SOCMINT_CI_MODE=true bash scripts/fresh_db_release_gate_v12_10_15.sh
```

`SOCMINT_CI_MODE=true` allows the GitHub Actions checkout environment while preserving the strict clean-check behavior for local operator runs.

## Artifact upload

The workflow uploads all release gate report files from:

```text
var/socmint/rc_reports/*.json
var/socmint/rc_reports/*.md
```

Artifact name pattern:

```text
socmint-v12-10-15-release-gate-${{ github.run_id }}
```

Retention:

```text
30 days
```

Upload policy:

```text
if: always()
```

That means reports are uploaded on both pass and fail, as long as the workflow can reach the upload step.

## Local run

```bash
bash scripts/fresh_db_release_gate_v12_10_15.sh
```

## CI run

```bash
SOCMINT_CI_MODE=true bash scripts/fresh_db_release_gate_v12_10_15.sh
```

## Required pass criteria

1. `git clean checkout or CI checkout accepted`
2. `python venv install succeeds`
3. `pyproject version matches release manifest`
4. `alembic upgrade head succeeds on empty DB`
5. `app imports hard-pass`
6. `route list hard-pass`
7. `command_center_payload returns schema`
8. `create subject succeeds`
9. `add seed succeeds`
10. `create connector run succeeds`
11. `create observation succeeds`
12. `create assertion succeeds`
13. `approve/reject assertion succeeds`
14. `dossier export generates JSON + HTML`
15. `RC report writes JSON + Markdown`
16. `GitHub Actions uploads release gate JSON/Markdown artifacts`

## Release decision rule

- `GO`: all release gate checks pass
- `FAIL`: any install, migration, import, route, schema, workflow, export, report, or CI artifact step fails

## Operator note

After this merges, every new SOCMINT feature branch should be expected to pass the v12.10.15 release gate before merge.
