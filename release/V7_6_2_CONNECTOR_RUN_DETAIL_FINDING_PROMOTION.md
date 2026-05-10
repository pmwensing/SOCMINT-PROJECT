# SOCMINT v7.6.2 — Real Connector Run Detail + Raw Output Viewer + Finding Promotion Queue

## Why

v7.6.1 completed runtime activation and all seven connector runtimes reported ready:

- h8mail
- holehe
- maigret
- phoneinfoga
- sherlock
- socialscan
- archivebox

v7.6.2 adds the analyst review workflow after connector execution.

## Added

- Connector run review payload layer.
- Connector run list page.
- Connector run detail page.
- Raw stdout viewer.
- Raw stderr viewer.
- Raw JSON viewer.
- Normalized finding display per run.
- Finding Promotion Queue.
- Finding review actions:
  - promote
  - reject
  - uncertain
- Promotion into Spine Dossier assertions when a subject is selected.
- Audit logging for connector finding review actions.
- API endpoints for runs, run detail, finding queue, and review actions.
- Command Center links for Connector Runs and Finding Queue.
- v7.6.2 smoke test.

## New routes

- `GET /connectors/runs`
- `GET /connectors/runs/<run_id>`
- `GET /connectors/findings`
- `POST /connectors/findings/<finding_id>/review`
- `GET /api/v1/connectors/runs`
- `GET /api/v1/connectors/runs/<run_id>`
- `GET /api/v1/connectors/findings`
- `POST /api/v1/connectors/findings/<finding_id>/review`

## Validate

```bash
bash scripts/test_v7_6_2.sh
```

## Smoke coverage

- Creates a connector run with raw stdout/stderr/JSON.
- Records normalized findings linked to the connector run.
- Opens connector run list.
- Opens connector run detail.
- Verifies raw stdout/stderr/JSON panels render.
- Opens Finding Promotion Queue.
- Promotes a finding into a Spine subject assertion.
- Rejects and marks findings uncertain.
- Verifies API paths.
- Verifies Command Center links to Connector Runs and Finding Queue.
- Runs v7.6.1 runtime repair regression.
- Runs Full Dossier regression.

## Note

The Makefile target may be added in a smaller follow-up patch if the repository tooling blocks the full Makefile rewrite. The runnable test script is included as `scripts/test_v7_6_2.sh`.
