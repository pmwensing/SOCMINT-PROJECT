# SOCMINT v12.10.14 — Release Candidate Stabilization + Fresh Deploy Gate

## Release identity

- Version: `12.10.14`
- Release tag: `v12.10.14-rc1`
- Branch: `feat/v12.10.14-rc-stabilization-gate`
- Baseline commit: `72aeb96d84b0598dac21ebf03fa27ee171974ede`
- Baseline summary: `v12.10.13 integrate dossier assertion handoff stack`

## Purpose

This release candidate does not add another intelligence feature layer. It stabilizes the current v12 stack behind a clean, reproducible release gate.

The gate is designed to prove that a clean checkout can install, migrate an empty database, import the application, verify critical runtime routes, execute the command center payload, create a subject workflow, validate assertion review actions, export a dossier, and write RC report artifacts.

## Added files

- `scripts/fresh_db_release_gate_v12_10_14.sh`
- `scripts/runtime_route_release_gate_v12_10_14.py`
- `scripts/subject_to_dossier_e2e_v12_10_14.py`
- `src/socmint/version.py`
- `release/CURRENT_STATUS.json`
- `release/V12_10_14_RC_STABILIZATION_REPORT.md`

## Required pass criteria

1. `git clean checkout`
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

## Gate behavior

### Fresh DB wrapper

Run:

```bash
bash scripts/fresh_db_release_gate_v12_10_14.sh
```

The wrapper performs the full release check in order:

- confirms the working tree is clean before creating temporary artifacts
- creates an isolated virtual environment under `var/test_v12_10_14/.venv`
- installs the package in editable mode
- checks `pyproject.toml`, `src/socmint/version.py`, and `release/CURRENT_STATUS.json` version alignment
- runs Alembic against an empty SQLite database
- verifies required tables exist after migration
- runs the hard runtime route gate
- runs the subject-to-dossier E2E gate
- writes final status artifacts under `var/socmint/rc_reports/`

### Runtime route gate

Run:

```bash
python scripts/runtime_route_release_gate_v12_10_14.py
```

This is intentionally stricter than the older diagnostic RC gate. A WSGI import failure, version mismatch, or missing required route is a hard release failure.

### Subject-to-dossier E2E gate

Run:

```bash
python scripts/subject_to_dossier_e2e_v12_10_14.py
```

This gate exercises the human-review dossier chain:

- create subject
- add seed
- create connector run
- create observation
- create assertion
- confirm assertion
- reject assertion
- generate command center payload
- export dossier JSON
- export dossier HTML
- write RC report JSON
- write RC report Markdown

## Expected outputs

The release gate writes JSON and Markdown reports under:

```text
var/socmint/rc_reports/
```

Expected final wrapper status files:

```text
var/socmint/rc_reports/socmint_v12_10_14_fresh_db_gate_status.json
var/socmint/rc_reports/socmint_v12_10_14_fresh_db_gate_status.md
```

## Release decision rule

- `GO`: all required criteria pass
- `FAIL`: any install, migration, import, route, schema, workflow, export, or report step fails

There is no soft `review` state for this release gate. Diagnostic gates may still use review states, but the v12.10.14 release gate must fail closed.

## Operator note

If the gate fails, fix the first failing stage before continuing feature work. v12.10.14 is a stabilization gate, not a new feature target.
